from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import xml.etree.ElementTree as ET

from mtnsim.scene import build_scene_model, read_network_bounds
from mtnsim.schemas.project import ProjectManifest
from mtnsim.schemas.scenario import ScenarioConfig


@dataclass(slots=True)
class PolylineLayer:
    name: str
    polylines: list[list[tuple[float, float]]] = field(default_factory=list)


@dataclass(slots=True)
class PolygonLayer:
    name: str
    polygons: list[list[tuple[float, float]]] = field(default_factory=list)


@dataclass(slots=True)
class PointLayer:
    name: str
    points: list[tuple[str, float, float]] = field(default_factory=list)


@dataclass(slots=True)
class SceneSnapshot:
    bounds: tuple[float, float, float, float]
    road_layer: PolylineLayer
    barrier_layer: PolylineLayer
    terrain_layer: PolylineLayer
    building_layer: PolygonLayer
    ground_layer: PolygonLayer
    vegetation_layer: PolygonLayer
    receiver_layer: PointLayer


class SceneController:
    def build_snapshot(self, project: ProjectManifest, scenario: ScenarioConfig) -> SceneSnapshot:
        network_path = self._resolve_path(project, project.paths.network)
        bounds = read_network_bounds(network_path)
        road_polylines = self._load_network_polylines(network_path)
        scene_model = build_scene_model(scenario.scene)

        barrier_layer = PolylineLayer(
            name='Noise Barriers',
            polylines=[[item.start_xy, item.end_xy] for item in scene_model.noise_barriers],
        )
        terrain_layer = PolylineLayer(
            name='Terrain Edges',
            polylines=[[item.start_xy, item.end_xy] for item in scene_model.terrain_edges],
        )
        building_layer = PolygonLayer(
            name='Buildings',
            polygons=[list(item.footprint) for item in scene_model.buildings],
        )
        ground_layer = PolygonLayer(
            name='Ground Surfaces',
            polygons=[list(item.footprint) for item in scene_model.ground_surfaces],
        )
        vegetation_layer = PolygonLayer(
            name='Vegetation Zones',
            polygons=[list(item.footprint) for item in scene_model.vegetation_zones],
        )
        receiver_layer = PointLayer(
            name='Receivers',
            points=[(receiver.id, receiver.x, receiver.y) for receiver in scenario.receivers],
        )
        return SceneSnapshot(
            bounds=bounds,
            road_layer=PolylineLayer(name='Road Network', polylines=road_polylines),
            barrier_layer=barrier_layer,
            terrain_layer=terrain_layer,
            building_layer=building_layer,
            ground_layer=ground_layer,
            vegetation_layer=vegetation_layer,
            receiver_layer=receiver_layer,
        )

    def _resolve_path(self, project: ProjectManifest, raw_path: str) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path
        if project.source_path is None:
            return Path.cwd() / path
        source_parent = project.source_path.parent
        project_root = source_parent.parent if source_parent.name == 'examples' else source_parent
        return project_root / path

    def _load_network_polylines(self, network_path: Path) -> list[list[tuple[float, float]]]:
        root = ET.parse(network_path).getroot()
        polylines: list[list[tuple[float, float]]] = []
        for edge in root.findall('edge'):
            if edge.get('function') == 'internal':
                continue
            for lane in edge.findall('lane'):
                shape = lane.get('shape')
                if not shape:
                    continue
                points: list[tuple[float, float]] = []
                for pair in shape.split():
                    x_str, y_str = pair.split(',')
                    points.append((float(x_str), float(y_str)))
                if len(points) >= 2:
                    polylines.append(points)
        return polylines
