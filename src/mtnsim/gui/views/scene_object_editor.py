from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class SceneObjectEditorView(QWidget):
    save_as_requested = Signal(dict)
    preview_requested = Signal(dict)
    object_selected = Signal(str, str)
    draw_mode_requested = Signal(dict)
    finish_draw_requested = Signal()
    cancel_draw_requested = Signal()

    OBJECT_TYPES = [
        ('noise_barriers', 'Noise Barriers'),
        ('buildings', 'Buildings'),
        ('terrain_edges', 'Terrain Edges'),
        ('ground_surfaces', 'Ground Surfaces'),
        ('vegetation_zones', 'Vegetation Zones'),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_source_path = ''
        self._source_scenario_name = ''
        self._source_description = ''
        self._scene_data: dict[str, list[dict]] = {key: [] for key, _ in self.OBJECT_TYPES}
        self._suspend = False
        self._selected_object_key: tuple[str, str] | None = None
        self._undo_stack: list[dict] = []
        self._redo_stack: list[dict] = []
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel('Scene Object Editor')
        title.setObjectName('pageTitle')
        root.addWidget(title)

        self.info_box = QTextEdit()
        self.info_box.setObjectName('infoCard')
        self.info_box.setReadOnly(True)
        self.info_box.setMaximumHeight(110)
        root.addWidget(self.info_box)

        meta_title = QLabel('Derived Scenario')
        meta_title.setObjectName('sectionTitle')
        root.addWidget(meta_title)

        meta_card = QFrame()
        meta_card.setObjectName('infoCard')
        meta_layout = QVBoxLayout(meta_card)
        meta_layout.setContentsMargins(14, 14, 14, 14)
        meta_form = QFormLayout()
        self.scenario_name_edit = QLineEdit()
        self.description_edit = QLineEdit()
        meta_form.addRow('Scenario Name', self.scenario_name_edit)
        meta_form.addRow('Description', self.description_edit)
        meta_layout.addLayout(meta_form)
        root.addWidget(meta_card)

        main_row = QHBoxLayout()
        main_row.setSpacing(12)
        root.addLayout(main_row, 1)

        left_col = QVBoxLayout()
        main_row.addLayout(left_col, 1)

        type_title = QLabel('Object Type')
        type_title.setObjectName('sectionTitle')
        left_col.addWidget(type_title)
        self.object_type_combo = QComboBox()
        for key, label in self.OBJECT_TYPES:
            self.object_type_combo.addItem(label, key)
        self.object_type_combo.currentIndexChanged.connect(self._refresh_object_list)
        left_col.addWidget(self.object_type_combo)

        list_title = QLabel('Objects')
        list_title.setObjectName('sectionTitle')
        left_col.addWidget(list_title)
        self.object_list = QListWidget()
        self.object_list.setObjectName('infoCard')
        self.object_list.currentRowChanged.connect(self._load_selected_object_into_form)
        left_col.addWidget(self.object_list, 1)

        left_buttons = QHBoxLayout()
        self.add_button = QPushButton('Add New')
        self.add_button.clicked.connect(self._add_new_object)
        self.duplicate_button = QPushButton('Duplicate Selected')
        self.duplicate_button.clicked.connect(self._duplicate_selected_object)
        self.delete_button = QPushButton('Delete Selected')
        self.delete_button.clicked.connect(self._delete_selected_object)
        left_buttons.addWidget(self.add_button)
        left_buttons.addWidget(self.duplicate_button)
        left_buttons.addWidget(self.delete_button)
        left_col.addLayout(left_buttons)

        history_buttons = QHBoxLayout()
        self.undo_button = QPushButton('Undo')
        self.undo_button.clicked.connect(self._undo)
        self.redo_button = QPushButton('Redo')
        self.redo_button.clicked.connect(self._redo)
        history_buttons.addWidget(self.undo_button)
        history_buttons.addWidget(self.redo_button)
        left_col.addLayout(history_buttons)

        draw_buttons = QHBoxLayout()
        self.draw_button = QPushButton('Draw In Scene View')
        self.draw_button.clicked.connect(self._request_draw_mode)
        self.finish_draw_button = QPushButton('Finish Draw')
        self.finish_draw_button.clicked.connect(self.finish_draw_requested.emit)
        self.cancel_draw_button = QPushButton('Cancel Draw')
        self.cancel_draw_button.clicked.connect(self.cancel_draw_requested.emit)
        draw_buttons.addWidget(self.draw_button)
        draw_buttons.addWidget(self.finish_draw_button)
        draw_buttons.addWidget(self.cancel_draw_button)
        left_col.addLayout(draw_buttons)

        right_col = QVBoxLayout()
        main_row.addLayout(right_col, 2)

        prop_title = QLabel('Object Properties')
        prop_title.setObjectName('sectionTitle')
        right_col.addWidget(prop_title)

        form_card = QFrame()
        form_card.setObjectName('infoCard')
        form_card_layout = QVBoxLayout(form_card)
        form_card_layout.setContentsMargins(14, 14, 14, 14)
        form_card_layout.setSpacing(8)

        self.form = QFormLayout()
        self.object_id_edit = QLineEdit()
        self.material_edit = QLineEdit()
        self.x1_spin = self._make_spin()
        self.y1_spin = self._make_spin()
        self.x2_spin = self._make_spin()
        self.y2_spin = self._make_spin()
        self.height_spin = self._make_spin(0.0, 1000.0)
        self.attenuation_spin = self._make_spin(0.0, 1000.0)
        self.footprint_edit = QTextEdit()
        self.footprint_edit.setObjectName('infoCard')
        self.footprint_edit.setMinimumHeight(80)

        self.form.addRow('ID', self.object_id_edit)
        self.form.addRow('Material', self.material_edit)
        self.form.addRow('X1', self.x1_spin)
        self.form.addRow('Y1', self.y1_spin)
        self.form.addRow('X2', self.x2_spin)
        self.form.addRow('Y2', self.y2_spin)
        self.form.addRow('Height (m)', self.height_spin)
        self.form.addRow('Attenuation (dB)', self.attenuation_spin)
        self.form.addRow('Footprint', self.footprint_edit)
        form_card_layout.addLayout(self.form)

        helper = QLabel('Footprint format: one x,y pair per line. Example:\n430,0\n570,0\n570,76\n430,76')
        helper.setObjectName('homeHelperLabel')
        form_card_layout.addWidget(helper)

        form_buttons = QHBoxLayout()
        self.apply_button = QPushButton('Apply Object Changes')
        self.apply_button.clicked.connect(self._apply_form_to_object)
        self.reset_button = QPushButton('Reset Form')
        self.reset_button.clicked.connect(self._reset_form)
        form_buttons.addWidget(self.apply_button)
        form_buttons.addWidget(self.reset_button)
        form_card_layout.addLayout(form_buttons)
        right_col.addWidget(form_card, 1)

        bottom = QHBoxLayout()
        self.save_as_button = QPushButton('Save As New Scenario')
        self.save_as_button.clicked.connect(self._emit_save_as)
        bottom.addWidget(self.save_as_button)
        bottom.addStretch(1)
        root.addLayout(bottom)

        self.status_label = QLabel('Select a scenario to edit its scene objects.')
        self.status_label.setObjectName('statusBadgeNeutral')
        root.addWidget(self.status_label)

    def _make_spin(self, minimum: float = -100000.0, maximum: float = 100000.0) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(2)
        return spin

    def current_object_type(self) -> str:
        return str(self.object_type_combo.currentData())

    def set_scenario(self, scenario_path, scenario) -> None:
        self._suspend = True
        self._current_source_path = str(scenario_path) if scenario_path is not None else ''
        self._source_scenario_name = scenario.scenario.name
        self._source_description = scenario.scenario.description
        self.scenario_name_edit.setText(f'{scenario.scenario.name}_scene_variant')
        self.description_edit.setText(scenario.scenario.description)
        self._scene_data = {
            'noise_barriers': [
                {'id': item.id, 'x1': item.x1, 'y1': item.y1, 'x2': item.x2, 'y2': item.y2, 'height_meters': item.height_meters, 'attenuation_db': item.attenuation_db, 'material': item.material}
                for item in scenario.scene.noise_barriers
            ],
            'buildings': [
                {'id': item.id, 'footprint': [list(point) for point in item.footprint], 'height_meters': item.height_meters, 'attenuation_db': item.attenuation_db, 'material': item.material}
                for item in scenario.scene.buildings
            ],
            'terrain_edges': [
                {'id': item.id, 'x1': item.x1, 'y1': item.y1, 'x2': item.x2, 'y2': item.y2, 'height_meters': item.height_meters, 'attenuation_db': item.attenuation_db, 'material': item.material}
                for item in scenario.scene.terrain_edges
            ],
            'ground_surfaces': [
                {'id': item.id, 'footprint': [list(point) for point in item.footprint], 'material': item.material}
                for item in scenario.scene.ground_surfaces
            ],
            'vegetation_zones': [
                {'id': item.id, 'footprint': [list(point) for point in item.footprint], 'height_meters': item.height_meters, 'attenuation_db': item.attenuation_db, 'material': item.material}
                for item in scenario.scene.vegetation_zones
            ],
        }
        self.info_box.setPlainText('\n'.join([
            f'Source file: {scenario_path}',
            f'Noise barriers: {len(self._scene_data["noise_barriers"])}',
            f'Buildings: {len(self._scene_data["buildings"])}',
            f'Terrain edges: {len(self._scene_data["terrain_edges"])}',
            f'Ground surfaces: {len(self._scene_data["ground_surfaces"])}',
            f'Vegetation zones: {len(self._scene_data["vegetation_zones"])}',
        ]))
        self._suspend = False
        self._undo_stack = []
        self._redo_stack = []
        self._refresh_object_list()
        self._update_history_buttons()
        self.set_status('Edit scene objects and use Save As to create a derived scenario.')
        self._emit_preview()

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)
        self._apply_status_style(text)

    def set_draw_status(self, text: str) -> None:
        self.set_status(text)

    def _capture_history_state(self) -> dict:
        return {
            'scene': deepcopy(self._scene_data),
            'object_type': self.current_object_type(),
            'selected': self._selected_object_key,
        }

    def _restore_history_state(self, state: dict) -> None:
        self._scene_data = deepcopy(state.get('scene', self._scene_data))
        target_type = state.get('object_type')
        if target_type:
            target_index = self.object_type_combo.findData(target_type)
            if target_index >= 0 and self.object_type_combo.currentIndex() != target_index:
                self.object_type_combo.setCurrentIndex(target_index)
        self._refresh_object_list()
        selected = state.get('selected')
        if selected:
            self.set_selected_object(selected[0], selected[1])
        self._emit_preview()
        self._update_history_buttons()

    def _push_undo_state(self) -> None:
        self._undo_stack.append(self._capture_history_state())
        if len(self._undo_stack) > 50:
            self._undo_stack = self._undo_stack[-50:]
        self._redo_stack = []
        self._update_history_buttons()

    def _update_history_buttons(self) -> None:
        self.undo_button.setEnabled(bool(self._undo_stack))
        self.redo_button.setEnabled(bool(self._redo_stack))

    def _undo(self) -> None:
        if not self._undo_stack:
            return
        self._redo_stack.append(self._capture_history_state())
        state = self._undo_stack.pop()
        self._restore_history_state(state)
        self.set_status('Undid scene-object edit.')

    def _redo(self) -> None:
        if not self._redo_stack:
            return
        self._undo_stack.append(self._capture_history_state())
        state = self._redo_stack.pop()
        self._restore_history_state(state)
        self.set_status('Redid scene-object edit.')

    def add_drawn_object(self, object_type: str, payload: dict) -> None:
        if object_type not in self._scene_data:
            return
        self._push_undo_state()
        item = deepcopy(payload)
        item['id'] = self._generate_unique_id(object_type, str(item.get('id', '')).strip())
        self._scene_data.setdefault(object_type, []).append(item)
        target_index = self.object_type_combo.findData(object_type)
        if target_index >= 0 and self.object_type_combo.currentIndex() != target_index:
            self.object_type_combo.setCurrentIndex(target_index)
        self._refresh_object_list()
        self.set_selected_object(object_type, item['id'])
        self.set_status(f'Added {item["id"]} from Scene View.')
        self._emit_preview()

    def update_object_geometry(self, object_type: str, object_id: str, geometry_payload: dict) -> None:
        items = self._scene_data.get(object_type, [])
        for index, item in enumerate(items):
            if str(item.get('id', '')) != object_id:
                continue
            self._push_undo_state()
            updated = deepcopy(item)
            updated.update(geometry_payload)
            items[index] = updated
            self._refresh_object_list()
            self.set_selected_object(object_type, object_id)
            self._emit_preview()
            return

    def _refresh_object_list(self) -> None:
        self.object_list.clear()
        object_type = self.current_object_type()
        for item in self._scene_data.get(object_type, []):
            self.object_list.addItem(QListWidgetItem(item.get('id', object_type)))
        if self.object_list.count() > 0:
            self.object_list.setCurrentRow(0)
        else:
            self._reset_form()
        self._refresh_field_visibility()

    def set_selected_object(self, object_type: str, object_id: str) -> None:
        if not object_type or not object_id:
            return
        target_index = self.object_type_combo.findData(object_type)
        if target_index >= 0 and self.object_type_combo.currentIndex() != target_index:
            self.object_type_combo.setCurrentIndex(target_index)
        items = self._scene_data.get(object_type, [])
        for row, item in enumerate(items):
            if str(item.get('id', '')) == object_id:
                self.object_list.setCurrentRow(row)
                self.set_status(f'Selected {object_id} from scene view.')
                return

    def _request_draw_mode(self) -> None:
        payload = {
            'object_type': self.current_object_type(),
            'template': self._build_draw_template(self.current_object_type()),
        }
        self.draw_mode_requested.emit(payload)
        object_type = payload['object_type']
        if object_type in {'noise_barriers', 'terrain_edges'}:
            self.set_status(f'Draw mode active for {object_type}: click two points in Scene View.')
        else:
            self.set_status(f'Draw mode active for {object_type}: click polygon vertices, then Finish Draw.')

    def _build_draw_template(self, object_type: str) -> dict:
        template = self._default_object(object_type)
        proposed_id = self.object_id_edit.text().strip()
        if proposed_id:
            template['id'] = proposed_id
        material = self.material_edit.text().strip()
        if material:
            template['material'] = material
        if object_type in {'noise_barriers', 'terrain_edges', 'buildings', 'vegetation_zones'}:
            template['height_meters'] = float(self.height_spin.value() or template.get('height_meters', 0.0))
            template['attenuation_db'] = float(self.attenuation_spin.value() or template.get('attenuation_db', 0.0))
        return template

    def _generate_unique_id(self, object_type: str, proposed_id: str) -> str:
        default_id = self._default_object(object_type)['id']
        base = proposed_id or default_id
        existing = {str(item.get('id', '')) for item in self._scene_data.get(object_type, [])}
        if base not in existing:
            return base
        prefix = base.rsplit('_', 1)[0] if '_' in base else base
        counter = 2
        while f'{prefix}_{counter}' in existing:
            counter += 1
        return f'{prefix}_{counter}'

    def _refresh_field_visibility(self) -> None:
        object_type = self.current_object_type()
        is_linear = object_type in {'noise_barriers', 'terrain_edges'}
        has_polygon = object_type in {'buildings', 'ground_surfaces', 'vegetation_zones'}
        has_height = object_type in {'noise_barriers', 'terrain_edges', 'buildings', 'vegetation_zones'}
        has_attenuation = object_type in {'noise_barriers', 'terrain_edges', 'buildings', 'vegetation_zones'}
        self._set_field_visible(self.x1_spin, is_linear)
        self._set_field_visible(self.y1_spin, is_linear)
        self._set_field_visible(self.x2_spin, is_linear)
        self._set_field_visible(self.y2_spin, is_linear)
        self._set_field_visible(self.footprint_edit, has_polygon)
        self._set_field_visible(self.height_spin, has_height)
        self._set_field_visible(self.attenuation_spin, has_attenuation)

    def _set_field_visible(self, widget, visible: bool) -> None:
        widget.setVisible(visible)
        label = self.form.labelForField(widget)
        if label is not None:
            label.setVisible(visible)

    def _load_selected_object_into_form(self, row: int) -> None:
        if row < 0:
            self._reset_form()
            return
        object_type = self.current_object_type()
        items = self._scene_data.get(object_type, [])
        if row >= len(items):
            self._reset_form()
            return
        item = items[row]
        self._suspend = True
        self.object_id_edit.setText(str(item.get('id', '')))
        self.material_edit.setText(str(item.get('material', 'generic')))
        self.x1_spin.setValue(float(item.get('x1', 0.0)))
        self.y1_spin.setValue(float(item.get('y1', 0.0)))
        self.x2_spin.setValue(float(item.get('x2', 0.0)))
        self.y2_spin.setValue(float(item.get('y2', 0.0)))
        self.height_spin.setValue(float(item.get('height_meters', 0.0)))
        self.attenuation_spin.setValue(float(item.get('attenuation_db', 0.0)))
        self.footprint_edit.setPlainText('\n'.join(f'{p[0]},{p[1]}' for p in item.get('footprint', [])))
        self._suspend = False
        self._selected_object_key = (object_type, str(item.get('id', '')))
        self.object_selected.emit(object_type, str(item.get('id', '')))

    def _reset_form(self) -> None:
        self._suspend = True
        self.object_id_edit.clear()
        self.material_edit.setText('generic')
        for spin in [self.x1_spin, self.y1_spin, self.x2_spin, self.y2_spin, self.height_spin, self.attenuation_spin]:
            spin.setValue(0.0)
        self.footprint_edit.clear()
        self._suspend = False

    def _default_object(self, object_type: str) -> dict:
        defaults = {
            'noise_barriers': {'id': 'barrier_1', 'x1': 0.0, 'y1': 0.0, 'x2': 20.0, 'y2': 0.0, 'height_meters': 4.0, 'attenuation_db': 8.0, 'material': 'concrete'},
            'buildings': {'id': 'building_1', 'footprint': [[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]], 'height_meters': 10.0, 'attenuation_db': 9.0, 'material': 'concrete'},
            'terrain_edges': {'id': 'terrain_edge_1', 'x1': 0.0, 'y1': 0.0, 'x2': 20.0, 'y2': 0.0, 'height_meters': 3.0, 'attenuation_db': 6.0, 'material': 'soil'},
            'ground_surfaces': {'id': 'ground_1', 'footprint': [[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]], 'material': 'grass'},
            'vegetation_zones': {'id': 'vegetation_1', 'footprint': [[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]], 'height_meters': 6.0, 'attenuation_db': 2.5, 'material': 'dense_trees'},
        }
        return deepcopy(defaults[object_type])

    def _add_new_object(self) -> None:
        object_type = self.current_object_type()
        self._push_undo_state()
        items = self._scene_data.setdefault(object_type, [])
        obj = self._default_object(object_type)
        prefix = obj['id'].rsplit('_', 1)[0]
        obj['id'] = f'{prefix}_{len(items) + 1}'
        items.append(obj)
        self._refresh_object_list()
        self.object_list.setCurrentRow(len(items) - 1)
        self._emit_preview()

    def _duplicate_selected_object(self) -> None:
        row = self.object_list.currentRow()
        if row < 0:
            return
        object_type = self.current_object_type()
        items = self._scene_data.get(object_type, [])
        if row >= len(items):
            return
        self._push_undo_state()
        duplicate = deepcopy(items[row])
        duplicate['id'] = self._generate_unique_id(object_type, str(duplicate.get('id', '')).strip())
        items.insert(row + 1, duplicate)
        self._refresh_object_list()
        self.object_list.setCurrentRow(row + 1)
        self.set_status(f'Duplicated {duplicate["id"]}.')
        self._emit_preview()

    def _delete_selected_object(self) -> None:
        row = self.object_list.currentRow()
        if row < 0:
            return
        object_type = self.current_object_type()
        items = self._scene_data.get(object_type, [])
        if row < len(items):
            self._push_undo_state()
            items.pop(row)
        self._refresh_object_list()
        self._emit_preview()

    def _apply_form_to_object(self) -> None:
        row = self.object_list.currentRow()
        if row < 0:
            QMessageBox.information(self, 'Scene Object Editor', 'Select or add an object first.')
            return
        object_type = self.current_object_type()
        payload, errors = self._build_object_from_form(object_type)
        if errors:
            self.set_status(f'Cannot apply object: {errors[0]}')
            QMessageBox.warning(self, 'Scene Object Validation', '\n'.join(errors))
            return
        self._push_undo_state()
        self._scene_data[object_type][row] = payload
        self._refresh_object_list()
        self.object_list.setCurrentRow(row)
        self.set_status(f'Updated {payload["id"]}.')
        self._emit_preview()

    def _parse_footprint(self) -> tuple[list[list[float]], list[str]]:
        points = []
        errors = []
        for line in [line.strip() for line in self.footprint_edit.toPlainText().splitlines() if line.strip()]:
            pieces = [piece.strip() for piece in line.split(',')]
            if len(pieces) != 2:
                errors.append(f'Invalid footprint row: {line}')
                continue
            try:
                points.append([float(pieces[0]), float(pieces[1])])
            except ValueError:
                errors.append(f'Non-numeric footprint coordinate: {line}')
        if self.current_object_type() in {'buildings', 'ground_surfaces', 'vegetation_zones'} and points and len(points) < 3:
            errors.append('Polygon objects require at least three footprint points.')
        return points, errors

    def _build_object_from_form(self, object_type: str) -> tuple[dict | None, list[str]]:
        errors = []
        payload = {
            'id': self.object_id_edit.text().strip(),
            'material': self.material_edit.text().strip() or 'generic',
        }
        if not payload['id']:
            errors.append('Object ID must not be empty.')
        if object_type in {'noise_barriers', 'terrain_edges'}:
            payload.update({
                'x1': float(self.x1_spin.value()), 'y1': float(self.y1_spin.value()),
                'x2': float(self.x2_spin.value()), 'y2': float(self.y2_spin.value()),
                'height_meters': float(self.height_spin.value()),
                'attenuation_db': float(self.attenuation_spin.value()),
            })
            if payload['x1'] == payload['x2'] and payload['y1'] == payload['y2']:
                errors.append('Linear objects require two distinct endpoints.')
        else:
            footprint, fp_errors = self._parse_footprint()
            errors.extend(fp_errors)
            payload['footprint'] = footprint
            if object_type in {'buildings', 'vegetation_zones'}:
                payload['height_meters'] = float(self.height_spin.value())
                payload['attenuation_db'] = float(self.attenuation_spin.value())
        return (payload if not errors else None), errors

    def _validate_scene_payload(self, scene_payload: dict[str, list[dict]]) -> list[str]:
        errors = []
        for object_type, items in scene_payload.items():
            seen_ids = set()
            for item in items:
                object_id = str(item.get('id', '')).strip()
                if not object_id:
                    errors.append(f'{object_type}: object ID must not be empty.')
                    continue
                if object_id in seen_ids:
                    errors.append(f'{object_type}: duplicate object ID {object_id}.')
                seen_ids.add(object_id)
        return errors

    def _build_payload(self) -> dict:
        return {
            'source_path': self._current_source_path,
            'scenario_name': self.scenario_name_edit.text().strip() or f'{self._source_scenario_name}_scene_variant',
            'description': self.description_edit.text().strip() or self._source_description,
            'scene': deepcopy(self._scene_data),
        }

    def _emit_preview(self) -> None:
        if self._suspend or not self._current_source_path:
            return
        self.preview_requested.emit(self._build_payload())

    def _emit_save_as(self) -> None:
        if not self._current_source_path:
            return
        payload = self._build_payload()
        errors = self._validate_scene_payload(payload['scene'])
        if errors:
            self.set_status(f'Cannot save scene objects: {errors[0]}')
            QMessageBox.warning(self, 'Scene Object Validation', '\n'.join(errors))
            return
        self.set_status('Scene objects ready to save.')
        self.save_as_requested.emit(payload)

    def _apply_status_style(self, text: str) -> None:
        lowered = text.lower()
        if 'cannot' in lowered or 'error' in lowered:
            object_name = 'statusBadgeWarning'
        elif 'ready' in lowered or 'updated' in lowered:
            object_name = 'statusBadgeReady'
        else:
            object_name = 'statusBadgeNeutral'
        if self.status_label.objectName() != object_name:
            self.status_label.setObjectName(object_name)
            self.status_label.style().unpolish(self.status_label)
            self.status_label.style().polish(self.status_label)
