from pathlib import Path

# scene_3d model
model_path = Path(r'D:\Codex\MTNsim\src\mtnsim\gui\models\scene_3d.py')
text = model_path.read_text(encoding='utf-8')
text = text.replace("class Marker3D:\n    x: float\n    y: float\n    z: float\n    color: str = '#f7fbff'\n    label: str = ''\n    highlighted: bool = False\n    highlight_color: str = '#fff4b2'\n", "class Marker3D:\n    x: float\n    y: float\n    z: float\n    color: str = '#f7fbff'\n    label: str = ''\n    highlighted: bool = False\n    highlight_color: str = '#fff4b2'\n    directivity_gain_db: float = 0.0\n")
model_path.write_text(text, encoding='utf-8')

# scene3d controller
ctrl_path = Path(r'D:\Codex\MTNsim\src\mtnsim\gui\controllers\scene3d_controller.py')
text = ctrl_path.read_text(encoding='utf-8')
if "from mtnsim.acoustics.emission.road_vehicle import directional_gain_db" not in text:
    text = text.replace("from mtnsim.gui.controllers.playback_controller import PlaybackDataset, PlaybackFrame\n", "from mtnsim.acoustics.emission.road_vehicle import directional_gain_db\nfrom mtnsim.gui.controllers.playback_controller import PlaybackDataset, PlaybackFrame\n")
text = text.replace(
"        directivity_preset: str = 'custom',\n    ) -> Scene3DFrame | None:\n",
"        directivity_preset: str = 'custom',\n        emission_mode: str = 'isotropic',\n        emission_strength_db: float = 0.0,\n    ) -> Scene3DFrame | None:\n")
text = text.replace(
"        for receiver in frame.receivers:\n            receiver.highlighted = False\n",
"        for receiver in frame.receivers:\n            receiver.highlighted = False\n            receiver.directivity_gain_db = 0.0\n")
text = text.replace(
"            vertical_angle_deg=vertical_angle_deg,\n            vertical_strength_db=vertical_strength_db,\n            highlight_receivers=highlight_receivers,\n            show_receiver_links=show_receiver_links,\n        )\n",
"            emission_mode=emission_mode,\n            emission_strength_db=emission_strength_db,\n            wedge_span_deg=wedge_span_deg,\n            vertical_angle_deg=vertical_angle_deg,\n            vertical_strength_db=vertical_strength_db,\n            highlight_receivers=highlight_receivers,\n            show_receiver_links=show_receiver_links,\n        )\n")
text = text.replace(
"        directivity_preset: str,\n        vertical_angle_deg: float,\n        vertical_strength_db: float,\n        highlight_receivers: bool,\n        show_receiver_links: bool,\n    ) -> None:\n",
"        directivity_preset: str,\n        emission_mode: str,\n        emission_strength_db: float,\n        wedge_span_deg: float,\n        vertical_angle_deg: float,\n        vertical_strength_db: float,\n        highlight_receivers: bool,\n        show_receiver_links: bool,\n    ) -> None:\n")
text = text.replace(
"        profile = self._receiver_interaction_profile(directivity_preset)\n        for receiver in frame.receivers:\n            receiver.highlight_color = str(profile['highlight_color'])\n            inside = any(self._point_in_polygon((receiver.x, receiver.y), overlay.footprint) for overlay in frame.source_field_overlays)\n            if not inside and float(profile['margin_m']) > 0.0:\n                inside = any(self._distance_to_polygon((receiver.x, receiver.y), overlay.footprint) <= float(profile['margin_m']) for overlay in frame.source_field_overlays)\n            inside = inside and self._point_in_vertical_span(vehicle, receiver, vertical_angle_deg, vertical_strength_db)\n            receiver.highlighted = bool(highlight_receivers and inside)\n            if receiver.highlighted and show_receiver_links:\n                frame.source_field_links.append(\n                    InteractionLine3D(\n                        start=(vehicle.x, vehicle.y, 0.45),\n                        end=(receiver.x, receiver.y, receiver.z + 1.8),\n                        color=str(profile['link_color']),\n                    )\n                )\n",
"        profile = self._receiver_interaction_profile(directivity_preset)\n        heading_deg = self._estimate_heading_deg(None, None, '')\n        heading_vector = None\n        if frame.vehicles:\n            for candidate in frame.vehicles:\n                if abs(candidate.x - vehicle.x) < 1e-6 and abs(candidate.y - vehicle.y) < 1e-6:\n                    break\n        if hasattr(vehicle, 'vehicle_id'):\n            try:\n                heading_deg = self._estimate_heading_deg(getattr(self, '_active_dataset', None), getattr(self, '_active_frame_index', None), vehicle.vehicle_id)\n            except Exception:\n                heading_deg = 0.0\n        heading_vector = (math.cos(math.radians(heading_deg)), math.sin(math.radians(heading_deg)))\n        for receiver in frame.receivers:\n            receiver.highlight_color = str(profile['highlight_color'])\n            inside = any(self._point_in_polygon((receiver.x, receiver.y), overlay.footprint) for overlay in frame.source_field_overlays)\n            if not inside and float(profile['margin_m']) > 0.0:\n                inside = any(self._distance_to_polygon((receiver.x, receiver.y), overlay.footprint) <= float(profile['margin_m']) for overlay in frame.source_field_overlays)\n            gain_db = directional_gain_db(\n                (receiver.x, receiver.y, receiver.z),\n                (vehicle.x, vehicle.y),\n                heading_vector,\n                mode=emission_mode,\n                strength_db=emission_strength_db,\n                wedge_angle_deg=wedge_span_deg,\n                vertical_strength_db=vertical_strength_db,\n                vertical_angle_deg=vertical_angle_deg,\n                vehicle_z=0.35,\n            )\n            receiver.directivity_gain_db = gain_db\n            inside = inside and self._point_in_vertical_span(vehicle, receiver, vertical_angle_deg, vertical_strength_db)\n            interaction_allowed = gain_db >= float(profile['gain_gate_db'])\n            receiver.highlighted = bool(highlight_receivers and inside and interaction_allowed)\n            if receiver.highlighted and show_receiver_links:\n                frame.source_field_links.append(\n                    InteractionLine3D(\n                        start=(vehicle.x, vehicle.y, 0.45),\n                        end=(receiver.x, receiver.y, receiver.z + 1.8),\n                        color=str(profile['link_color']),\n                    )\n                )\n")
text = text.replace(
"            'custom': {'highlight_color': '#fff4b2', 'link_color': '#fff2a6', 'margin_m': 2.0},\n            'passenger': {'highlight_color': '#b7f1ff', 'link_color': '#8be3ff', 'margin_m': 1.5},\n            'bus': {'highlight_color': '#ffe29a', 'link_color': '#ffd166', 'margin_m': 4.0},\n            'truck': {'highlight_color': '#ffc4a8', 'link_color': '#ff9b6e', 'margin_m': 7.0},\n",
"            'custom': {'highlight_color': '#fff4b2', 'link_color': '#fff2a6', 'margin_m': 2.0, 'gain_gate_db': -3.5},\n            'passenger': {'highlight_color': '#b7f1ff', 'link_color': '#8be3ff', 'margin_m': 1.5, 'gain_gate_db': -1.5},\n            'bus': {'highlight_color': '#ffe29a', 'link_color': '#ffd166', 'margin_m': 4.0, 'gain_gate_db': -3.0},\n            'truck': {'highlight_color': '#ffc4a8', 'link_color': '#ff9b6e', 'margin_m': 7.0, 'gain_gate_db': -4.5},\n")
ctrl_path.write_text(text, encoding='utf-8')

# main_window pass calculation mode/strength and active playback context to controller
main_path = Path(r'D:\Codex\MTNsim\src\mtnsim\gui\main_window.py')
text = main_path.read_text(encoding='utf-8')
text = text.replace(
"            scene3d_frame = self.scene3d_controller.apply_source_field_overlay(\n                scene3d_frame,\n                frame,\n                dataset=dataset,\n                frame_index=frame_index,\n",
"            self.scene3d_controller._active_dataset = dataset\n            self.scene3d_controller._active_frame_index = frame_index\n            scene3d_frame = self.scene3d_controller.apply_source_field_overlay(\n                scene3d_frame,\n                frame,\n                dataset=dataset,\n                frame_index=frame_index,\n")
text = text.replace(
"                vertical_angle_deg=source_field_settings['vertical_angle_deg'],\n                vertical_strength_db=source_field_settings['vertical_strength_db'],\n                highlight_receivers=bool(source_field_settings['highlight_receivers']),\n                show_receiver_links=bool(source_field_settings['show_receiver_links']),\n                directivity_preset=str(source_field_settings.get('calculation_preset', 'custom')),\n",
"                vertical_angle_deg=source_field_settings['vertical_angle_deg'],\n                vertical_strength_db=source_field_settings['vertical_strength_db'],\n                highlight_receivers=bool(source_field_settings['highlight_receivers']),\n                show_receiver_links=bool(source_field_settings['show_receiver_links']),\n                directivity_preset=str(source_field_settings.get('calculation_preset', 'custom')),\n                emission_mode=str(source_field_settings.get('calculation_mode', 'isotropic')),\n                emission_strength_db=float(source_field_settings.get('calculation_strength_db', 0.0)),\n")
main_path.write_text(text, encoding='utf-8')

# scene_3d_view hover label shows gain
view_path = Path(r'D:\Codex\MTNsim\src\mtnsim\gui\views\scene_3d_view.py')
text = view_path.read_text(encoding='utf-8')
text = text.replace(
"                register_hover_target(top, marker.label, 'Receiver', radius=14.0)\n",
"                hover_label = marker.label if not marker.highlighted else f\"{marker.label} | gain {marker.directivity_gain_db:.1f} dB\"\n                register_hover_target(top, hover_label, 'Receiver', radius=14.0)\n")
view_path.write_text(text, encoding='utf-8')
