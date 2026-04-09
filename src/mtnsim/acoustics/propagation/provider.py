from __future__ import annotations

from dataclasses import dataclass

from mtnsim.acoustics.emission.road_vehicle import calculate_3d_distance
from mtnsim.acoustics.propagation.correction import PropagationContext, total_propagation_correction_db
from mtnsim.acoustics.propagation.diffraction import DiffractionModelSettings, build_diffraction_context
from mtnsim.acoustics.propagation.materials import MaterialContext
from mtnsim.acoustics.propagation.reflection import ReflectionModelSettings, build_reflection_context
from mtnsim.acoustics.propagation.shielding import build_shielding_context

try:
    import torch
except ImportError:  # pragma: no cover
    torch = None


@dataclass(frozen=True, slots=True)
class PropagationSample:
    distance_meters: float
    correction_db: float


@dataclass(frozen=True, slots=True)
class TensorCandidateScan:
    poi_ids: list[str]
    distances_meters: list[float]
    scene_effect_mask: list[bool]


class SceneAwarePropagationProvider:
    def __init__(self, scene_model, reflection_settings: ReflectionModelSettings, diffraction_settings: DiffractionModelSettings) -> None:
        self.scene_model = scene_model
        self.reflection_settings = reflection_settings
        self.diffraction_settings = diffraction_settings
        self._poi_cache_key: tuple[str, ...] | None = None
        self._poi_ids_cache: list[str] | None = None
        self._poi_tensor_cache = None
        self._tensor_device = None
        self._segment_bbox_tensor = None
        self._ground_bbox_tensor = None
        self._vegetation_bbox_tensor = None
        if torch is not None:
            self._tensor_device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self._segment_bbox_tensor = self._build_bbox_tensor([bbox for _, bbox in self.scene_model.shielding_segment_bboxes])
            self._ground_bbox_tensor = self._build_bbox_tensor([item.bbox for item in self.scene_model.ground_surfaces])
            self._vegetation_bbox_tensor = self._build_bbox_tensor([item.bbox for item in self.scene_model.vegetation_zones])

    def corrections_for_vehicle(
        self,
        poi_positions: dict[str, tuple[float, float, float]],
        vehicle_id: str,
        vehicle_position: tuple[float, float],
        max_area_meters: float,
    ) -> dict[str, PropagationSample]:
        samples: dict[str, PropagationSample] = {}
        scan = self._scan_pois(poi_positions, vehicle_position, max_area_meters)
        for poi_id, distance, has_scene_effect in zip(scan.poi_ids, scan.distances_meters, scan.scene_effect_mask):
            poi_position = poi_positions[poi_id]
            correction_db = self._correction_for_pair(poi_position, vehicle_position) if has_scene_effect else 0.0
            samples[poi_id] = PropagationSample(distance_meters=distance, correction_db=correction_db)
        return samples

    def correction_for_pair(
        self,
        poi_id: str,
        poi_position: tuple[float, float, float],
        vehicle_id: str,
        vehicle_position: tuple[float, float],
    ) -> PropagationContext | None:
        return self._build_context(poi_position, vehicle_position)

    def _scan_pois(
        self,
        poi_positions: dict[str, tuple[float, float, float]],
        vehicle_position: tuple[float, float],
        max_area_meters: float,
    ) -> TensorCandidateScan:
        if torch is None or self._tensor_device is None:
            return self._scan_pois_python(poi_positions, vehicle_position, max_area_meters)
        if self._tensor_device.type != 'cuda' and len(poi_positions) < 256:
            return self._scan_pois_python(poi_positions, vehicle_position, max_area_meters)

        poi_ids, poi_tensor = self._resolve_poi_tensor(poi_positions)
        vehicle_tensor = torch.tensor([vehicle_position[0], vehicle_position[1], 0.3], dtype=torch.float32, device=self._tensor_device)
        deltas = poi_tensor - vehicle_tensor
        distances = torch.linalg.norm(deltas, dim=1)
        within_mask = distances <= float(max_area_meters)
        if not bool(within_mask.any()):
            return TensorCandidateScan(poi_ids=[], distances_meters=[], scene_effect_mask=[])

        candidate_indices = torch.nonzero(within_mask, as_tuple=False).flatten()
        candidate_positions = poi_tensor[candidate_indices, :2]
        source_x = torch.full((candidate_positions.shape[0],), float(vehicle_position[0]), dtype=torch.float32, device=self._tensor_device)
        source_y = torch.full((candidate_positions.shape[0],), float(vehicle_position[1]), dtype=torch.float32, device=self._tensor_device)
        path_bbox = torch.stack(
            [
                torch.minimum(source_x, candidate_positions[:, 0]),
                torch.minimum(source_y, candidate_positions[:, 1]),
                torch.maximum(source_x, candidate_positions[:, 0]),
                torch.maximum(source_y, candidate_positions[:, 1]),
            ],
            dim=1,
        )
        scene_mask = self._scene_effect_mask(path_bbox)
        candidate_ids = [poi_ids[index] for index in candidate_indices.tolist()]
        candidate_distances = distances[candidate_indices].tolist()
        candidate_scene_mask = scene_mask.tolist() if isinstance(scene_mask, torch.Tensor) else list(scene_mask)
        return TensorCandidateScan(
            poi_ids=candidate_ids,
            distances_meters=[float(value) for value in candidate_distances],
            scene_effect_mask=[bool(value) for value in candidate_scene_mask],
        )

    def _scene_effect_mask(self, path_bbox):
        masks = []
        for bbox_tensor in (self._segment_bbox_tensor, self._ground_bbox_tensor, self._vegetation_bbox_tensor):
            if bbox_tensor is None or bbox_tensor.shape[0] == 0:
                continue
            intersects = self._bbox_intersections(path_bbox, bbox_tensor)
            masks.append(torch.any(intersects, dim=1))
        if not masks:
            return torch.zeros((path_bbox.shape[0],), dtype=torch.bool, device=self._tensor_device)
        combined = masks[0]
        for mask in masks[1:]:
            combined = torch.logical_or(combined, mask)
        return combined

    def _bbox_intersections(self, path_bbox, scene_bbox_tensor):
        return ~(
            (path_bbox[:, 2:3] < scene_bbox_tensor[:, 0])
            | (scene_bbox_tensor[:, 2] < path_bbox[:, 0:1])
            | (path_bbox[:, 3:4] < scene_bbox_tensor[:, 1])
            | (scene_bbox_tensor[:, 3] < path_bbox[:, 1:2])
        )

    def _resolve_poi_tensor(self, poi_positions: dict[str, tuple[float, float, float]]):
        cache_key = tuple(poi_positions.keys())
        if self._poi_cache_key != cache_key:
            self._poi_cache_key = cache_key
            self._poi_ids_cache = list(poi_positions.keys())
            self._poi_tensor_cache = torch.tensor(list(poi_positions.values()), dtype=torch.float32, device=self._tensor_device)
        return self._poi_ids_cache, self._poi_tensor_cache

    def _build_bbox_tensor(self, boxes: list[tuple[float, float, float, float]]):
        if not boxes:
            return None
        return torch.tensor(boxes, dtype=torch.float32, device=self._tensor_device)

    def _scan_pois_python(
        self,
        poi_positions: dict[str, tuple[float, float, float]],
        vehicle_position: tuple[float, float],
        max_area_meters: float,
    ) -> TensorCandidateScan:
        poi_ids: list[str] = []
        distances: list[float] = []
        scene_mask: list[bool] = []
        for poi_id, poi_position in poi_positions.items():
            distance = calculate_3d_distance(poi_position, vehicle_position)
            if distance > max_area_meters:
                continue
            receiver_xy = (poi_position[0], poi_position[1])
            poi_ids.append(poi_id)
            distances.append(distance)
            scene_mask.append(self.scene_model.has_path_scene_effects(receiver_xy, vehicle_position))
        return TensorCandidateScan(poi_ids=poi_ids, distances_meters=distances, scene_effect_mask=scene_mask)

    def _correction_for_pair(self, poi_position: tuple[float, float, float], vehicle_position: tuple[float, float]) -> float:
        context = self._build_context(poi_position, vehicle_position)
        return total_propagation_correction_db(context)

    def _build_context(self, poi_position: tuple[float, float, float], vehicle_position: tuple[float, float]) -> PropagationContext | None:
        receiver_xy = (poi_position[0], poi_position[1])
        if not self.scene_model.has_path_scene_effects(receiver_xy, vehicle_position):
            return None

        candidate_segments = self.scene_model.candidate_shielding_segments(receiver_xy, vehicle_position)
        shielding = build_shielding_context(
            receiver_pos=poi_position,
            source_pos=vehicle_position,
            barriers=candidate_segments,
        )
        reflection = build_reflection_context(
            receiver_pos=poi_position,
            source_pos=vehicle_position,
            barriers=candidate_segments,
            settings=self.reflection_settings,
        )
        diffraction = build_diffraction_context(shielding, settings=self.diffraction_settings)

        material = None
        if shielding is not None:
            material = MaterialContext(
                reflection_loss_db=shielding.reflection_loss_db,
                diffraction_loss_db=shielding.diffraction_loss_db,
                absorption_coefficient=shielding.absorption_coefficient,
                allows_reflection=shielding.allows_reflection,
                allows_diffraction=shielding.allows_diffraction,
            )

        ground_correction_db = self.scene_model.ground_correction_db(poi_position, vehicle_position)
        vegetation_correction_db = self.scene_model.vegetation_correction_db(poi_position, vehicle_position)
        if shielding is None and reflection is None and diffraction is None and material is None and ground_correction_db == 0.0 and vegetation_correction_db == 0.0:
            return None

        return PropagationContext(
            shielding=shielding,
            reflection=reflection,
            diffraction=diffraction,
            material=material,
            ground_correction_db=ground_correction_db,
            vegetation_correction_db=vegetation_correction_db,
        )
