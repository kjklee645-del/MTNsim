from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from mtnsim.scene import build_scene_model, read_network_bounds
from mtnsim.security.paths import resolve_project_path
from mtnsim.security.xml import parse_xml_root
from mtnsim.schemas.project import ProjectManifest
from mtnsim.schemas.scenario import ScenarioConfig


@dataclass(slots=True)
class PolylineLayer:
    name: str
    polylines: list[list[tuple[float, float]]] = field(default_factory=list)
    widths: list[float] = field(default_factory=list)
    ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PolygonLayer:
    name: str
    polygons: list[list[tuple[float, float]]] = field(default_factory=list)
    ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PointLayer:
    name: str
    points: list[tuple[str, float, float]] = field(default_factory=list)


@dataclass(slots=True)
class SceneSnapshot:
    bounds: tuple[float, float, float, float]
    road_layer: PolylineLayer
    junction_layer: PolygonLayer
    barrier_layer: PolylineLayer
    terrain_layer: PolylineLayer
    building_layer: PolygonLayer
    ground_layer: PolygonLayer
    vegetation_layer: PolygonLayer
    receiver_layer: PointLayer
    grid_region: tuple[float, float, float, float] | None = None


class SceneController:
    def build_snapshot(self, project: ProjectManifest, scenario: ScenarioConfig) -> SceneSnapshot:
        network_path = self._resolve_path(project, project.paths.network)
        if network_path is not None and network_path.exists():
            network_bounds = read_network_bounds(network_path)
            road_polylines, road_widths, junction_polygons = self._load_network_geometry(network_path)
        else:
            network_bounds = self._receiver_bounds(scenario)
            road_polylines, road_widths, junction_polygons = [], [], []
        scene_model = build_scene_model(scenario.scene)

        road_layer = PolylineLayer(
            name='Road Network',
            polylines=road_polylines,
            widths=road_widths,
            ids=[f'lane_{index + 1}' for index in range(len(road_polylines))],
        )
        junction_layer = PolygonLayer(
            name='Junctions',
            polygons=junction_polygons,
            ids=[f'junction_{index + 1}' for index in range(len(junction_polygons))],
        )
        barrier_layer = PolylineLayer(
            name='Noise Barriers',
            polylines=[[item.start_xy, item.end_xy] for item in scene_model.noise_barriers],
            widths=[item.height_meters for item in scene_model.noise_barriers],
            ids=[item.id for item in scene_model.noise_barriers],
        )
        terrain_layer = PolylineLayer(
            name='Terrain Edges',
            polylines=[[item.start_xy, item.end_xy] for item in scene_model.terrain_edges],
            widths=[item.height_meters for item in scene_model.terrain_edges],
            ids=[item.id for item in scene_model.terrain_edges],
        )
        building_layer = PolygonLayer(
            name='Buildings',
            polygons=[list(item.footprint) for item in scene_model.buildings],
            ids=[item.id for item in scene_model.buildings],
        )
        ground_layer = PolygonLayer(
            name='Ground Surfaces',
            polygons=[list(item.footprint) for item in scene_model.ground_surfaces],
            ids=[item.id for item in scene_model.ground_surfaces],
        )
        vegetation_layer = PolygonLayer(
            name='Vegetation Zones',
            polygons=[list(item.footprint) for item in scene_model.vegetation_zones],
            ids=[item.id for item in scene_model.vegetation_zones],
        )
        receiver_layer = PointLayer(
            name='Receivers',
            points=[(receiver.id, receiver.x, receiver.y) for receiver in scenario.receivers],
        )
        bounds = self._compose_display_bounds(
            network_bounds,
            road_layer,
            junction_layer,
            barrier_layer,
            terrain_layer,
            building_layer,
            ground_layer,
            vegetation_layer,
            receiver_layer,
        )
        grid_region = None
        if scenario.grid.override_enabled and None not in (
            scenario.grid.override_min_x,
            scenario.grid.override_min_y,
            scenario.grid.override_max_x,
            scenario.grid.override_max_y,
        ):
            grid_region = (
                float(scenario.grid.override_min_x),
                float(scenario.grid.override_min_y),
                float(scenario.grid.override_max_x),
                float(scenario.grid.override_max_y),
            )
        return SceneSnapshot(
            bounds=bounds,
            road_layer=road_layer,
            junction_layer=junction_layer,
            barrier_layer=barrier_layer,
            terrain_layer=terrain_layer,
            building_layer=building_layer,
            ground_layer=ground_layer,
            vegetation_layer=vegetation_layer,
            receiver_layer=receiver_layer,
            grid_region=grid_region,
        )

    def _resolve_path(self, project: ProjectManifest, raw_path: str) -> Path | None:
        if not raw_path:
            return None
        return resolve_project_path(project, raw_path, label="project scene path", must_exist=False)

    def _load_network_geometry(self, network_path: Path) -> tuple[list[list[tuple[float, float]]], list[float], list[list[tuple[float, float]]]]:
        root = parse_xml_root(network_path, label="SUMO network geometry file")
        polylines: list[list[tuple[float, float]]] = []
        widths: list[float] = []
        junction_polygons: list[list[tuple[float, float]]] = []
        for edge in root.findall('edge'):
            if edge.get('function') == 'internal':
                continue
            for lane in edge.findall('lane'):
                shape = lane.get('shape')
                if not shape:
                    continue
                points = self._parse_shape(shape)
                if len(points) >= 2:
                    polylines.append(points)
                    widths.append(float(lane.get('width', '3.2')))
        for junction in root.findall('junction'):
            shape = junction.get('shape')
            if not shape:
                continue
            polygon = self._parse_shape(shape)
            if len(polygon) >= 3:
                junction_polygons.append(polygon)
        return polylines, widths, junction_polygons

    def _parse_shape(self, shape: str) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        for pair in shape.split():
            x_str, y_str = pair.split(',')
            points.append((float(x_str), float(y_str)))
        return points

    def _receiver_bounds(self, scenario: ScenarioConfig) -> tuple[float, float, float, float]:
        if not scenario.receivers:
            return (0.0, 0.0, 100.0, 100.0)
        xs = [receiver.x for receiver in scenario.receivers]
        ys = [receiver.y for receiver in scenario.receivers]
        min_x = min(xs)
        max_x = max(xs)
        min_y = min(ys)
        max_y = max(ys)
        span_x = max(max_x - min_x, 10.0)
        span_y = max(max_y - min_y, 10.0)
        return (min_x - span_x * 0.25, min_y - span_y * 0.25, max_x + span_x * 0.25, max_y + span_y * 0.25)

    def _compose_display_bounds(
        self,
        network_bounds: tuple[float, float, float, float],
        road_layer: PolylineLayer,
        junction_layer: PolygonLayer,
        barrier_layer: PolylineLayer,
        terrain_layer: PolylineLayer,
        building_layer: PolygonLayer,
        ground_layer: PolygonLayer,
        vegetation_layer: PolygonLayer,
        receiver_layer: PointLayer,
    ) -> tuple[float, float, float, float]:
        xs: list[float] = []
        ys: list[float] = []

        def add_point(x: float, y: float) -> None:
            xs.append(float(x))
            ys.append(float(y))

        for min_x, min_y, max_x, max_y in [network_bounds]:
            add_point(min_x, min_y)
            add_point(max_x, max_y)

        for layer in [road_layer, barrier_layer, terrain_layer]:
            for polyline in layer.polylines:
                for x, y in polyline:
                    add_point(x, y)

        for layer in [junction_layer, building_layer, ground_layer, vegetation_layer]:
            for polygon in layer.polygons:
                for x, y in polygon:
                    add_point(x, y)

        for _, x, y in receiver_layer.points:
            add_point(x, y)

        if not xs or not ys:
            return network_bounds

        min_x = min(xs)
        min_y = min(ys)
        max_x = max(xs)
        max_y = max(ys)
        span_x = max(max_x - min_x, 1.0)
        span_y = max(max_y - min_y, 1.0)
        padding_x = max(span_x * 0.05, 10.0)
        padding_y = max(span_y * 0.10, 12.0)
        return (min_x - padding_x, min_y - padding_y, max_x + padding_x, max_y + padding_y)
