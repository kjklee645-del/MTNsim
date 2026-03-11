from __future__ import annotations

from dataclasses import dataclass, field

from mtnsim.acoustics.propagation.shielding import BarrierSegment
from mtnsim.scene.materials import resolve_propagation_properties
from mtnsim.schemas.scenario import (
    Building,
    GroundSurface,
    NoiseBarrier,
    PropagationProperties,
    SceneConfig,
    TerrainEdge,
    VegetationZone,
)


@dataclass(slots=True)
class PropagationMaterial:
    name: str
    shielding_attenuation_db: float
    reflection_loss_db: float
    diffraction_loss_db: float
    absorption_coefficient: float
    allows_reflection: bool
    allows_diffraction: bool


@dataclass(slots=True)
class SceneObject:
    id: str
    object_type: str
    material: PropagationMaterial
    height_meters: float

    def to_shielding_segments(self) -> list[BarrierSegment]:
        return []


@dataclass(slots=True)
class LinearSceneObject(SceneObject):
    start_xy: tuple[float, float]
    end_xy: tuple[float, float]

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return _segment_bbox(self.start_xy, self.end_xy)

    def to_shielding_segments(self) -> list[BarrierSegment]:
        return [
            BarrierSegment(
                id=self.id,
                x1=self.start_xy[0],
                y1=self.start_xy[1],
                x2=self.end_xy[0],
                y2=self.end_xy[1],
                height_meters=self.height_meters,
                attenuation_db=self.material.shielding_attenuation_db,
                reflection_loss_db=self.material.reflection_loss_db,
                diffraction_loss_db=self.material.diffraction_loss_db,
                absorption_coefficient=self.material.absorption_coefficient,
                allows_reflection=self.material.allows_reflection,
                allows_diffraction=self.material.allows_diffraction,
            )
        ]


@dataclass(slots=True)
class PolygonSceneObject(SceneObject):
    footprint: list[tuple[float, float]] = field(default_factory=list)

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return _polygon_bbox(self.footprint)

    def to_shielding_segments(self) -> list[BarrierSegment]:
        if len(self.footprint) < 3:
            return []
        segments: list[BarrierSegment] = []
        for index, start_point in enumerate(self.footprint):
            end_point = self.footprint[(index + 1) % len(self.footprint)]
            segments.append(
                BarrierSegment(
                    id=f"{self.id}:edge:{index}",
                    x1=start_point[0],
                    y1=start_point[1],
                    x2=end_point[0],
                    y2=end_point[1],
                    height_meters=self.height_meters,
                    attenuation_db=self.material.shielding_attenuation_db,
                    reflection_loss_db=self.material.reflection_loss_db,
                    diffraction_loss_db=self.material.diffraction_loss_db,
                    absorption_coefficient=self.material.absorption_coefficient,
                    allows_reflection=self.material.allows_reflection,
                    allows_diffraction=self.material.allows_diffraction,
                )
            )
        return segments


@dataclass(slots=True)
class NoiseBarrierObject(LinearSceneObject):
    pass


@dataclass(slots=True)
class TerrainEdgeObject(LinearSceneObject):
    pass


@dataclass(slots=True)
class BuildingObject(PolygonSceneObject):
    pass


@dataclass(slots=True)
class GroundSurfaceObject(PolygonSceneObject):
    def to_shielding_segments(self) -> list[BarrierSegment]:
        return []

    def ground_correction_db(self, receiver_xy: tuple[float, float], source_xy: tuple[float, float]) -> float:
        if not _path_bbox_intersects_polygon(source_xy, receiver_xy, self.footprint):
            return 0.0
        coverage = _polygon_coverage_fraction(source_xy, receiver_xy, self.footprint)
        if coverage <= 0.0:
            return 0.0
        absorption = self.material.absorption_coefficient
        correction = ((0.28 - absorption) * 3.2) * coverage
        return _clamp(correction, -2.3, 0.9)


@dataclass(slots=True)
class VegetationZoneObject(PolygonSceneObject):
    attenuation_db: float = 0.0

    def to_shielding_segments(self) -> list[BarrierSegment]:
        return []

    def vegetation_correction_db(self, receiver_xy: tuple[float, float], source_xy: tuple[float, float]) -> float:
        if not _path_bbox_intersects_polygon(source_xy, receiver_xy, self.footprint):
            return 0.0
        coverage = _polygon_coverage_fraction(source_xy, receiver_xy, self.footprint)
        if coverage <= 0.0:
            return 0.0
        density_factor = 0.35 + (self.material.absorption_coefficient * 0.9) + min(self.height_meters / 10.0, 0.4)
        attenuation = self.attenuation_db * coverage * density_factor
        return -min(attenuation, 4.5)


@dataclass(slots=True)
class SceneModel:
    objects: list[SceneObject] = field(default_factory=list)
    _shielding_segments_cache: list[BarrierSegment] | None = field(default=None, init=False, repr=False)
    _shielding_segment_bboxes_cache: list[tuple[BarrierSegment, tuple[float, float, float, float]]] | None = field(default=None, init=False, repr=False)

    @property
    def noise_barriers(self) -> list[NoiseBarrierObject]:
        return [item for item in self.objects if isinstance(item, NoiseBarrierObject)]

    @property
    def terrain_edges(self) -> list[TerrainEdgeObject]:
        return [item for item in self.objects if isinstance(item, TerrainEdgeObject)]

    @property
    def buildings(self) -> list[BuildingObject]:
        return [item for item in self.objects if isinstance(item, BuildingObject)]

    @property
    def ground_surfaces(self) -> list[GroundSurfaceObject]:
        return [item for item in self.objects if isinstance(item, GroundSurfaceObject)]

    @property
    def vegetation_zones(self) -> list[VegetationZoneObject]:
        return [item for item in self.objects if isinstance(item, VegetationZoneObject)]

    @property
    def shielding_segments(self) -> list[BarrierSegment]:
        if self._shielding_segments_cache is None:
            segments: list[BarrierSegment] = []
            for item in self.objects:
                segments.extend(item.to_shielding_segments())
            self._shielding_segments_cache = segments
        return self._shielding_segments_cache

    @property
    def shielding_segment_bboxes(self) -> list[tuple[BarrierSegment, tuple[float, float, float, float]]]:
        if self._shielding_segment_bboxes_cache is None:
            self._shielding_segment_bboxes_cache = [
                (segment, _segment_bbox((segment.x1, segment.y1), (segment.x2, segment.y2)))
                for segment in self.shielding_segments
            ]
        return self._shielding_segment_bboxes_cache

    def to_shielding_segments(self) -> list[BarrierSegment]:
        return list(self.shielding_segments)

    def candidate_shielding_segments(self, receiver_xy: tuple[float, float], source_xy: tuple[float, float]) -> list[BarrierSegment]:
        path_bbox = _segment_bbox(source_xy, receiver_xy)
        return [segment for segment, bbox in self.shielding_segment_bboxes if _bbox_intersects(path_bbox, bbox)]

    def has_path_scene_effects(self, receiver_xy: tuple[float, float], source_xy: tuple[float, float]) -> bool:
        path_bbox = _segment_bbox(source_xy, receiver_xy)
        for segment_bbox in (bbox for _, bbox in self.shielding_segment_bboxes):
            if _bbox_intersects(path_bbox, segment_bbox):
                return True
        for item in self.ground_surfaces:
            if _bbox_intersects(path_bbox, item.bbox):
                return True
        for item in self.vegetation_zones:
            if _bbox_intersects(path_bbox, item.bbox):
                return True
        return False

    def ground_correction_db(self, receiver_xy: tuple[float, float], source_xy: tuple[float, float]) -> float:
        path_bbox = _segment_bbox(source_xy, receiver_xy)
        total = sum(item.ground_correction_db(receiver_xy, source_xy) for item in self.ground_surfaces if _bbox_intersects(path_bbox, item.bbox))
        return _clamp(total, -3.0, 1.2)

    def vegetation_correction_db(self, receiver_xy: tuple[float, float], source_xy: tuple[float, float]) -> float:
        path_bbox = _segment_bbox(source_xy, receiver_xy)
        total = sum(item.vegetation_correction_db(receiver_xy, source_xy) for item in self.vegetation_zones if _bbox_intersects(path_bbox, item.bbox))
        return _clamp(total, -5.5, 0.0)


def build_scene_model(scene_config: SceneConfig) -> SceneModel:
    objects: list[SceneObject] = []
    for barrier in scene_config.noise_barriers:
        objects.append(_noise_barrier_to_object(barrier))
    for terrain_edge in scene_config.terrain_edges:
        objects.append(_terrain_edge_to_object(terrain_edge))
    for building in scene_config.buildings:
        objects.append(_building_to_object(building))
    for ground_surface in scene_config.ground_surfaces:
        objects.append(_ground_surface_to_object(ground_surface))
    for vegetation_zone in scene_config.vegetation_zones:
        objects.append(_vegetation_zone_to_object(vegetation_zone))
    return SceneModel(objects=objects)


def _noise_barrier_to_object(barrier: NoiseBarrier) -> NoiseBarrierObject:
    return NoiseBarrierObject(
        id=barrier.id,
        object_type='noise_barrier',
        material=_build_material(
            object_type='noise_barrier',
            material_name=barrier.material,
            shielding_attenuation_db=barrier.attenuation_db,
            propagation=barrier.propagation,
        ),
        height_meters=barrier.height_meters,
        start_xy=(barrier.x1, barrier.y1),
        end_xy=(barrier.x2, barrier.y2),
    )


def _terrain_edge_to_object(terrain_edge: TerrainEdge) -> TerrainEdgeObject:
    return TerrainEdgeObject(
        id=terrain_edge.id,
        object_type='terrain_edge',
        material=_build_material(
            object_type='terrain_edge',
            material_name=terrain_edge.material,
            shielding_attenuation_db=terrain_edge.attenuation_db,
            propagation=terrain_edge.propagation,
        ),
        height_meters=terrain_edge.height_meters,
        start_xy=(terrain_edge.x1, terrain_edge.y1),
        end_xy=(terrain_edge.x2, terrain_edge.y2),
    )


def _building_to_object(building: Building) -> BuildingObject:
    return BuildingObject(
        id=building.id,
        object_type='building',
        material=_build_material(
            object_type='building',
            material_name=building.material,
            shielding_attenuation_db=building.attenuation_db,
            propagation=building.propagation,
        ),
        height_meters=building.height_meters,
        footprint=list(building.footprint),
    )


def _ground_surface_to_object(ground_surface: GroundSurface) -> GroundSurfaceObject:
    return GroundSurfaceObject(
        id=ground_surface.id,
        object_type='ground_surface',
        material=_build_material(
            object_type='ground_surface',
            material_name=ground_surface.material,
            shielding_attenuation_db=0.0,
            propagation=ground_surface.propagation,
        ),
        height_meters=0.0,
        footprint=list(ground_surface.footprint),
    )


def _vegetation_zone_to_object(vegetation_zone: VegetationZone) -> VegetationZoneObject:
    return VegetationZoneObject(
        id=vegetation_zone.id,
        object_type='vegetation_zone',
        material=_build_material(
            object_type='vegetation_zone',
            material_name=vegetation_zone.material,
            shielding_attenuation_db=vegetation_zone.attenuation_db,
            propagation=vegetation_zone.propagation,
        ),
        height_meters=vegetation_zone.height_meters,
        footprint=list(vegetation_zone.footprint),
        attenuation_db=vegetation_zone.attenuation_db,
    )


def _build_material(
    object_type: str,
    material_name: str,
    shielding_attenuation_db: float,
    propagation: PropagationProperties,
) -> PropagationMaterial:
    resolved = resolve_propagation_properties(
        object_type=object_type,
        material_name=material_name,
        overrides=propagation,
    )
    return PropagationMaterial(
        name=material_name,
        shielding_attenuation_db=shielding_attenuation_db,
        reflection_loss_db=resolved.reflection_loss_db if resolved.reflection_loss_db is not None else 0.0,
        diffraction_loss_db=resolved.diffraction_loss_db if resolved.diffraction_loss_db is not None else 0.0,
        absorption_coefficient=resolved.absorption_coefficient if resolved.absorption_coefficient is not None else 0.0,
        allows_reflection=bool(resolved.allows_reflection),
        allows_diffraction=bool(resolved.allows_diffraction),
    )


def _path_bbox_intersects_polygon(source_xy: tuple[float, float], receiver_xy: tuple[float, float], footprint: list[tuple[float, float]]) -> bool:
    if len(footprint) < 3:
        return False
    min_px = min(point[0] for point in footprint)
    max_px = max(point[0] for point in footprint)
    min_py = min(point[1] for point in footprint)
    max_py = max(point[1] for point in footprint)
    min_x = min(source_xy[0], receiver_xy[0])
    max_x = max(source_xy[0], receiver_xy[0])
    min_y = min(source_xy[1], receiver_xy[1])
    max_y = max(source_xy[1], receiver_xy[1])
    return not (max_x < min_px or max_px < min_x or max_y < min_py or max_py < min_y)


def _polygon_coverage_fraction(source_xy: tuple[float, float], receiver_xy: tuple[float, float], footprint: list[tuple[float, float]], samples: int = 7) -> float:
    if len(footprint) < 3:
        return 0.0
    inside = 0
    total = max(samples, 2)
    for index in range(total):
        t = index / (total - 1)
        point = (
            source_xy[0] + ((receiver_xy[0] - source_xy[0]) * t),
            source_xy[1] + ((receiver_xy[1] - source_xy[1]) * t),
        )
        if _point_in_polygon(point, footprint):
            inside += 1
    return inside / total


def _point_in_polygon(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    x, y = point
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            slope_x = x1 + ((y - y1) * (x2 - x1) / ((y2 - y1) or 1e-9))
            if x < slope_x:
                inside = not inside
    return inside


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))



def _segment_bbox(point_a: tuple[float, float], point_b: tuple[float, float]) -> tuple[float, float, float, float]:
    return (
        min(point_a[0], point_b[0]),
        min(point_a[1], point_b[1]),
        max(point_a[0], point_b[0]),
        max(point_a[1], point_b[1]),
    )


def _polygon_bbox(footprint: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    return (
        min(point[0] for point in footprint),
        min(point[1] for point in footprint),
        max(point[0] for point in footprint),
        max(point[1] for point in footprint),
    )


def _bbox_intersects(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])
