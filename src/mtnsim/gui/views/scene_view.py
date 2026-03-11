from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen, QBrush
from PySide6.QtWidgets import QLabel, QSplitter, QTextEdit, QVBoxLayout, QWidget

from mtnsim.gui.controllers.scene_controller import SceneSnapshot


@dataclass(frozen=True, slots=True)
class LayerStyle:
    pen_color: str
    pen_width: int = 1
    brush_color: str | None = None


class SceneCanvas(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.snapshot: SceneSnapshot | None = None
        self.setMinimumHeight(420)

    def set_snapshot(self, snapshot: SceneSnapshot | None) -> None:
        self.snapshot = snapshot
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#f8f5ef'))
        painter.setRenderHint(QPainter.Antialiasing)

        if self.snapshot is None:
            painter.setPen(QPen(QColor('#374151'), 1))
            painter.drawText(self.rect(), Qt.AlignCenter, 'Load a project and scenario to view the scene.')
            return

        margin = 28
        plot_rect = self.rect().adjusted(margin, margin, -margin, -margin)
        min_x, min_y, max_x, max_y = self.snapshot.bounds
        span_x = max(max_x - min_x, 1.0)
        span_y = max(max_y - min_y, 1.0)

        def map_point(point: tuple[float, float]) -> tuple[float, float]:
            x_ratio = (point[0] - min_x) / span_x
            y_ratio = (point[1] - min_y) / span_y
            px = plot_rect.left() + (plot_rect.width() * x_ratio)
            py = plot_rect.bottom() - (plot_rect.height() * y_ratio)
            return px, py

        painter.setPen(QPen(QColor('#d1d5db'), 1))
        painter.drawRect(plot_rect)

        self._draw_polylines(painter, self.snapshot.road_layer.polylines, map_point, LayerStyle('#4b5563', 2))
        self._draw_polylines(painter, self.snapshot.barrier_layer.polylines, map_point, LayerStyle('#dc2626', 3))
        self._draw_polylines(painter, self.snapshot.terrain_layer.polylines, map_point, LayerStyle('#7c2d12', 3))
        self._draw_polygons(painter, self.snapshot.ground_layer.polygons, map_point, LayerStyle('#84cc16', 1, '#d9f99d'))
        self._draw_polygons(painter, self.snapshot.vegetation_layer.polygons, map_point, LayerStyle('#166534', 1, '#bbf7d0'))
        self._draw_polygons(painter, self.snapshot.building_layer.polygons, map_point, LayerStyle('#1d4ed8', 2, '#bfdbfe'))
        self._draw_points(painter, self.snapshot.receiver_layer.points, map_point, '#0f172a')

    def _draw_polylines(self, painter: QPainter, polylines, mapper, style: LayerStyle) -> None:
        painter.setPen(QPen(QColor(style.pen_color), style.pen_width))
        for polyline in polylines:
            for index in range(len(polyline) - 1):
                x1, y1 = mapper(polyline[index])
                x2, y2 = mapper(polyline[index + 1])
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))

    def _draw_polygons(self, painter: QPainter, polygons, mapper, style: LayerStyle) -> None:
        painter.setPen(QPen(QColor(style.pen_color), style.pen_width))
        painter.setBrush(QBrush(QColor(style.brush_color)) if style.brush_color else Qt.NoBrush)
        for polygon in polygons:
            if len(polygon) < 3:
                continue
            mapped = [mapper(point) for point in polygon]
            for index in range(len(mapped)):
                x1, y1 = mapped[index]
                x2, y2 = mapped[(index + 1) % len(mapped)]
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))

    def _draw_points(self, painter: QPainter, points, mapper, color: str) -> None:
        painter.setPen(QPen(QColor(color), 1))
        painter.setBrush(QBrush(QColor(color)))
        for label, x, y in points:
            px, py = mapper((x, y))
            painter.drawEllipse(int(px) - 4, int(py) - 4, 8, 8)
            painter.drawText(int(px) + 6, int(py) - 6, label)


class SceneView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel('Scene View')
        title.setStyleSheet('font-size: 22px; font-weight: 700;')
        layout.addWidget(title)

        splitter = QSplitter()
        layout.addWidget(splitter, 1)

        self.canvas = SceneCanvas()
        splitter.addWidget(self.canvas)

        self.legend_box = QTextEdit()
        self.legend_box.setReadOnly(True)
        self.legend_box.setMaximumWidth(280)
        splitter.addWidget(self.legend_box)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

    def set_snapshot(self, snapshot: SceneSnapshot | None) -> None:
        self.canvas.set_snapshot(snapshot)
        if snapshot is None:
            self.legend_box.setPlainText('No scene snapshot loaded.')
            return
        min_x, min_y, max_x, max_y = snapshot.bounds
        lines = [
            'Layers',
            '- Road network',
            '- Noise barriers',
            '- Terrain edges',
            '- Buildings',
            '- Ground surfaces',
            '- Vegetation zones',
            '- Receivers',
            '',
            'Counts',
            f'- Road polylines: {len(snapshot.road_layer.polylines)}',
            f'- Barriers: {len(snapshot.barrier_layer.polylines)}',
            f'- Terrain edges: {len(snapshot.terrain_layer.polylines)}',
            f'- Buildings: {len(snapshot.building_layer.polygons)}',
            f'- Ground surfaces: {len(snapshot.ground_layer.polygons)}',
            f'- Vegetation zones: {len(snapshot.vegetation_layer.polygons)}',
            f'- Receivers: {len(snapshot.receiver_layer.points)}',
            '',
            'Bounds',
            f'- min_x: {min_x:.1f}',
            f'- min_y: {min_y:.1f}',
            f'- max_x: {max_x:.1f}',
            f'- max_y: {max_y:.1f}',
        ]
        self.legend_box.setPlainText('\n'.join(lines))
