from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from uuid import uuid4

from mtnsim.acoustics.field.noise_grid import update_noise_grid_cpu, update_noise_grid_gpu
from mtnsim.acoustics.propagation.correction import PropagationContext
from mtnsim.acoustics.propagation.diffraction import build_diffraction_context
from mtnsim.acoustics.propagation.materials import MaterialContext
from mtnsim.acoustics.propagation.reflection import build_reflection_context
from mtnsim.acoustics.propagation.shielding import BarrierSegment, build_shielding_context
from mtnsim.core.context import RunContext
from mtnsim.io.result_store import write_receiver_histories, write_run_manifest, write_run_result_summary
from mtnsim.scene import GridDomain, build_scene_model, read_network_bounds
from mtnsim.schemas.project import ProjectManifest
from mtnsim.schemas.results import ReceiverStats, RunResultSummary
from mtnsim.schemas.run import RunSummary
from mtnsim.schemas.scenario import ScenarioConfig
from mtnsim.traffic.sumo_adapter import SumoAdapter
from mtnsim.traffic.vehicle_controls import (
    LaneChangeState,
    VehicleDeploymentConfig,
    add_vehicle,
    apply_speed_after_distance,
    disable_lane_change,
    enforce_lane_change,
    restore_vehicle_speeds,
)


@dataclass(slots=True)
class SimulationArtifacts:
    run_id: str
    output_dir: Path
    receiver_history_files: dict[str, Path]
    manifest_file: Path
    result_summary_file: Path
    run_summary: RunSummary
    result_summary: RunResultSummary
    final_grid_snapshot_file: Path | None = None


class RunService:
    def create_run_context(self, project: ProjectManifest, scenario: ScenarioConfig) -> RunContext:
        return RunContext(project=project, scenario=scenario, run_id=uuid4().hex)

    def summarize(self, context: RunContext) -> RunSummary:
        return RunSummary(
            run_id=context.run_id,
            project=context.project.project.name,
            scenario=context.scenario.scenario.name,
            max_steps=context.project.simulation_defaults.max_steps,
            max_vehicles=context.scenario.traffic.max_vehicles,
            receiver_count=len(context.scenario.receivers),
            lane_change_mode=context.scenario.controls.lane_change_mode,
            lane_change_strategy=context.scenario.controls.lane_change_strategy,
        )

    def run_simulation(self, context: RunContext, use_gpu: bool = True) -> SimulationArtifacts:
        project_root = self._project_root(context.project)
        network_path = self._resolve_path(project_root, context.project.paths.network)
        sumo_config_path = self._resolve_path(project_root, context.project.paths.sumo_config)
        output_root = self._resolve_path(project_root, context.project.paths.outputs)

        if not network_path.exists():
            raise FileNotFoundError(f"Network file not found: {network_path}")
        if not sumo_config_path.exists():
            raise FileNotFoundError(f"SUMO config not found: {sumo_config_path}")

        output_dir = output_root / context.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        min_x, min_y, max_x, max_y = read_network_bounds(network_path)
        grid_domain = self._build_grid_domain(context, min_x, min_y, max_x, max_y)
        receiver_positions = {receiver.id: (receiver.x, receiver.y, receiver.z) for receiver in context.scenario.receivers}
        receiver_histories = {receiver.id: [] for receiver in context.scenario.receivers}
        coefficients = {
            vehicle_type: (profile.a, profile.b)
            for vehicle_type, profile in context.scenario.noise.vehicle_coefficients.items()
        }
        scene_model = build_scene_model(context.scenario.scene)
        shielding_segments = scene_model.to_shielding_segments()
        propagation_provider = self._build_propagation_provider(shielding_segments)
        effective_use_gpu = use_gpu and not shielding_segments

        lane_state = LaneChangeState()
        deployment_config = VehicleDeploymentConfig(
            vehicle_types=context.scenario.traffic.vehicle_types,
            vehicle_weights=context.scenario.traffic.vehicle_weights,
            route_types=context.scenario.traffic.route_types,
            start_mode=context.scenario.traffic.start_mode,
            vehicle_interval_seconds=context.scenario.traffic.vehicle_interval_seconds,
            max_simulation_steps=context.project.simulation_defaults.max_steps,
            lane_change_ratio=context.scenario.controls.lane_change_ratio,
        )
        start_speed_mps = context.scenario.traffic.start_speed_kmh / 3.6
        post_target_speed_mps = context.scenario.controls.post_target_speed_kmh / 3.6
        lane_change_constant_speed_mps = self._kmh_to_mps(context.scenario.controls.lane_change_constant_speed_kmh)

        sim = SumoAdapter()
        deployed_vehicles = 0
        final_grid_snapshot: dict[str, float] = {}

        try:
            sim.start(sumo_config_path)
            for time_step in range(context.project.simulation_defaults.max_steps):
                if deployed_vehicles < context.scenario.traffic.max_vehicles:
                    add_vehicle(sim, lane_state, deployed_vehicles, time_step, deployment_config, constant_speed=start_speed_mps)
                    deployed_vehicles += 1

                sim.simulation_step()
                snapshots = sim.snapshots()

                if context.scenario.controls.lane_change_mode == "disable":
                    for snapshot in snapshots:
                        disable_lane_change(sim, snapshot.vehicle_id)
                elif context.scenario.controls.lane_change_mode == "enforce":
                    enforce_lane_change(
                        sim,
                        lane_state,
                        lane_index=context.scenario.controls.target_lane_index,
                        designated_lane=context.scenario.controls.designated_lane,
                        min_x=min_x,
                        max_x=max_x,
                        min_y=min_y,
                        max_y=max_y,
                        check_radius=context.scenario.controls.lane_change_check_radius_meters,
                        force_change=context.scenario.controls.lane_change_force_change,
                        mode=context.scenario.controls.lane_change_strategy,
                        target_positions=context.scenario.controls.lane_change_target_positions,
                        constant_speed=lane_change_constant_speed_mps,
                        speed_change=context.scenario.controls.lane_change_speed_change_mps,
                        restore_time=context.scenario.controls.lane_change_restore_time_seconds,
                    )
                    restore_vehicle_speeds(sim, lane_state)

                vehicle_positions = {}
                vehicle_types = {}
                vehicle_speeds = {}
                for snapshot in snapshots:
                    apply_speed_after_distance(
                        sim,
                        lane_state,
                        snapshot.vehicle_id,
                        snapshot.position,
                        context.scenario.controls.post_distance_meters,
                        post_target_speed_mps,
                        enabled=context.scenario.controls.post_distance_speed_control,
                    )
                    vehicle_positions[snapshot.vehicle_id] = snapshot.position
                    vehicle_types[snapshot.vehicle_id] = snapshot.vehicle_type
                    vehicle_speeds[snapshot.vehicle_id] = snapshot.speed_mps

                engine = update_noise_grid_gpu if effective_use_gpu else update_noise_grid_cpu
                final_grid_snapshot = engine(
                    {cell_id: (cell.x, cell.y, cell.z) for cell_id, cell in grid_domain.cells.items()},
                    vehicle_positions,
                    vehicle_types,
                    vehicle_speeds,
                    coefficients,
                    context.scenario.noise.background_noise_db,
                    context.scenario.noise.max_area_meters,
                    propagation_provider,
                )
                receiver_snapshot = engine(
                    receiver_positions,
                    vehicle_positions,
                    vehicle_types,
                    vehicle_speeds,
                    coefficients,
                    context.scenario.noise.background_noise_db,
                    context.scenario.noise.max_area_meters,
                    propagation_provider,
                )
                for receiver_id, value in receiver_snapshot.items():
                    receiver_histories[receiver_id].append(value)
        finally:
            sim.close()

        run_summary = self.summarize(context)
        manifest_file = write_run_manifest(output_dir, run_summary)
        receiver_files = write_receiver_histories(output_dir, receiver_histories)
        grid_snapshot_file = None
        if context.project.outputs.store_grid_timeseries:
            grid_snapshot_file = output_dir / 'grid_final_snapshot.json'
            grid_snapshot_file.write_text(json.dumps(final_grid_snapshot, indent=2), encoding='utf-8')

        result_summary = RunResultSummary(
            run=run_summary,
            output_dir=str(output_dir),
            manifest_file=str(manifest_file),
            receiver_history_files={key: str(value) for key, value in receiver_files.items()},
            final_grid_snapshot_file=str(grid_snapshot_file) if grid_snapshot_file else None,
            used_gpu=effective_use_gpu,
            receiver_stats=self._build_receiver_stats(receiver_histories),
            propagation_features={
                'shielding_enabled': bool(shielding_segments),
                'reflection_enabled': bool(shielding_segments),
                'diffraction_enabled': bool(shielding_segments),
                'shielding_segment_count': len(shielding_segments),
                'noise_barrier_count': len(scene_model.noise_barriers),
                'building_count': len(scene_model.buildings),
                'scene_object_count': len(scene_model.objects),
                'gpu_requested': use_gpu,
                'gpu_used': effective_use_gpu,
            },
        )
        result_summary_file = write_run_result_summary(output_dir, result_summary)

        return SimulationArtifacts(
            run_id=context.run_id,
            output_dir=output_dir,
            receiver_history_files=receiver_files,
            manifest_file=manifest_file,
            result_summary_file=result_summary_file,
            run_summary=run_summary,
            result_summary=result_summary,
            final_grid_snapshot_file=grid_snapshot_file,
        )

    def _project_root(self, project: ProjectManifest) -> Path:
        if project.source_path is None:
            return Path.cwd()
        source_parent = project.source_path.parent
        if source_parent.name == 'examples':
            return source_parent.parent
        return source_parent

    def _resolve_path(self, project_root: Path, raw_path: str) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path
        return project_root / path

    def _build_grid_domain(self, context: RunContext, min_x: float, min_y: float, max_x: float, max_y: float) -> GridDomain:
        domain = GridDomain(
            min_x=min_x,
            min_y=min_y,
            max_x=max_x,
            max_y=max_y,
            grid_size=context.scenario.noise.grid_size_meters,
        )
        for x, y in domain.iter_points(
            context.scenario.grid.margin_x_start,
            context.scenario.grid.margin_x_end,
            context.scenario.grid.extra_y_extent,
        ):
            domain.add_cell(x, y, context.scenario.noise.receiver_height_meters, context.scenario.noise.background_noise_db)
        return domain

    def _kmh_to_mps(self, value: float | None) -> float | None:
        if value is None:
            return None
        return value / 3.6

    def _build_receiver_stats(self, histories: dict[str, list[float]]) -> dict[str, ReceiverStats]:
        stats: dict[str, ReceiverStats] = {}
        for receiver_id, values in histories.items():
            if not values:
                stats[receiver_id] = ReceiverStats(min_db=0.0, max_db=0.0, mean_db=0.0, sample_count=0)
                continue
            stats[receiver_id] = ReceiverStats(
                min_db=min(values),
                max_db=max(values),
                mean_db=sum(values) / len(values),
                sample_count=len(values),
            )
        return stats

    def _build_propagation_provider(self, shielding_segments: list[BarrierSegment]):
        if not shielding_segments:
            return None

        def provider(
            poi_id: str,
            poi_position: tuple[float, float, float],
            vehicle_id: str,
            vehicle_position: tuple[float, float],
        ) -> PropagationContext | None:
            shielding = build_shielding_context(
                receiver_pos=poi_position,
                source_pos=vehicle_position,
                barriers=shielding_segments,
            )
            reflection = build_reflection_context(
                receiver_pos=poi_position,
                source_pos=vehicle_position,
                barriers=shielding_segments,
            )
            diffraction = build_diffraction_context(shielding)
            material = None
            if shielding is not None:
                material = MaterialContext(
                    reflection_loss_db=shielding.reflection_loss_db,
                    diffraction_loss_db=shielding.diffraction_loss_db,
                    absorption_coefficient=shielding.absorption_coefficient,
                    allows_reflection=shielding.allows_reflection,
                    allows_diffraction=shielding.allows_diffraction,
                )
            if shielding is None and reflection is None and diffraction is None and material is None:
                return None
            return PropagationContext(
                shielding=shielding,
                reflection=reflection,
                diffraction=diffraction,
                material=material,
            )

        return provider