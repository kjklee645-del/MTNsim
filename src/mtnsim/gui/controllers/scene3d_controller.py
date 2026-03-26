from __future__ import annotations

import math
from math import cos, pi, radians, sin

from mtnsim.acoustics.emission.road_vehicle import directional_gain_db
from mtnsim.gui.controllers.playback_controller import PlaybackDataset, PlaybackFrame
from mtnsim.gui.controllers.result_controller import HeatmapCell
from mtnsim.gui.controllers.scene_controller import SceneSnapshot
from mtnsim.gui.models.scene_3d import GridRegion3D, InteractionLine3D, LineWall3D, Marker3D, NoiseCell3D, PrismMesh3D, RoadMesh3D, Scene3DFrame, SourceFieldOverlay3D, SurfacePolygon3D, TrailLine3D, VehicleMarker3D


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


    def apply_source_field_overlay(
        self,
        frame: Scene3DFrame | None,
        playback_frame: PlaybackFrame | None,
        *,
        dataset: PlaybackDataset | None = None,
        frame_index: int | None = None,
        selected_vehicle_id: str | None = None,
        mode: str = 'off',
        scale: float = 1.0,
        height_scale: float = 1.0,
        opacity: float = 0.32,
        wedge_span_deg: float = 70.0,
        vertical_angle_deg: float = 55.0,
        vertical_strength_db: float = 0.0,
        highlight_receivers: bool = True,
        show_receiver_links: bool = True,
        directivity_preset: str = 'custom',
        emission_mode: str = 'isotropic',
        emission_strength_db: float = 0.0,
    ) -> Scene3DFrame | None:
        if frame is None:
            return None
        frame.source_field_overlays = []
        frame.source_field_links = []
        for receiver in frame.receivers:
            receiver.highlighted = False
            receiver.directivity_gain_db = 0.0
        if playback_frame is None or not selected_vehicle_id or mode == 'off':
            return frame
        visual = self._source_field_visual_profile(directivity_preset, mode)
        target = None
        for vehicle in playback_frame.vehicles:
            if vehicle.vehicle_id == selected_vehicle_id:
                target = vehicle
                break
        if target is None:
            return frame
        heading_deg = self._estimate_heading_deg(dataset, frame_index, selected_vehicle_id)
        radius = max(8.0, min(90.0, (14.0 + target.speed_mps * 1.4) * max(scale, 0.2) * float(visual['scale_mul'])))
        vertical_half_span = radians(max(5.0, min(170.0, vertical_angle_deg))) * 0.5
        vertical_factor = max(0.12, min(1.6, math.tan(vertical_half_span) * 0.55))
        overlay_height = max(1.0, radius * vertical_factor * max(height_scale, 0.2) * float(visual['height_mul']))
        resolved_opacity = max(0.05, min(0.95, opacity * float(visual['opacity_mul'])))
        if mode == 'sphere':
            footprint = [
                (target.x + cos(theta) * radius, target.y + sin(theta) * radius)
                for theta in [2.0 * pi * idx / 18.0 for idx in range(18)]
            ]
            height = max(1.0, radius * 0.22 * max(height_scale, 0.2))
            frame.source_field_overlays.append(
                SourceFieldOverlay3D(
                    mode='sphere',
                    footprint=footprint,
                    height=height,
                    color=str(visual['primary']),
                    edge_color=str(visual['edge']),
                    label=selected_vehicle_id,
                    opacity=resolved_opacity,
                )
            )
        elif mode == 'wedge':
            heading = radians(heading_deg)
            span = radians(max(20.0, min(160.0, wedge_span_deg)))
            points = [(target.x, target.y)]
            steps = 8
            for idx in range(steps + 1):
                angle = heading - span * 0.5 + span * (idx / steps)
                points.append((target.x + cos(angle) * radius * 1.15, target.y + sin(angle) * radius * 1.15))
            frame.source_field_overlays.append(
                SourceFieldOverlay3D(
                    mode='wedge',
                    footprint=points,
                    height=overlay_height,
                    color=str(visual['primary']),
                    edge_color=str(visual['edge']),
                    label=selected_vehicle_id,
                    opacity=resolved_opacity,
                )
            )
        elif mode == 'dual_wedge':
            heading = radians(heading_deg)
            span = radians(max(20.0, min(160.0, wedge_span_deg)))
            steps = 8
            for direction, color in ((0.0, str(visual['primary'])), (pi, str(visual['secondary']))):
                points = [(target.x, target.y)]
                base_heading = heading + direction
                for idx in range(steps + 1):
                    angle = base_heading - span * 0.5 + span * (idx / steps)
                    points.append((target.x + cos(angle) * radius, target.y + sin(angle) * radius))
                frame.source_field_overlays.append(
                    SourceFieldOverlay3D(
                        mode='dual_wedge',
                        footprint=points,
                        height=overlay_height,
                        color=color,
                        edge_color=str(visual['edge']),
                        label=selected_vehicle_id,
                        opacity=resolved_opacity,
                    )
                )
        self._apply_receiver_interactions(
            frame,
            target,
            dataset=dataset,
            frame_index=frame_index,
            directivity_preset=directivity_preset,
            emission_mode=emission_mode,
            emission_strength_db=emission_strength_db,
            wedge_span_deg=wedge_span_deg,
            vertical_angle_deg=vertical_angle_deg,
            vertical_strength_db=vertical_strength_db,
            highlight_receivers=highlight_receivers,
            show_receiver_links=show_receiver_links,
        )
        return frame


    def _source_field_visual_profile(self, preset: str, mode: str) -> dict[str, float | str]:
        preset_key = str(preset or 'custom').lower()
        profiles = {
            'custom': {
                'primary': '#7c67ff' if mode == 'sphere' else '#ff7a59',
                'secondary': '#a06bff',
                'edge': '#f2ebff' if mode == 'sphere' else '#fff0eb',
                'scale_mul': 1.0,
                'height_mul': 1.0,
                'opacity_mul': 1.0,
            },
            'passenger': {
                'primary': '#46d7ff',
                'secondary': '#3d9bff',
                'edge': '#e8fbff',
                'scale_mul': 0.95,
                'height_mul': 0.95,
                'opacity_mul': 0.95,
            },
            'sedan': {
                'primary': '#5ee7ff',
                'secondary': '#46b8ff',
                'edge': '#eafcff',
                'scale_mul': 0.9,
                'height_mul': 0.9,
                'opacity_mul': 0.92,
            },
            'suv': {
                'primary': '#37d0d6',
                'secondary': '#2d8fff',
                'edge': '#defcff',
                'scale_mul': 1.02,
                'height_mul': 1.04,
                'opacity_mul': 0.98,
            },
            'bus': {
                'primary': '#ffd166',
                'secondary': '#8c7cff',
                'edge': '#fff6d6',
                'scale_mul': 1.12,
                'height_mul': 1.15,
                'opacity_mul': 1.0,
            },
            'city_bus': {
                'primary': '#ffc94a',
                'secondary': '#7f73ff',
                'edge': '#fff1c5',
                'scale_mul': 1.18,
                'height_mul': 1.2,
                'opacity_mul': 1.02,
            },
            'coach_bus': {
                'primary': '#ffe08a',
                'secondary': '#9d83ff',
                'edge': '#fff8de',
                'scale_mul': 1.08,
                'height_mul': 1.1,
                'opacity_mul': 0.98,
            },
            'truck': {
                'primary': '#ff7a59',
                'secondary': '#c26bff',
                'edge': '#fff0eb',
                'scale_mul': 1.22,
                'height_mul': 1.3,
                'opacity_mul': 1.08,
            },
            'delivery_truck': {
                'primary': '#ff9a63',
                'secondary': '#be7dff',
                'edge': '#fff1e7',
                'scale_mul': 1.15,
                'height_mul': 1.18,
                'opacity_mul': 1.02,
            },
            'heavy_truck': {
                'primary': '#ff6b45',
                'secondary': '#b65dff',
                'edge': '#ffe9df',
                'scale_mul': 1.28,
                'height_mul': 1.36,
                'opacity_mul': 1.1,
            },
        }
        return profiles.get(preset_key, profiles['custom'])

    def _receiver_interaction_profile(self, preset: str) -> dict[str, float | str]:
        preset_key = str(preset or 'custom').lower()
        profiles = {
            'custom': {'highlight_color': '#fff4b2', 'link_color': '#fff2a6', 'margin_m': 2.0, 'gain_gate_db': -3.5},
            'passenger': {'highlight_color': '#b7f1ff', 'link_color': '#8be3ff', 'margin_m': 1.5, 'gain_gate_db': -1.5},
            'sedan': {'highlight_color': '#cbf8ff', 'link_color': '#91e9ff', 'margin_m': 1.0, 'gain_gate_db': -1.0},
            'suv': {'highlight_color': '#b2f0f4', 'link_color': '#6fdff0', 'margin_m': 2.2, 'gain_gate_db': -2.0},
            'bus': {'highlight_color': '#ffe29a', 'link_color': '#ffd166', 'margin_m': 4.0, 'gain_gate_db': -3.0},
            'city_bus': {'highlight_color': '#ffd989', 'link_color': '#ffc94a', 'margin_m': 4.8, 'gain_gate_db': -2.8},
            'coach_bus': {'highlight_color': '#ffebb7', 'link_color': '#ffdb80', 'margin_m': 3.4, 'gain_gate_db': -3.2},
            'truck': {'highlight_color': '#ffc4a8', 'link_color': '#ff9b6e', 'margin_m': 7.0, 'gain_gate_db': -4.5},
            'delivery_truck': {'highlight_color': '#ffd1bc', 'link_color': '#ffab83', 'margin_m': 5.2, 'gain_gate_db': -3.8},
            'heavy_truck': {'highlight_color': '#ffb59a', 'link_color': '#ff825b', 'margin_m': 8.0, 'gain_gate_db': -5.0},
        }
        return profiles.get(preset_key, profiles['custom'])

    def _estimate_heading_deg(self, dataset: PlaybackDataset | None, frame_index: int | None, vehicle_id: str) -> float:
        if dataset is None or frame_index is None or frame_index < 0 or frame_index >= dataset.frame_count:
            return 0.0
        current = dataset.frames[frame_index]
        previous = dataset.frames[frame_index - 1] if frame_index > 0 else None
        current_vehicle = next((vehicle for vehicle in current.vehicles if vehicle.vehicle_id == vehicle_id), None)
        previous_vehicle = None
        if previous is not None:
            previous_vehicle = next((vehicle for vehicle in previous.vehicles if vehicle.vehicle_id == vehicle_id), None)
        if current_vehicle is None or previous_vehicle is None:
            return 0.0
        dx = current_vehicle.x - previous_vehicle.x
        dy = current_vehicle.y - previous_vehicle.y
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            return 0.0
        from math import atan2, degrees
        return degrees(atan2(dy, dx))


    def _apply_receiver_interactions(
        self,
        frame: Scene3DFrame,
        vehicle,
        *,
        dataset: PlaybackDataset | None,
        frame_index: int | None,
        directivity_preset: str,
        emission_mode: str,
        emission_strength_db: float,
        wedge_span_deg: float,
        vertical_angle_deg: float,
        vertical_strength_db: float,
        highlight_receivers: bool,
        show_receiver_links: bool,
    ) -> None:
        if not frame.source_field_overlays:
            return
        profile = self._receiver_interaction_profile(directivity_preset)
        heading_deg = self._estimate_heading_deg(dataset, frame_index, vehicle.vehicle_id if hasattr(vehicle, 'vehicle_id') else '')
        heading_vector = (math.cos(math.radians(heading_deg)), math.sin(math.radians(heading_deg)))
        for receiver in frame.receivers:
            receiver.highlight_color = str(profile['highlight_color'])
            inside = any(self._point_in_polygon((receiver.x, receiver.y), overlay.footprint) for overlay in frame.source_field_overlays)
            if not inside and float(profile['margin_m']) > 0.0:
                inside = any(self._distance_to_polygon((receiver.x, receiver.y), overlay.footprint) <= float(profile['margin_m']) for overlay in frame.source_field_overlays)
            gain_db = directional_gain_db(
                (receiver.x, receiver.y, receiver.z),
                (vehicle.x, vehicle.y),
                heading_vector,
                mode=emission_mode,
                strength_db=emission_strength_db,
                wedge_angle_deg=wedge_span_deg,
                vertical_strength_db=vertical_strength_db,
                vertical_angle_deg=vertical_angle_deg,
                vehicle_z=float(getattr(vehicle, 'z', 0.35)),
            )
            receiver.directivity_gain_db = gain_db
            inside = inside and self._point_in_vertical_span(vehicle, receiver, vertical_angle_deg, vertical_strength_db)
            interaction_allowed = gain_db >= float(profile['gain_gate_db'])
            receiver.highlighted = bool(highlight_receivers and inside and interaction_allowed)
            if receiver.highlighted and show_receiver_links:
                frame.source_field_links.append(
                    InteractionLine3D(
                        start=(vehicle.x, vehicle.y, 0.45),
                        end=(receiver.x, receiver.y, receiver.z + 1.8),
                        color=str(profile['link_color']),
                    )
                )

    def _point_in_vertical_span(self, vehicle, receiver: Marker3D, vertical_angle_deg: float, vertical_strength_db: float) -> bool:
        if vertical_strength_db <= 0.0:
            return True
        dx = receiver.x - vehicle.x
        dy = receiver.y - vehicle.y
        horizontal_distance = max((dx * dx + dy * dy) ** 0.5, 1e-6)
        dz = receiver.z - float(getattr(vehicle, 'z', 0.35))
        angle = abs(math.degrees(math.atan2(dz, horizontal_distance)))
        return angle <= max(5.0, min(170.0, vertical_angle_deg)) * 0.5

    def _distance_to_polygon(self, point: tuple[float, float], polygon: list[tuple[float, float]]) -> float:
        if len(polygon) < 2:
            return 1e9
        x, y = point
        best = 1e9
        for i in range(len(polygon)):
            x1, y1 = polygon[i]
            x2, y2 = polygon[(i + 1) % len(polygon)]
            best = min(best, self._distance_to_segment(x, y, x1, y1, x2, y2))
        return best

    def _distance_to_segment(self, px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
        dx = x2 - x1
        dy = y2 - y1
        if abs(dx) < 1e-9 and abs(dy) < 1e-9:
            return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
        t = ((px - x1) * dx + (py - y1) * dy) / max(dx * dx + dy * dy, 1e-9)
        t = max(0.0, min(1.0, t))
        qx = x1 + t * dx
        qy = y1 + t * dy
        return ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5

    def _point_in_polygon(self, point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
        if len(polygon) < 3:
            return False
        x, y = point
        inside = False
        j = len(polygon) - 1
        for i in range(len(polygon)):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            denominator = (yj - yi)
            if abs(denominator) < 1e-9:
                denominator = 1e-9 if denominator >= 0 else -1e-9
            intersects = ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / denominator + xi)
            if intersects:
                inside = not inside
            j = i
        return inside
