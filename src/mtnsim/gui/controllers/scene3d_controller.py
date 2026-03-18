from __future__ import annotations

from mtnsim.gui.controllers.result_controller import HeatmapCell
from mtnsim.gui.controllers.scene_controller import SceneSnapshot
from mtnsim.gui.models.scene_3d import GridRegion3D, LineWall3D, Marker3D, NoiseCell3D, PrismMesh3D, RoadMesh3D, Scene3DFrame, SurfacePolygon3D


class Scene3DController:
    def build_frame(self, snapshot: SceneSnapshot | None) -> Scene3DFrame | None:
        if snapshot is None:
            return None
        frame = Scene3DFrame(bounds=snapshot.bounds)
        frame.roads = [
            RoadMesh3D(points=list(polyline), width=max(width, 2.0), z=0.0, color='#d7dde8')
            for polyline, width in zip(snapshot.road_layer.polylines, snapshot.road_layer.widths)
        ]
        frame.barriers = [
            LineWall3D(
                start=polyline[0],
                end=polyline[-1],
                height=max(width, 2.0),
                thickness=1.4,
                color='#ff9548',
                edge_color='#381a08',
                label=snapshot.barrier_layer.ids[index] if index < len(snapshot.barrier_layer.ids) else '',
            )
            for index, (polyline, width) in enumerate(zip(snapshot.barrier_layer.polylines, snapshot.barrier_layer.widths))
            if len(polyline) >= 2
        ]
        frame.terrain_edges = [
            LineWall3D(
                start=polyline[0],
                end=polyline[-1],
                height=max(width, 1.5),
                thickness=1.2,
                color='#6b7c4f',
                edge_color='#1d2512',
                label=snapshot.terrain_layer.ids[index] if index < len(snapshot.terrain_layer.ids) else '',
            )
            for index, (polyline, width) in enumerate(zip(snapshot.terrain_layer.polylines, snapshot.terrain_layer.widths))
            if len(polyline) >= 2
        ]
        frame.buildings = [
            PrismMesh3D(
                footprint=list(polygon),
                height=14.0,
                color='#2d3441',
                edge_color='#11161d',
                label=snapshot.building_layer.ids[index] if index < len(snapshot.building_layer.ids) else '',
            )
            for index, polygon in enumerate(snapshot.building_layer.polygons)
            if len(polygon) >= 3
        ]
        frame.ground_surfaces = [
            SurfacePolygon3D(
                polygon=list(polygon),
                z=0.02,
                color='#3f4a2e',
                edge_color='#233018',
                label=snapshot.ground_layer.ids[index] if index < len(snapshot.ground_layer.ids) else '',
            )
            for index, polygon in enumerate(snapshot.ground_layer.polygons)
            if len(polygon) >= 3
        ]
        frame.vegetation_zones = [
            SurfacePolygon3D(
                polygon=list(polygon),
                z=0.05,
                color='#24533a',
                edge_color='#133222',
                label=snapshot.vegetation_layer.ids[index] if index < len(snapshot.vegetation_layer.ids) else '',
            )
            for index, polygon in enumerate(snapshot.vegetation_layer.polygons)
            if len(polygon) >= 3
        ]
        frame.receivers = [
            Marker3D(x=x, y=y, z=1.5, color='#f8fbff', label=receiver_id)
            for receiver_id, x, y in snapshot.receiver_layer.points
        ]
        if snapshot.grid_region is not None:
            frame.grid_region = GridRegion3D(bounds=snapshot.grid_region, z=0.12, color='#47b8ff')
        return frame


    def apply_noise_cells(self, frame: Scene3DFrame | None, cells: list[HeatmapCell], cell_size: float = 10.0) -> Scene3DFrame | None:
        if frame is None:
            return None
        frame.noise_cells = [
            NoiseCell3D(x=cell.x, y=cell.y, value_db=cell.value_db, cell_size=cell_size)
            for cell in cells
        ]
        return frame
