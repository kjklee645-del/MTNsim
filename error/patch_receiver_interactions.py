from pathlib import Path

# update model
model_path = Path(r'D:\Codex\MTNsim\src\mtnsim\gui\models\scene_3d.py')
text = model_path.read_text(encoding='utf-8')
text = text.replace("class Marker3D:\n    x: float\n    y: float\n    z: float\n    color: str = '#f7fbff'\n    label: str = ''\n    highlighted: bool = False\n", "class Marker3D:\n    x: float\n    y: float\n    z: float\n    color: str = '#f7fbff'\n    label: str = ''\n    highlighted: bool = False\n    highlight_color: str = '#fff4b2'\n")
model_path.write_text(text, encoding='utf-8')

# update controller
ctrl_path = Path(r'D:\Codex\MTNsim\src\mtnsim\gui\controllers\scene3d_controller.py')
text = ctrl_path.read_text(encoding='utf-8')
text = text.replace(
"        self._apply_receiver_interactions(\n            frame,\n            target,\n            vertical_angle_deg=vertical_angle_deg,\n            vertical_strength_db=vertical_strength_db,\n            highlight_receivers=highlight_receivers,\n            show_receiver_links=show_receiver_links,\n        )\n",
"        self._apply_receiver_interactions(\n            frame,\n            target,\n            directivity_preset=directivity_preset,\n            vertical_angle_deg=vertical_angle_deg,\n            vertical_strength_db=vertical_strength_db,\n            highlight_receivers=highlight_receivers,\n            show_receiver_links=show_receiver_links,\n        )\n")

text = text.replace(
"    def _apply_receiver_interactions(\n        self,\n        frame: Scene3DFrame,\n        vehicle,\n        *,\n        vertical_angle_deg: float,\n        vertical_strength_db: float,\n        highlight_receivers: bool,\n        show_receiver_links: bool,\n    ) -> None:\n        if not frame.source_field_overlays:\n            return\n        for receiver in frame.receivers:\n            inside = any(self._point_in_polygon((receiver.x, receiver.y), overlay.footprint) for overlay in frame.source_field_overlays)\n            inside = inside and self._point_in_vertical_span(vehicle, receiver, vertical_angle_deg, vertical_strength_db)\n            receiver.highlighted = bool(highlight_receivers and inside)\n            if receiver.highlighted and show_receiver_links:\n                frame.source_field_links.append(\n                    InteractionLine3D(\n                        start=(vehicle.x, vehicle.y, 0.45),\n                        end=(receiver.x, receiver.y, receiver.z + 1.8),\n                        color='#fff2a6',\n                    )\n                )\n",
"    def _apply_receiver_interactions(\n        self,\n        frame: Scene3DFrame,\n        vehicle,\n        *,\n        directivity_preset: str,\n        vertical_angle_deg: float,\n        vertical_strength_db: float,\n        highlight_receivers: bool,\n        show_receiver_links: bool,\n    ) -> None:\n        if not frame.source_field_overlays:\n            return\n        profile = self._receiver_interaction_profile(directivity_preset)\n        for receiver in frame.receivers:\n            receiver.highlight_color = str(profile['highlight_color'])\n            inside = any(self._point_in_polygon((receiver.x, receiver.y), overlay.footprint) for overlay in frame.source_field_overlays)\n            if not inside and float(profile['margin_m']) > 0.0:\n                inside = any(self._distance_to_polygon((receiver.x, receiver.y), overlay.footprint) <= float(profile['margin_m']) for overlay in frame.source_field_overlays)\n            inside = inside and self._point_in_vertical_span(vehicle, receiver, vertical_angle_deg, vertical_strength_db)\n            receiver.highlighted = bool(highlight_receivers and inside)\n            if receiver.highlighted and show_receiver_links:\n                frame.source_field_links.append(\n                    InteractionLine3D(\n                        start=(vehicle.x, vehicle.y, 0.45),\n                        end=(receiver.x, receiver.y, receiver.z + 1.8),\n                        color=str(profile['link_color']),\n                    )\n                )\n")

insert_after = "    def _source_field_visual_profile(self, preset: str, mode: str) -> dict[str, float | str]:\n"
idx = text.index(insert_after)
# find end of function by next def _estimate_heading_deg
end_idx = text.index("\n    def _estimate_heading_deg", idx)
addition = "\n    def _receiver_interaction_profile(self, preset: str) -> dict[str, float | str]:\n        preset_key = str(preset or 'custom').lower()\n        profiles = {\n            'custom': {'highlight_color': '#fff4b2', 'link_color': '#fff2a6', 'margin_m': 2.0},\n            'passenger': {'highlight_color': '#b7f1ff', 'link_color': '#8be3ff', 'margin_m': 1.5},\n            'bus': {'highlight_color': '#ffe29a', 'link_color': '#ffd166', 'margin_m': 4.0},\n            'truck': {'highlight_color': '#ffc4a8', 'link_color': '#ff9b6e', 'margin_m': 7.0},\n        }\n        return profiles.get(preset_key, profiles['custom'])\n"
text = text[:end_idx] + addition + text[end_idx:]

insert_before = "    def _point_in_polygon(self, point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:\n"
idx = text.index(insert_before)
geometry_helpers = "    def _distance_to_polygon(self, point: tuple[float, float], polygon: list[tuple[float, float]]) -> float:\n        if len(polygon) < 2:\n            return 1e9\n        x, y = point\n        best = 1e9\n        for i in range(len(polygon)):\n            x1, y1 = polygon[i]\n            x2, y2 = polygon[(i + 1) % len(polygon)]\n            best = min(best, self._distance_to_segment(x, y, x1, y1, x2, y2))\n        return best\n\n    def _distance_to_segment(self, px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:\n        dx = x2 - x1\n        dy = y2 - y1\n        if abs(dx) < 1e-9 and abs(dy) < 1e-9:\n            return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5\n        t = ((px - x1) * dx + (py - y1) * dy) / max(dx * dx + dy * dy, 1e-9)\n        t = max(0.0, min(1.0, t))\n        qx = x1 + t * dx\n        qy = y1 + t * dy\n        return ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5\n\n"
text = text[:idx] + geometry_helpers + text[idx:]

ctrl_path.write_text(text, encoding='utf-8')

# update view receiver highlight color usage
view_path = Path(r'D:\Codex\MTNsim\src\mtnsim\gui\views\scene_3d_view.py')
text = view_path.read_text(encoding='utf-8')
text = text.replace(
"                line_color = QColor('#fff4b2') if marker.highlighted else QColor('#eff6ff')\n                fill_color = QColor('#fff4b2') if marker.highlighted else QColor('#eff6ff')\n",
"                line_color = QColor(marker.highlight_color) if marker.highlighted else QColor('#eff6ff')\n                fill_color = QColor(marker.highlight_color) if marker.highlighted else QColor('#eff6ff')\n")
text = text.replace(
"                    draw_screen_label(top, marker.label, fill='#121b24', border='#394d63', fg='#fff4b2' if marker.highlighted else '#eef6ff')\n",
"                    draw_screen_label(top, marker.label, fill='#121b24', border='#394d63', fg=marker.highlight_color if marker.highlighted else '#eef6ff')\n")
view_path.write_text(text, encoding='utf-8')
