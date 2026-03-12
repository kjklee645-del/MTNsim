from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
import csv
import json

from mtnsim.acoustics.field.noise_grid import update_noise_grid_cpu, update_noise_grid_gpu
from mtnsim.acoustics.propagation.diffraction import DEFAULT_DIFFRACTION_SETTINGS, DiffractionModelSettings
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
    cache: OrderedDict[int, list[HeatmapCell]] = field(default_factory=OrderedDict)
    cache_limit: int = 24


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
        )

    def compute_dynamic_heatmap(
        self,
        context: DynamicHeatmapContext | None,
        frame: PlaybackFrame | None,
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

    def _parse_cell_id(self, cell_id: str) -> tuple[float, float] | None:
        if not str(cell_id).startswith('poi_'):
            return None
        try:
            _, x_str, y_str = str(cell_id).split('_', 2)
            return float(x_str), float(y_str)
        except ValueError:
            return None

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
