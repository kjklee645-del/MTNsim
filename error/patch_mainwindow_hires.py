from pathlib import Path

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f'missing snippet: {label}')
    return text.replace(old, new, 1)

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
