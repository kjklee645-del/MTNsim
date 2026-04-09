from pathlib import Path

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f'missing snippet: {label}')
    return text.replace(old, new, 1)

scene_path = Path(r'D:\Codex\MTNsim\src\mtnsim\gui\views\scene_3d_view.py')
scene = scene_path.read_text(encoding='utf-8')

scene = replace_once(scene, '''        def lerp_point(p1: QPointF, p2: QPointF, t: float) -> QPointF:
            return QPointF(p1.x() + (p2.x() - p1.x()) * t, p1.y() + (p2.y() - p1.y()) * t)

        def draw_screen_label(anchor: QPointF, text_value: str, *, fill: str = '#111a23', border: str = '#314355', fg: str = '#eef6ff') -> None:
''', '''        def lerp_point(p1: QPointF, p2: QPointF, t: float) -> QPointF:
            return QPointF(p1.x() + (p2.x() - p1.x()) * t, p1.y() + (p2.y() - p1.y()) * t)

        hover_targets: list[dict[str, object]] = []

        def register_hover_target(point: QPointF, label: str, kind: str, *, radius: float = 16.0) -> None:
            if not label:
                return
            hover_targets.append({
                'point': QPointF(point),
                'label': label,
                'kind': kind,
                'radius': radius,
            })

        def draw_screen_label(anchor: QPointF, text_value: str, *, fill: str = '#111a23', border: str = '#314355', fg: str = '#eef6ff') -> None:
''', 'hover helper')

scene = replace_once(scene, '''                if mesh.label:
                    draw_screen_label(center, mesh.label, fill='#16212d', border='#3c5269')
''', '''                if mesh.label:
                    draw_screen_label(center, mesh.label, fill='#16212d', border='#3c5269')
                register_hover_target(center, mesh.label or 'Building', 'Building', radius=20.0)
''', 'prism hover')

scene = replace_once(scene, '''            painter.setBrush(QColor(mesh.color).lighter(118))
            painter.setPen(QPen(QColor('#fff0d9') if is_barrier else '#dfe8cf', 1.1))
            painter.drawPolygon(top)
''', '''            painter.setBrush(QColor(mesh.color).lighter(118))
            painter.setPen(QPen(QColor('#fff0d9') if is_barrier else '#dfe8cf', 1.1))
            painter.drawPolygon(top)
            anchor = QPointF((p_front_d.x() + p_front_c.x()) * 0.5, (p_front_d.y() + p_front_c.y()) * 0.5)
            register_hover_target(anchor, mesh.label or ('Barrier' if is_barrier else 'Terrain Edge'), 'Barrier' if is_barrier else 'Terrain', radius=20.0)
''', 'wall hover')

scene = replace_once(scene, '''                if marker.highlighted or label_receivers:
                    draw_screen_label(top, marker.label, fill='#121b24', border='#394d63', fg='#fff4b2' if marker.highlighted else '#eef6ff')
''', '''                if marker.highlighted or label_receivers:
                    draw_screen_label(top, marker.label, fill='#121b24', border='#394d63', fg='#fff4b2' if marker.highlighted else '#eef6ff')
                register_hover_target(top, marker.label, 'Receiver', radius=14.0)
''', 'receiver hover')

scene = replace_once(scene, '''                if vehicle.selected or label_vehicles:
                    vehicle_label = vehicle.vehicle_id if vehicle.selected else vehicle.vehicle_type or vehicle.vehicle_id
                    draw_screen_label(top, vehicle_label, fill='#102032', border='#40627c', fg='#eef8ff')

        painter.setPen(QColor('#f4f7fb'))
''', '''                vehicle_label = vehicle.vehicle_id if vehicle.selected else vehicle.vehicle_type or vehicle.vehicle_id
                if vehicle.selected or label_vehicles:
                    draw_screen_label(top, vehicle_label, fill='#102032', border='#40627c', fg='#eef8ff')
                register_hover_target(top, vehicle_label, 'Vehicle', radius=16.0)

        self._hover_targets = hover_targets
        if self._last_pointer_pos is None or not hover_targets:
            self._hovered_target = None
        else:
            px = float(self._last_pointer_pos.x())
            py = float(self._last_pointer_pos.y())
            best = None
            best_dist = 1e9
            for item in hover_targets:
                point = item['point']
                dx = float(point.x()) - px
                dy = float(point.y()) - py
                dist = hypot(dx, dy)
                if dist <= float(item.get('radius', 16.0)) and dist < best_dist:
                    best = item
                    best_dist = dist
            self._hovered_target = best
        if self._hovered_target is not None:
            point = self._hovered_target['point']
            radius = float(self._hovered_target.get('radius', 16.0)) + 4.0
            halo_fill = QColor('#7dd3fc')
            halo_fill.setAlpha(34)
            painter.setBrush(halo_fill)
            painter.setPen(QPen(QColor('#7dd3fc'), 1.8))
            painter.drawEllipse(point, radius, radius)
            draw_screen_label(point, f"{self._hovered_target['kind']}: {self._hovered_target['label']}", fill='#0d1720', border='#7dd3fc', fg='#eef8ff')

        painter.setPen(QColor('#f4f7fb'))
''', 'vehicle hover and tooltip block')

scene = replace_once(scene, '''        self.export_snapshot_button = QLabel('<a href="#">Export 3D Snapshot</a>')
        self.export_snapshot_button.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.export_snapshot_button.linkActivated.connect(lambda *_: self.export_snapshot_requested.emit())
        action_row.addWidget(self.export_snapshot_button)
        self.export_markdown_button = QLabel('<a href="#">Export 3D Markdown</a>')
''', '''        self.export_snapshot_button = QLabel('<a href="#">Export 3D Snapshot</a>')
        self.export_snapshot_button.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.export_snapshot_button.linkActivated.connect(lambda *_: self.export_snapshot_requested.emit())
        action_row.addWidget(self.export_snapshot_button)
        self.export_snapshot_hires_button = QLabel('<a href="#">Export Hi-Res Snapshot</a>')
        self.export_snapshot_hires_button.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.export_snapshot_hires_button.linkActivated.connect(lambda *_: self.export_snapshot_hires_requested.emit())
        action_row.addWidget(self.export_snapshot_hires_button)
        self.export_markdown_button = QLabel('<a href="#">Export 3D Markdown</a>')
''', 'hires action')

scene_path.write_text(scene, encoding='utf-8')

main_path = Path(r'D:\Codex\MTNsim\src\mtnsim\gui\main_window.py')
main = main_path.read_text(encoding='utf-8')

main = replace_once(main, '''        self.scene_3d_view.open_result_summary_requested.connect(self.open_current_result_summary_file)
        self.scene_3d_view.export_snapshot_requested.connect(self.export_current_3d_snapshot)
        self.scene_3d_view.export_markdown_requested.connect(self.export_current_3d_markdown)
''', '''        self.scene_3d_view.open_result_summary_requested.connect(self.open_current_result_summary_file)
        self.scene_3d_view.export_snapshot_requested.connect(self.export_current_3d_snapshot)
        self.scene_3d_view.export_snapshot_hires_requested.connect(self.export_current_3d_snapshot_hires)
        self.scene_3d_view.export_markdown_requested.connect(self.export_current_3d_markdown)
''', 'hires signal connect')

main = replace_once(main, '''    def export_current_3d_snapshot(self) -> None:
        frame = self.scene_3d_view.canvas.frame_data
        if frame is None:
            QMessageBox.information(self, '3D Export', 'Open a 3D scene or result before exporting a snapshot.')
            return
        base_dir = Path(self.current_result_summary.output_dir) if self.current_result_summary is not None else Path.cwd()
        stem = self.current_result_summary.run.scenario if self.current_result_summary is not None else 'scene3d'
        default_path = base_dir / f'{stem}_3d_snapshot.png'
        file_path, _ = QFileDialog.getSaveFileName(self, 'Save 3D Snapshot', str(default_path), 'PNG Files (*.png)')
        if not file_path:
            return
        output_path = self._export_current_3d_snapshot_to(Path(file_path))
        QMessageBox.information(self, '3D Export', '3D snapshot saved to:\n' + str(output_path))

    def _export_current_3d_snapshot_to(self, output_path: Path) -> Path:
        pixmap = self.scene_3d_view.canvas.grab()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pixmap.save(str(output_path), 'PNG')
        self._append_log(f'[info] Exported 3D snapshot: {output_path}')
        self.statusBar().showMessage(f'Exported 3D snapshot: {output_path.name}')
        return output_path
''', '''    def export_current_3d_snapshot(self) -> None:
        frame = self.scene_3d_view.canvas.frame_data
        if frame is None:
            QMessageBox.information(self, '3D Export', 'Open a 3D scene or result before exporting a snapshot.')
            return
        base_dir = Path(self.current_result_summary.output_dir) if self.current_result_summary is not None else Path.cwd()
        stem = self.current_result_summary.run.scenario if self.current_result_summary is not None else 'scene3d'
        default_path = base_dir / f'{stem}_3d_snapshot.png'
        file_path, _ = QFileDialog.getSaveFileName(self, 'Save 3D Snapshot', str(default_path), 'PNG Files (*.png)')
        if not file_path:
            return
        output_path = self._export_current_3d_snapshot_to(Path(file_path), scale_factor=1.0)
        QMessageBox.information(self, '3D Export', '3D snapshot saved to:\n' + str(output_path))

    def export_current_3d_snapshot_hires(self) -> None:
        frame = self.scene_3d_view.canvas.frame_data
        if frame is None:
            QMessageBox.information(self, '3D Export', 'Open a 3D scene or result before exporting a hi-res snapshot.')
            return
        base_dir = Path(self.current_result_summary.output_dir) if self.current_result_summary is not None else Path.cwd()
        stem = self.current_result_summary.run.scenario if self.current_result_summary is not None else 'scene3d'
        default_path = base_dir / f'{stem}_3d_snapshot_2x.png'
        file_path, _ = QFileDialog.getSaveFileName(self, 'Save Hi-Res 3D Snapshot', str(default_path), 'PNG Files (*.png)')
        if not file_path:
            return
        output_path = self._export_current_3d_snapshot_to(Path(file_path), scale_factor=2.0)
        QMessageBox.information(self, '3D Export', 'Hi-res 3D snapshot saved to:\n' + str(output_path))

    def _export_current_3d_snapshot_to(self, output_path: Path, scale_factor: float = 1.0) -> Path:
        pixmap = self.scene_3d_view.canvas.grab()
        image = pixmap.toImage()
        if scale_factor > 1.0:
            image = image.scaled(max(1, int(image.width() * scale_factor)), max(1, int(image.height() * scale_factor)), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(str(output_path), 'PNG')
        suffix = ' (hi-res)' if scale_factor > 1.0 else ''
        self._append_log(f'[info] Exported 3D snapshot{suffix}: {output_path}')
        self.statusBar().showMessage(f'Exported 3D snapshot{suffix}: {output_path.name}')
        return output_path
''', 'hires export methods')

main_path.write_text(main, encoding='utf-8')
