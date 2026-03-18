from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import csv
from typing import Callable
import random
import json
from pathlib import Path
from uuid import uuid4

from mtnsim.acoustics.field.noise_grid import update_noise_grid_cpu, update_noise_grid_gpu
from mtnsim.acoustics.propagation.diffraction import DEFAULT_DIFFRACTION_SETTINGS, DiffractionModelSettings
from mtnsim.acoustics.propagation.provider import SceneAwarePropagationProvider
from mtnsim.acoustics.propagation.reflection import DEFAULT_REFLECTION_SETTINGS, ReflectionModelSettings
from mtnsim.acoustics.propagation.shielding import BarrierSegment
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
    vehicle_trace_file: Path | None = None


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

    def run_simulation(
        self,
        context: RunContext,
        use_gpu: bool = True,
        progress_callback: Callable[[dict], None] | None = None,
        record_vehicle_trace: bool = False,
    ) -> SimulationArtifacts:
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

        self._emit_progress(progress_callback, 1, "Preparing simulation context", run_id=context.run_id, output_dir=str(output_dir))

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
        reflection_settings = self._resolve_reflection_settings(context.scenario)
        diffraction_settings = self._resolve_diffraction_settings(context.scenario)
        propagation_provider = self._build_propagation_provider(
            scene_model=scene_model,
            shielding_segments=shielding_segments,
            reflection_settings=reflection_settings,
            diffraction_settings=diffraction_settings,
        )
        effective_use_gpu = use_gpu

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
        vehicle_trace_file = output_dir / 'vehicle_trace.csv' if record_vehicle_trace else None
        random.seed(context.project.simulation_defaults.random_seed)

        try:
            sim.start(sumo_config_path, seed=context.project.simulation_defaults.random_seed)
            self._emit_progress(progress_callback, 3, "SUMO started")
            progress_interval = max(1, context.project.simulation_defaults.max_steps // 20)
            trace_writer = None
            trace_handle = None
            if vehicle_trace_file is not None:
                trace_handle = vehicle_trace_file.open('w', newline='', encoding='utf-8')
                trace_writer = csv.writer(trace_handle)
                trace_writer.writerow(['time_index', 'sim_time_seconds', 'vehicle_id', 'vehicle_type', 'x', 'y', 'speed_mps'])
            try:
                for time_step in range(context.project.simulation_defaults.max_steps):
                    if deployed_vehicles < context.scenario.traffic.max_vehicles:
                        add_vehicle(sim, lane_state, deployed_vehicles, time_step, deployment_config, constant_speed=start_speed_mps)
                        deployed_vehicles += 1

                    sim.simulation_step()
                    snapshots = sim.snapshots()
                    sim_time_seconds = sim.simulation_time()

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
                        if trace_writer is not None:
                            trace_writer.writerow(
                                [
                                    time_step,
                                    f"{sim_time_seconds:.3f}",
                                    snapshot.vehicle_id,
                                    snapshot.vehicle_type,
                                    f"{snapshot.position[0]:.3f}",
                                    f"{snapshot.position[1]:.3f}",
                                    f"{snapshot.speed_mps:.3f}",
                                ]
                            )

                    engine = update_noise_grid_gpu if effective_use_gpu else update_noise_grid_cpu
                    should_compute_grid = context.project.outputs.store_grid_timeseries or (time_step == context.project.simulation_defaults.max_steps - 1)
                    if should_compute_grid:
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

                    if (time_step + 1) == context.project.simulation_defaults.max_steps or ((time_step + 1) % progress_interval == 0):
                        percent = int(((time_step + 1) / context.project.simulation_defaults.max_steps) * 100)
                        self._emit_progress(
                            progress_callback,
                            percent,
                            f"Running step {time_step + 1}/{context.project.simulation_defaults.max_steps}",
                        )
            finally:
                if trace_handle is not None:
                    trace_handle.close()
        finally:
            sim.close()

        run_summary = self.summarize(context)
        manifest_file = write_run_manifest(output_dir, run_summary)
        receiver_files = write_receiver_histories(output_dir, receiver_histories)
        grid_snapshot_file = output_dir / 'grid_final_snapshot.json'
        grid_snapshot_file.write_text(json.dumps(final_grid_snapshot, indent=2), encoding='utf-8')

        result_summary = RunResultSummary(
            run=run_summary,
            output_dir=str(output_dir),
            manifest_file=str(manifest_file),
            receiver_history_files={key: str(value) for key, value in receiver_files.items()},
            final_grid_snapshot_file=str(grid_snapshot_file) if grid_snapshot_file else None,
            vehicle_trace_file=str(vehicle_trace_file) if vehicle_trace_file and vehicle_trace_file.exists() else None,
            used_gpu=effective_use_gpu,
            receiver_stats=self._build_receiver_stats(receiver_histories),
            propagation_features={
                'shielding_enabled': bool(shielding_segments),
                'reflection_enabled': bool(shielding_segments),
                'diffraction_enabled': bool(shielding_segments),
                'shielding_segment_count': len(shielding_segments),
                'noise_barrier_count': len(scene_model.noise_barriers),
                'terrain_edge_count': len(scene_model.terrain_edges),
                'building_count': len(scene_model.buildings),
                'ground_surface_count': len(scene_model.ground_surfaces),
                'vegetation_zone_count': len(scene_model.vegetation_zones),
                'scene_object_count': len(scene_model.objects),
                'gpu_requested': use_gpu,
                'gpu_used': effective_use_gpu,
                'reflection_model_settings': asdict(reflection_settings),
                'diffraction_model_settings': asdict(diffraction_settings),
            },
        )
        result_summary_file = write_run_result_summary(output_dir, result_summary)

        self._emit_progress(
            progress_callback,
            100,
            "Simulation completed",
            run_id=context.run_id,
            output_dir=str(output_dir),
            result_summary_file=str(result_summary_file),
        )

        return SimulationArtifacts(
            run_id=context.run_id,
            output_dir=output_dir,
            receiver_history_files=receiver_files,
            manifest_file=manifest_file,
            result_summary_file=result_summary_file,
            run_summary=run_summary,
            result_summary=result_summary,
            final_grid_snapshot_file=grid_snapshot_file,
            vehicle_trace_file=vehicle_trace_file if vehicle_trace_file and vehicle_trace_file.exists() else None,
        )

    def _emit_progress(self, callback: Callable[[dict], None] | None, percent: int, message: str, **extra) -> None:
        if callback is None:
            return
        payload = {'percent': int(percent), 'message': message}
        payload.update(extra)
        callback(payload)

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
        grid_config = context.scenario.grid
        use_override = (
            bool(grid_config.override_enabled)
            and grid_config.override_min_x is not None
            and grid_config.override_max_x is not None
            and grid_config.override_min_y is not None
            and grid_config.override_max_y is not None
        )
        domain_min_x = float(grid_config.override_min_x) if use_override else min_x
        domain_min_y = float(grid_config.override_min_y) if use_override else min_y
        domain_max_x = float(grid_config.override_max_x) if use_override else max_x
        domain_max_y = float(grid_config.override_max_y) if use_override else max_y
        domain = GridDomain(
            min_x=domain_min_x,
            min_y=domain_min_y,
            max_x=domain_max_x,
            max_y=domain_max_y,
            grid_size=context.scenario.noise.grid_size_meters,
        )
        if use_override:
            iterator = domain.iter_points_within_bounds()
        else:
            iterator = domain.iter_points(
                grid_config.margin_x_start,
                grid_config.margin_x_end,
                grid_config.extra_y_extent,
            )
        for x, y in iterator:
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

    def _resolve_reflection_settings(self, scenario: ScenarioConfig) -> ReflectionModelSettings:
        config = scenario.propagation_model.reflection
        overrides = {key: value for key, value in asdict(config).items() if value is not None}
        if not overrides:
            return DEFAULT_REFLECTION_SETTINGS
        return replace(DEFAULT_REFLECTION_SETTINGS, **overrides)

    def _resolve_diffraction_settings(self, scenario: ScenarioConfig) -> DiffractionModelSettings:
        config = scenario.propagation_model.diffraction
        overrides = {key: value for key, value in asdict(config).items() if value is not None}
        if not overrides:
            return DEFAULT_DIFFRACTION_SETTINGS
        return replace(DEFAULT_DIFFRACTION_SETTINGS, **overrides)

    def _build_propagation_provider(
        self,
        scene_model,
        shielding_segments: list[BarrierSegment],
        reflection_settings: ReflectionModelSettings,
        diffraction_settings: DiffractionModelSettings,
    ):
        if not shielding_segments:
            return None

        return SceneAwarePropagationProvider(
            scene_model=scene_model,
            reflection_settings=reflection_settings,
            diffraction_settings=diffraction_settings,
        )
