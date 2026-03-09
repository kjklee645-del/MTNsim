from __future__ import annotations

from dataclasses import dataclass, field

from mtnsim.acoustics.propagation.shielding import BarrierSegment
from mtnsim.scene.materials import resolve_propagation_properties
from mtnsim.schemas.scenario import Building, NoiseBarrier, PropagationProperties, SceneConfig


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


@dataclass(slots=True)
class LinearSceneObject(SceneObject):
    start_xy: tuple[float, float]
    end_xy: tuple[float, float]

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
            )
        ]


@dataclass(slots=True)
class PolygonSceneObject(SceneObject):
    footprint: list[tuple[float, float]] = field(default_factory=list)

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
                )
            )
        return segments


@dataclass(slots=True)
class NoiseBarrierObject(LinearSceneObject):
    pass


@dataclass(slots=True)
class BuildingObject(PolygonSceneObject):
    pass


@dataclass(slots=True)
class SceneModel:
    objects: list[SceneObject] = field(default_factory=list)

    @property
    def noise_barriers(self) -> list[NoiseBarrierObject]:
        return [item for item in self.objects if isinstance(item, NoiseBarrierObject)]

    @property
    def buildings(self) -> list[BuildingObject]:
        return [item for item in self.objects if isinstance(item, BuildingObject)]

    def to_shielding_segments(self) -> list[BarrierSegment]:
        segments: list[BarrierSegment] = []
        for item in self.objects:
            segments.extend(item.to_shielding_segments())
        return segments



def build_scene_model(scene_config: SceneConfig) -> SceneModel:
    objects: list[SceneObject] = []
    for barrier in scene_config.noise_barriers:
        objects.append(_noise_barrier_to_object(barrier))
    for building in scene_config.buildings:
        objects.append(_building_to_object(building))
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