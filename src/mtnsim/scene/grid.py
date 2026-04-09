from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import xml.etree.ElementTree as ET


@dataclass(slots=True)
class GridCell:
    cell_id: str
    x: float
    y: float
    z: float
    value: float


@dataclass(slots=True)
class GridDomain:
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    grid_size: float
    cells: dict[str, GridCell] = field(default_factory=dict)

    def add_cell(self, x: float, y: float, z: float, default_value: float) -> GridCell:
        cell_id = f"poi_{x}_{y}"
        cell = GridCell(cell_id=cell_id, x=x, y=y, z=z, value=default_value)
        self.cells[cell_id] = cell
        return cell

    def iter_points(self, margin_x_start: float, margin_x_end: float, extra_y_extent: float):
        x = self.min_x + margin_x_start
        while x < self.max_x - margin_x_end:
            y = self.min_y
            while y < self.max_y + extra_y_extent:
                yield x, y
                y += self.grid_size
            x += self.grid_size

    def iter_points_within_bounds(self):
        x = self.min_x
        while x < self.max_x:
            y = self.min_y
            while y < self.max_y:
                yield x, y
                y += self.grid_size
            x += self.grid_size


def read_network_bounds(network_file: str | Path) -> tuple[float, float, float, float]:
    root = ET.parse(network_file).getroot()
    location = root.find("location")
    if location is None:
        raise ValueError("Network file does not contain <location>.")
    boundary = location.get("convBoundary")
    if not boundary:
        raise ValueError("Network file does not define convBoundary.")
    min_x, min_y, max_x, max_y = map(float, boundary.split(","))
    return min_x, min_y, max_x, max_y
