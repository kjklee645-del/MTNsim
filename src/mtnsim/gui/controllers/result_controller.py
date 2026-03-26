from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
import csv
import json
import math

from mtnsim.acoustics.emission.road_vehicle import calculate_3d_distance, directional_gain_db, resolve_heading_vector
from mtnsim.acoustics.field.noise_grid import update_noise_grid_cpu, update_noise_grid_gpu
from mtnsim.acoustics.propagation.correction import total_propagation_correction_db
from mtnsim.acoustics.propagation.diffraction import DEFAULT_DIFFRACTION_SETTINGS, DiffractionModelSettings
from mtnsim.acoustics.propagation.distance import free_field_attenuation_db
from mtnsim.acoustics.propagation.provider import SceneAwarePropagationProvider
from mtnsim.acoustics.propagation.reflection import DEFAULT_REFLECTION_SETTINGS, ReflectionModelSettings
from mtnsim.scene import build_scene_model
from mtnsim.schemas.project import ProjectManifest
from mtnsim.schemas.results import RunResultSummary
from mtnsim.schemas.scenario import ScenarioConfig
from mtnsim.gui.controllers.playback_controller import PlaybackFrame


@dataclass(slots=True)
class ReceiverSeries:
    receiver_id: str
    points: list[tuple[int, float]]


@dataclass(slots=True)
class HeatmapCell:
    x: float
    y: float
    value_db: float


@dataclass(slots=True)
class DynamicHeatmapContext:
    grid_positions: dict[str, tuple[float, float, float]]
    coefficients: dict[str, tuple[float, float]]
    background_noise_db: float
    max_area_meters: float
    propagation_provider: object | None
    use_gpu: bool
    directivity_mode: str = 'isotropic'
    directivity_response_profile: str = 'physical'
    directivity_strength_db: float = 6.0
    directivity_wedge_angle_deg: float = 70.0
    directivity_vertical_strength_db: float = 0.0
    directivity_vertical_angle_deg: float = 55.0
    cache: OrderedDict[int, list[HeatmapCell]] = field(default_factory=OrderedDict)
    cache_limit: int = 72


class ResultController:
    def load_result_summary(self, result_summary_path: str | Path) -> RunResultSummary:
        return RunResultSummary.load(result_summary_path)

    def load_receiver_series(self, receiver_id: str, csv_path: str | Path) -> ReceiverSeries:
        points: list[tuple[int, float]] = []
        with Path(csv_path).open('r', encoding='utf-8', newline='') as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                points.append((int(row['time_index']), float(row['value_db'])))
        return ReceiverSeries(receiver_id=receiver_id, points=points)

    def load_heatmap_cells(self, snapshot_path: str | Path | None) -> list[HeatmapCell]:
        if snapshot_path is None:
            return []
        path = Path(snapshot_path)
        if not path.exists():
            return []
        raw = json.loads(path.read_text(encoding='utf-8'))
        cells: list[HeatmapCell] = []
        for cell_id, value in raw.items():
            parsed = self._parse_cell_id(cell_id)
            if parsed is None:
                continue
            x, y = parsed
            cells.append(HeatmapCell(x=x, y=y, value_db=float(value)))
        return cells

    def build_dynamic_heatmap_context(
        self,
        project: ProjectManifest,
        scenario: ScenarioConfig,
        result_summary: RunResultSummary,
    ) -> DynamicHeatmapContext | None:
        base_cells = self.load_heatmap_cells(result_summary.final_grid_snapshot_file)
        if not base_cells:
            return None
        grid_positions = {
            f'poi_{cell.x}_{cell.y}': (cell.x, cell.y, scenario.noise.receiver_height_meters)
            for cell in base_cells
        }
        coefficients = {
            vehicle_type: (profile.a, profile.b)
            for vehicle_type, profile in scenario.noise.vehicle_coefficients.items()
        }
        scene_model = build_scene_model(scenario.scene)
        shielding_segments = scene_model.to_shielding_segments()
        propagation_provider = None
        if shielding_segments:
            propagation_provider = SceneAwarePropagationProvider(
                scene_model=scene_model,
                reflection_settings=self._resolve_reflection_settings(scenario),
                diffraction_settings=self._resolve_diffraction_settings(scenario),
            )
        return DynamicHeatmapContext(
            grid_positions=grid_positions,
            coefficients=coefficients,
            background_noise_db=scenario.noise.background_noise_db,
            max_area_meters=scenario.noise.max_area_meters,
            propagation_provider=propagation_provider,
            use_gpu=result_summary.used_gpu,
            directivity_mode=scenario.noise.directivity.mode,
            directivity_response_profile=scenario.noise.directivity.response_profile,
            directivity_strength_db=scenario.noise.directivity.strength_db,
            directivity_wedge_angle_deg=scenario.noise.directivity.wedge_angle_deg,
            directivity_vertical_strength_db=scenario.noise.directivity.vertical_strength_db,
            directivity_vertical_angle_deg=scenario.noise.directivity.vertical_angle_deg,
        )

    def compute_dynamic_heatmap(
        self,
        context: DynamicHeatmapContext | None,
        frame: PlaybackFrame | None,
        dataset=None,
        frame_index: int | None = None,
    ) -> list[HeatmapCell]:
        if context is None or frame is None:
            return []
        cached = context.cache.get(frame.time_index)
        if cached is not None:
            context.cache.move_to_end(frame.time_index)
            return cached

        vehicle_positions = {vehicle.vehicle_id: (vehicle.x, vehicle.y) for vehicle in frame.vehicles}
        vehicle_types = {vehicle.vehicle_id: vehicle.vehicle_type for vehicle in frame.vehicles}
        vehicle_speeds = {vehicle.vehicle_id: vehicle.speed_mps for vehicle in frame.vehicles}
        vehicle_headings = self._build_vehicle_headings(dataset, frame_index, frame)
        engine = update_noise_grid_gpu if context.use_gpu else update_noise_grid_cpu
        values = engine(
            context.grid_positions,
            vehicle_positions,
            vehicle_types,
            vehicle_speeds,
            context.coefficients,
            context.background_noise_db,
            context.max_area_meters,
            context.propagation_provider,
            vehicle_headings,
            self._build_directivity_proxy(context),
        )
        cells = [
            HeatmapCell(x=position[0], y=position[1], value_db=float(values[cell_id]))
            for cell_id, position in context.grid_positions.items()
        ]
        context.cache[frame.time_index] = cells
        context.cache.move_to_end(frame.time_index)
        while len(context.cache) > context.cache_limit:
            context.cache.popitem(last=False)
        return cells

    def prefetch_dynamic_heatmap_frames(
        self,
        context: DynamicHeatmapContext | None,
        dataset,
        frame_indices: list[int],
        max_frames: int | None = None,
    ) -> list[int]:
        if context is None:
            return []
        prefetched: list[int] = []
        if dataset is None:
            return prefetched
        for frame_index in frame_indices:
            if frame_index < 0 or frame_index >= dataset.frame_count:
                continue
            frame = dataset.frames[frame_index]
            if frame.time_index in context.cache:
                context.cache.move_to_end(frame.time_index)
                continue
            self.compute_dynamic_heatmap(context, frame, dataset=dataset, frame_index=frame_index)
            prefetched.append(frame.time_index)
            if max_frames is not None and len(prefetched) >= max_frames:
                break
        return prefetched


    def compute_vehicle_contribution_heatmap(
        self,
        context: DynamicHeatmapContext | None,
        frame: PlaybackFrame | None,
        vehicle_id: str | None,
        dataset=None,
        frame_index: int | None = None,
    ) -> list[HeatmapCell]:
        if context is None or frame is None or not vehicle_id:
            return []
        values = self._compute_vehicle_contribution_values(context, context.grid_positions, frame, vehicle_id, dataset=dataset, frame_index=frame_index)
        return [
            HeatmapCell(x=position[0], y=position[1], value_db=float(values.get(cell_id, 0.0)))
            for cell_id, position in context.grid_positions.items()
        ]

    def compute_vehicle_receiver_contributions(
        self,
        context: DynamicHeatmapContext | None,
        frame: PlaybackFrame | None,
        vehicle_id: str | None,
        receiver_positions: dict[str, tuple[float, float, float]],
        dataset=None,
        frame_index: int | None = None,
    ) -> dict[str, float]:
        if context is None or frame is None or not vehicle_id:
            return {}
        return self._compute_vehicle_contribution_values(context, receiver_positions, frame, vehicle_id, dataset=dataset, frame_index=frame_index)

    def _compute_vehicle_contribution_values(
        self,
        context: DynamicHeatmapContext,
        positions: dict[str, tuple[float, float, float]],
        frame: PlaybackFrame,
        vehicle_id: str,
        dataset=None,
        frame_index: int | None = None,
    ) -> dict[str, float]:
        selected_vehicle = next((vehicle for vehicle in frame.vehicles if vehicle.vehicle_id == vehicle_id), None)
        if selected_vehicle is None:
            return {position_id: 0.0 for position_id in positions}
        coeff = context.coefficients.get(selected_vehicle.vehicle_type)
        if coeff is None:
            return {position_id: 0.0 for position_id in positions}

        vehicle_position = (selected_vehicle.x, selected_vehicle.y)
        speed = max(selected_vehicle.speed_mps, 0.1)
        a, b = coeff
        pwl = a + (b * math.log10(3.6 * speed))
        vehicle_headings = self._build_vehicle_headings(dataset, frame_index, frame)
        directivity = self._build_directivity_proxy(context)
        values: dict[str, float] = {}
        for position_id, position in positions.items():
            distance = calculate_3d_distance(position, vehicle_position)
            if distance > context.max_area_meters:
                values[position_id] = 0.0
                continue
            correction_db = 0.0
            provider = context.propagation_provider
            if provider is not None and hasattr(provider, 'correction_for_pair'):
                propagation_context = provider.correction_for_pair(position_id, position, selected_vehicle.vehicle_id, vehicle_position)
                correction_db = total_propagation_correction_db(propagation_context)
            directional_db = directional_gain_db(
                (position[0], position[1]),
                vehicle_position,
                vehicle_headings.get(selected_vehicle.vehicle_id),
                mode=directivity.mode,
                response_profile=directivity.response_profile,
                strength_db=directivity.strength_db,
                wedge_angle_deg=directivity.wedge_angle_deg,
                vertical_strength_db=directivity.vertical_strength_db,
                vertical_angle_deg=directivity.vertical_angle_deg,
            )
            attenuation_db = free_field_attenuation_db(distance)
            level_db = pwl + directional_db - attenuation_db + correction_db
            values[position_id] = max(0.0, float(level_db))
        return values

    def _parse_cell_id(self, cell_id: str) -> tuple[float, float] | None:
        if not str(cell_id).startswith('poi_'):
            return None
        try:
            _, x_str, y_str = str(cell_id).split('_', 2)
            return float(x_str), float(y_str)
        except ValueError:
            return None

    def _build_directivity_proxy(self, context: DynamicHeatmapContext):
        class _Directivity:
            pass
        proxy = _Directivity()
        proxy.mode = context.directivity_mode
        proxy.response_profile = context.directivity_response_profile
        proxy.strength_db = context.directivity_strength_db
        proxy.wedge_angle_deg = context.directivity_wedge_angle_deg
        proxy.vertical_strength_db = context.directivity_vertical_strength_db
        proxy.vertical_angle_deg = context.directivity_vertical_angle_deg
        return proxy

    def _build_vehicle_headings(self, dataset, frame_index: int | None, frame: PlaybackFrame | None) -> dict[str, tuple[float, float]]:
        if dataset is None or frame is None or frame_index is None or frame_index < 0 or frame_index >= dataset.frame_count:
            return {}
        previous_lookup = {vehicle.vehicle_id: vehicle for vehicle in dataset.frames[frame_index - 1].vehicles} if frame_index > 0 else {}
        next_lookup = {vehicle.vehicle_id: vehicle for vehicle in dataset.frames[frame_index + 1].vehicles} if frame_index + 1 < dataset.frame_count else {}
        headings: dict[str, tuple[float, float]] = {}
        for vehicle in frame.vehicles:
            heading = None
            previous_vehicle = previous_lookup.get(vehicle.vehicle_id)
            if previous_vehicle is not None:
                heading = resolve_heading_vector((previous_vehicle.x, previous_vehicle.y), (vehicle.x, vehicle.y))
            if heading is None:
                next_vehicle = next_lookup.get(vehicle.vehicle_id)
                if next_vehicle is not None:
                    heading = resolve_heading_vector((vehicle.x, vehicle.y), (next_vehicle.x, next_vehicle.y))
            if heading is not None:
                headings[vehicle.vehicle_id] = heading
        return headings

    def _resolve_reflection_settings(self, scenario: ScenarioConfig) -> ReflectionModelSettings:
        overrides = {key: value for key, value in asdict(scenario.propagation_model.reflection).items() if value is not None}
        if not overrides:
            return DEFAULT_REFLECTION_SETTINGS
        return replace(DEFAULT_REFLECTION_SETTINGS, **overrides)

    def _resolve_diffraction_settings(self, scenario: ScenarioConfig) -> DiffractionModelSettings:
        overrides = {key: value for key, value in asdict(scenario.propagation_model.diffraction).items() if value is not None}
        if not overrides:
            return DEFAULT_DIFFRACTION_SETTINGS
        return replace(DEFAULT_DIFFRACTION_SETTINGS, **overrides)
