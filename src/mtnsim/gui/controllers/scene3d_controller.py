from __future__ import annotations

from mtnsim.gui.controllers.playback_controller import PlaybackDataset, PlaybackFrame
from mtnsim.gui.controllers.result_controller import HeatmapCell
from mtnsim.gui.controllers.scene_controller import SceneSnapshot
from mtnsim.gui.models.scene_3d import GridRegion3D, LineWall3D, Marker3D, NoiseCell3D, PrismMesh3D, RoadMesh3D, Scene3DFrame, SurfacePolygon3D, TrailLine3D, VehicleMarker3D


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


    def apply_playback_frame(
        self,
        frame: Scene3DFrame | None,
        playback_frame: PlaybackFrame | None,
        *,
        dataset: PlaybackDataset | None = None,
        frame_index: int | None = None,
        selected_vehicle_id: str | None = None,
    ) -> Scene3DFrame | None:
        if frame is None:
            return None
        if playback_frame is None:
            frame.vehicles = []
            frame.vehicle_trails = []
            return frame
        frame.vehicles = [
            VehicleMarker3D(
                vehicle_id=vehicle.vehicle_id,
                x=vehicle.x,
                y=vehicle.y,
                z=0.35,
                speed_mps=vehicle.speed_mps,
                vehicle_type=vehicle.vehicle_type,
                color=self._speed_color(vehicle.speed_mps),
                selected=(vehicle.vehicle_id == selected_vehicle_id),
            )
            for vehicle in playback_frame.vehicles
        ]
        frame.vehicle_trails = []
        if dataset is not None and frame_index is not None and frame_index >= 0:
            tail_start = max(0, frame_index - 12)
            tail_frames = dataset.frames[tail_start:frame_index + 1]
            for vehicle in playback_frame.vehicles:
                trail = []
                for tail_frame in tail_frames:
                    for candidate in tail_frame.vehicles:
                        if candidate.vehicle_id == vehicle.vehicle_id:
                            trail.append((candidate.x, candidate.y))
                            break
                if len(trail) >= 2:
                    frame.vehicle_trails.append(
                        TrailLine3D(
                            points=trail,
                            z=0.10,
                            color=self._speed_color(vehicle.speed_mps),
                            selected=(vehicle.vehicle_id == selected_vehicle_id),
                        )
                    )
        return frame

    def _speed_color(self, speed_mps: float) -> str:
        ratio = max(0.0, min(1.0, speed_mps / 35.0))
        if ratio < 0.5:
            local = ratio / 0.5
            r = int(60 + 80 * local)
            g = int(190 + 20 * local)
            b = int(240 - 140 * local)
        else:
            local = (ratio - 0.5) / 0.5
            r = int(140 + 110 * local)
            g = int(210 - 120 * local)
            b = int(100 - 70 * local)
        return f'#{r:02x}{g:02x}{b:02x}'
