from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tomllib

from mtnsim.security.exceptions import ConfigValidationError
from mtnsim.security.validators import (
    ensure_member,
    ensure_non_empty_sequence,
    ensure_non_empty_string,
    ensure_non_negative_number,
    ensure_positive_number,
    ensure_ratio,
    ensure_same_length,
    ensure_unique_strings,
)


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
class DirectivityConfig:
    preset: str = "custom"
    mode: str = "isotropic"
    response_profile: str = "physical"
    strength_db: float = 6.0
    wedge_angle_deg: float = 70.0
    vertical_strength_db: float = 0.0
    vertical_angle_deg: float = 55.0


@dataclass(slots=True)
class NoiseConfig:
    background_noise_db: float
    max_area_meters: float
    grid_size_meters: float
    receiver_height_meters: float
    vehicle_coefficients: dict[str, VehicleNoiseCoefficient]
    directivity: DirectivityConfig = field(default_factory=DirectivityConfig)


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
        try:
            coeffs = {
                key: VehicleNoiseCoefficient(**value)
                for key, value in data["noise"]["vehicle_coefficients"].items()
            }
            noise_data = dict(data["noise"])
            directivity_data = noise_data.pop("directivity", {})
            if "response_profile" not in directivity_data:
                preset = str(directivity_data.get("preset", "custom") or "custom")
                mode = str(directivity_data.get("mode", "isotropic") or "isotropic")
                directivity_data["response_profile"] = (
                    "enhanced" if preset != "custom" and mode != "isotropic" else "physical"
                )
            noise_data["vehicle_coefficients"] = coeffs
            noise_data["directivity"] = DirectivityConfig(**directivity_data)
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
            scenario = cls(
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
                source_path=Path(source_path).expanduser().resolve() if source_path is not None else None,
            )
        except KeyError as exc:
            raise ConfigValidationError(f"Scenario config is missing required field: {exc}") from exc
        except (TypeError, ValueError) as exc:
            raise ConfigValidationError(f"Scenario config is invalid: {exc}") from exc
        scenario.validate()
        return scenario

    def validate(self) -> None:
        ensure_non_empty_string(self.scenario.name, "scenario.name")
        ensure_non_empty_string(self.scenario.project, "scenario.project")

        ensure_non_negative_number(self.traffic.max_vehicles, "traffic.max_vehicles")
        ensure_non_empty_sequence(self.traffic.vehicle_types, "traffic.vehicle_types")
        ensure_non_empty_sequence(self.traffic.vehicle_weights, "traffic.vehicle_weights")
        ensure_same_length(self.traffic.vehicle_types, self.traffic.vehicle_weights, "traffic.vehicle_types and traffic.vehicle_weights")
        ensure_non_empty_sequence(self.traffic.route_types, "traffic.route_types")
        ensure_member(self.traffic.start_mode, {"interval", "random"}, "traffic.start_mode")
        ensure_positive_number(self.traffic.vehicle_interval_seconds, "traffic.vehicle_interval_seconds")
        ensure_non_negative_number(self.traffic.start_speed_kmh, "traffic.start_speed_kmh")
        for index, vehicle_type in enumerate(self.traffic.vehicle_types):
            ensure_non_empty_string(str(vehicle_type), f"traffic.vehicle_types[{index}]")
        for index, weight in enumerate(self.traffic.vehicle_weights):
            ensure_non_negative_number(weight, f"traffic.vehicle_weights[{index}]")
        if sum(float(weight) for weight in self.traffic.vehicle_weights) <= 0:
            raise ConfigValidationError("traffic.vehicle_weights must contain a positive total weight.")

        ensure_member(self.controls.lane_change_mode, {"disable", "enforce"}, "controls.lane_change_mode")
        ensure_member(self.controls.lane_change_strategy, {"fixed", "variable", "custom", "random"}, "controls.lane_change_strategy")
        ensure_ratio(self.controls.lane_change_ratio, "controls.lane_change_ratio")
        ensure_non_negative_number(self.controls.lane_change_check_radius_meters, "controls.lane_change_check_radius_meters")
        ensure_non_negative_number(self.controls.lane_change_restore_time_seconds, "controls.lane_change_restore_time_seconds")
        ensure_non_negative_number(self.controls.target_lane_index, "controls.target_lane_index")
        ensure_non_negative_number(self.controls.designated_lane, "controls.designated_lane")
        ensure_non_negative_number(self.controls.post_distance_meters, "controls.post_distance_meters")
        ensure_non_negative_number(self.controls.post_target_speed_kmh, "controls.post_target_speed_kmh")
        if self.controls.lane_change_constant_speed_kmh is not None:
            ensure_non_negative_number(self.controls.lane_change_constant_speed_kmh, "controls.lane_change_constant_speed_kmh")
        if self.controls.lane_change_strategy == "custom":
            ensure_non_empty_sequence(self.controls.lane_change_target_positions, "controls.lane_change_target_positions")
        for index, point in enumerate(self.controls.lane_change_target_positions):
            self._validate_point(point, f"controls.lane_change_target_positions[{index}]")

        ensure_positive_number(self.noise.max_area_meters, "noise.max_area_meters")
        ensure_positive_number(self.noise.grid_size_meters, "noise.grid_size_meters")
        ensure_positive_number(self.noise.receiver_height_meters, "noise.receiver_height_meters")
        ensure_member(self.noise.directivity.mode, {"isotropic", "wedge", "dual_wedge"}, "noise.directivity.mode")
        ensure_member(self.noise.directivity.response_profile, {"physical", "enhanced"}, "noise.directivity.response_profile")
        ensure_positive_number(self.noise.directivity.wedge_angle_deg, "noise.directivity.wedge_angle_deg")
        ensure_positive_number(self.noise.directivity.vertical_angle_deg, "noise.directivity.vertical_angle_deg")
        if self.noise.directivity.wedge_angle_deg > 360:
            raise ConfigValidationError("noise.directivity.wedge_angle_deg must be less than or equal to 360.")
        if self.noise.directivity.vertical_angle_deg > 360:
            raise ConfigValidationError("noise.directivity.vertical_angle_deg must be less than or equal to 360.")
        ensure_non_empty_sequence(self.noise.vehicle_coefficients, "noise.vehicle_coefficients")
        for vehicle_type in self.traffic.vehicle_types:
            if vehicle_type not in self.noise.vehicle_coefficients:
                raise ConfigValidationError(f"noise.vehicle_coefficients is missing an entry for vehicle type '{vehicle_type}'.")
            coefficient = self.noise.vehicle_coefficients[vehicle_type]
            self._validate_number(coefficient.a, f"noise.vehicle_coefficients[{vehicle_type}].a")
            self._validate_number(coefficient.b, f"noise.vehicle_coefficients[{vehicle_type}].b")

        ensure_non_negative_number(self.grid.margin_x_start, "grid.margin_x_start")
        ensure_non_negative_number(self.grid.margin_x_end, "grid.margin_x_end")
        ensure_non_negative_number(self.grid.extra_y_extent, "grid.extra_y_extent")
        if self.grid.override_enabled:
            override_values = (
                self.grid.override_min_x,
                self.grid.override_max_x,
                self.grid.override_min_y,
                self.grid.override_max_y,
            )
            if any(value is None for value in override_values):
                raise ConfigValidationError("grid override bounds must all be provided when grid.override_enabled is true.")
            if float(self.grid.override_min_x) >= float(self.grid.override_max_x):
                raise ConfigValidationError("grid.override_min_x must be less than grid.override_max_x.")
            if float(self.grid.override_min_y) >= float(self.grid.override_max_y):
                raise ConfigValidationError("grid.override_min_y must be less than grid.override_max_y.")

        ensure_non_empty_sequence(self.receivers, "receivers")
        receiver_ids = []
        for index, receiver in enumerate(self.receivers):
            ensure_non_empty_string(receiver.id, f"receivers[{index}].id")
            self._validate_number(receiver.x, f"receivers[{index}].x")
            self._validate_number(receiver.y, f"receivers[{index}].y")
            self._validate_number(receiver.z, f"receivers[{index}].z", non_negative=True)
            receiver_ids.append(receiver.id)
        ensure_unique_strings(receiver_ids, "receivers")

        for collection_name, items in (
            ("scene.noise_barriers", self.scene.noise_barriers),
            ("scene.terrain_edges", self.scene.terrain_edges),
        ):
            for index, item in enumerate(items):
                ensure_non_empty_string(item.id, f"{collection_name}[{index}].id")
                ensure_non_negative_number(item.height_meters, f"{collection_name}[{index}].height_meters")
        for collection_name, items in (
            ("scene.buildings", self.scene.buildings),
            ("scene.ground_surfaces", self.scene.ground_surfaces),
            ("scene.vegetation_zones", self.scene.vegetation_zones),
        ):
            for index, item in enumerate(items):
                ensure_non_empty_string(item.id, f"{collection_name}[{index}].id")
                if hasattr(item, "height_meters"):
                    ensure_non_negative_number(item.height_meters, f"{collection_name}[{index}].height_meters")
                if len(item.footprint) < 3:
                    raise ConfigValidationError(f"{collection_name}[{index}].footprint must contain at least three points.")
                for point_index, point in enumerate(item.footprint):
                    self._validate_point(point, f"{collection_name}[{index}].footprint[{point_index}]")

    @staticmethod
    def _validate_point(point: tuple[float, float], label: str) -> None:
        if len(point) != 2:
            raise ConfigValidationError(f"{label} must contain exactly two coordinates.")
        for index, value in enumerate(point):
            ScenarioConfig._validate_number(value, f"{label}[{index}]")

    @staticmethod
    def _validate_number(value: float, label: str, *, non_negative: bool = False) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigValidationError(f"{label} must be numeric.")
        if non_negative and value < 0:
            raise ConfigValidationError(f"{label} must be greater than or equal to 0.")

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
        path = Path(path).expanduser().resolve()
        try:
            with path.open("rb") as handle:
                data = tomllib.load(handle)
        except tomllib.TOMLDecodeError as exc:
            raise ConfigValidationError(f"Scenario TOML is invalid: {path}") from exc
        return cls.from_dict(data, source_path=path)
