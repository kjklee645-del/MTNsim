from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tomllib


@dataclass(slots=True)
class Receiver:
    id: str
    x: float
    y: float
    z: float


@dataclass(slots=True)
class PropagationProperties:
    reflection_loss_db: float | None = None
    diffraction_loss_db: float | None = None
    absorption_coefficient: float | None = None
    allows_reflection: bool | None = None
    allows_diffraction: bool | None = None


@dataclass(slots=True)
class ReflectionModelConfig:
    max_extra_path_meters: float | None = None
    max_nearest_offset_meters: float | None = None
    min_normal_alignment: float | None = None
    centrality_floor: float | None = None
    centrality_weight: float | None = None
    extra_path_scale_meters: float | None = None
    source_distance_scale_meters: float | None = None
    receiver_distance_scale_meters: float | None = None
    energy_scale: float | None = None
    max_gain_db: float | None = None


@dataclass(slots=True)
class DiffractionModelConfig:
    wavelength_meters: float | None = None
    height_penalty_scale: float | None = None
    height_penalty_cap_db: float | None = None
    min_remaining_attenuation_db: float | None = None


@dataclass(slots=True)
class PropagationModelConfig:
    reflection: ReflectionModelConfig = field(default_factory=ReflectionModelConfig)
    diffraction: DiffractionModelConfig = field(default_factory=DiffractionModelConfig)


@dataclass(slots=True)
class NoiseBarrier:
    id: str
    x1: float
    y1: float
    x2: float
    y2: float
    height_meters: float
    attenuation_db: float
    material: str = "generic"
    propagation: PropagationProperties = field(default_factory=PropagationProperties)


@dataclass(slots=True)
class TerrainEdge:
    id: str
    x1: float
    y1: float
    x2: float
    y2: float
    height_meters: float
    attenuation_db: float
    material: str = "soil"
    propagation: PropagationProperties = field(default_factory=PropagationProperties)


@dataclass(slots=True)
class Building:
    id: str
    footprint: list[tuple[float, float]]
    height_meters: float
    attenuation_db: float
    material: str = "generic"
    propagation: PropagationProperties = field(default_factory=PropagationProperties)


@dataclass(slots=True)
class GroundSurface:
    id: str
    footprint: list[tuple[float, float]]
    material: str = "grass"
    propagation: PropagationProperties = field(default_factory=PropagationProperties)


@dataclass(slots=True)
class VegetationZone:
    id: str
    footprint: list[tuple[float, float]]
    height_meters: float
    attenuation_db: float
    material: str = "generic"
    propagation: PropagationProperties = field(default_factory=PropagationProperties)


@dataclass(slots=True)
class SceneConfig:
    noise_barriers: list[NoiseBarrier] = field(default_factory=list)
    terrain_edges: list[TerrainEdge] = field(default_factory=list)
    buildings: list[Building] = field(default_factory=list)
    ground_surfaces: list[GroundSurface] = field(default_factory=list)
    vegetation_zones: list[VegetationZone] = field(default_factory=list)


@dataclass(slots=True)
class ScenarioInfo:
    name: str
    project: str
    description: str = ""


@dataclass(slots=True)
class TrafficConfig:
    max_vehicles: int
    vehicle_types: list[str]
    vehicle_weights: list[float]
    start_mode: str
    vehicle_interval_seconds: float
    start_speed_kmh: float
    route_types: list[str]


@dataclass(slots=True)
class ControlConfig:
    lane_change_mode: str
    lane_change_ratio: float
    lane_change_strategy: str
    lane_change_force_change: bool
    lane_change_check_radius_meters: float
    lane_change_restore_time_seconds: float
    target_lane_index: int
    designated_lane: int
    lane_change_target_positions: list[tuple[float, float]]
    post_distance_speed_control: bool
    post_distance_meters: float
    post_target_speed_kmh: float
    lane_change_constant_speed_kmh: float | None = None
    lane_change_speed_change_mps: float | None = None


@dataclass(slots=True)
class VehicleNoiseCoefficient:
    a: float
    b: float


@dataclass(slots=True)
class NoiseConfig:
    background_noise_db: float
    max_area_meters: float
    grid_size_meters: float
    receiver_height_meters: float
    vehicle_coefficients: dict[str, VehicleNoiseCoefficient]


@dataclass(slots=True)
class GridConfig:
    margin_x_start: float
    margin_x_end: float
    extra_y_extent: float
    override_enabled: bool = False
    override_min_x: float | None = None
    override_max_x: float | None = None
    override_min_y: float | None = None
    override_max_y: float | None = None


@dataclass(slots=True)
class ScenarioConfig:
    scenario: ScenarioInfo
    traffic: TrafficConfig
    controls: ControlConfig
    noise: NoiseConfig
    grid: GridConfig
    receivers: list[Receiver]
    scene: SceneConfig = field(default_factory=SceneConfig)
    propagation_model: PropagationModelConfig = field(default_factory=PropagationModelConfig)
    source_path: Path | None = None

    @classmethod
    def from_dict(cls, data: dict, source_path: str | Path | None = None) -> "ScenarioConfig":
        coeffs = {
            key: VehicleNoiseCoefficient(**value)
            for key, value in data["noise"]["vehicle_coefficients"].items()
        }
        noise_data = dict(data["noise"])
        noise_data["vehicle_coefficients"] = coeffs
        control_data = dict(data["controls"])
        control_data["lane_change_target_positions"] = [tuple(item) for item in control_data.get("lane_change_target_positions", [])]
        scene_data = data.get("scene") or {}
        propagation_model_data = data.get("propagation_model") or {}
        reflection_data = propagation_model_data.get("reflection") or {}
        diffraction_data = propagation_model_data.get("diffraction") or {}
        legacy_barriers = [cls._parse_noise_barrier(item) for item in scene_data.get("barriers", [])]
        declared_noise_barriers = [cls._parse_noise_barrier(item) for item in scene_data.get("noise_barriers", [])]
        terrain_edges = [cls._parse_terrain_edge(item) for item in scene_data.get("terrain_edges", [])]
        buildings = [cls._parse_building(item) for item in scene_data.get("buildings", [])]
        ground_surfaces = [cls._parse_ground_surface(item) for item in scene_data.get("ground_surfaces", [])]
        vegetation_zones = [cls._parse_vegetation_zone(item) for item in scene_data.get("vegetation_zones", [])]
        return cls(
            scenario=ScenarioInfo(**data["scenario"]),
            traffic=TrafficConfig(**data["traffic"]),
            controls=ControlConfig(**control_data),
            noise=NoiseConfig(**noise_data),
            grid=GridConfig(**data["grid"]),
            receivers=[Receiver(**item) for item in data["receivers"]],
            scene=SceneConfig(
                noise_barriers=[*legacy_barriers, *declared_noise_barriers],
                terrain_edges=terrain_edges,
                buildings=buildings,
                ground_surfaces=ground_surfaces,
                vegetation_zones=vegetation_zones,
            ),
            propagation_model=PropagationModelConfig(
                reflection=ReflectionModelConfig(**reflection_data),
                diffraction=DiffractionModelConfig(**diffraction_data),
            ),
            source_path=Path(source_path) if source_path is not None else None,
        )

    @staticmethod
    def _parse_noise_barrier(data: dict) -> NoiseBarrier:
        payload = dict(data)
        propagation = PropagationProperties(**payload.pop("propagation", {}))
        return NoiseBarrier(propagation=propagation, **payload)

    @staticmethod
    def _parse_terrain_edge(data: dict) -> TerrainEdge:
        payload = dict(data)
        propagation = PropagationProperties(**payload.pop("propagation", {}))
        return TerrainEdge(propagation=propagation, **payload)

    @staticmethod
    def _parse_building(data: dict) -> Building:
        payload = dict(data)
        propagation = PropagationProperties(**payload.pop("propagation", {}))
        footprint = [tuple(point) for point in payload.pop("footprint", [])]
        return Building(footprint=footprint, propagation=propagation, **payload)

    @staticmethod
    def _parse_ground_surface(data: dict) -> GroundSurface:
        payload = dict(data)
        propagation = PropagationProperties(**payload.pop("propagation", {}))
        footprint = [tuple(point) for point in payload.pop("footprint", [])]
        return GroundSurface(footprint=footprint, propagation=propagation, **payload)

    @staticmethod
    def _parse_vegetation_zone(data: dict) -> VegetationZone:
        payload = dict(data)
        propagation = PropagationProperties(**payload.pop("propagation", {}))
        footprint = [tuple(point) for point in payload.pop("footprint", [])]
        return VegetationZone(footprint=footprint, propagation=propagation, **payload)

    @classmethod
    def load(cls, path: str | Path) -> "ScenarioConfig":
        path = Path(path)
        with path.open("rb") as handle:
            data = tomllib.load(handle)
        return cls.from_dict(data, source_path=path)
