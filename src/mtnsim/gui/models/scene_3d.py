from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class RoadMesh3D:
    points: list[tuple[float, float]]
    width: float
    z: float = 0.0
    color: str = '#d9dee8'


@dataclass(slots=True)
class PrismMesh3D:
    footprint: list[tuple[float, float]]
    height: float
    color: str
    edge_color: str = '#0f1722'
    label: str = ''


@dataclass(slots=True)
class LineWall3D:
    start: tuple[float, float]
    end: tuple[float, float]
    height: float
    thickness: float = 1.5
    color: str = '#ff8a3d'
    edge_color: str = '#0f1722'
    label: str = ''


@dataclass(slots=True)
class Marker3D:
    x: float
    y: float
    z: float
    color: str = '#f7fbff'
    label: str = ''


@dataclass(slots=True)
class SurfacePolygon3D:
    polygon: list[tuple[float, float]]
    z: float = 0.0
    color: str = '#2a3b4e'
    edge_color: str = '#18212d'
    label: str = ''


@dataclass(slots=True)
class GridRegion3D:
    bounds: tuple[float, float, float, float]
    z: float = 0.0
    color: str = '#4fb3ff'


@dataclass(slots=True)
class NoiseCell3D:
    x: float
    y: float
    value_db: float
    cell_size: float = 10.0


@dataclass(slots=True)
class VehicleMarker3D:
    vehicle_id: str
    x: float
    y: float
    z: float = 0.35
    speed_mps: float = 0.0
    vehicle_type: str = ''
    color: str = '#53d6ff'
    selected: bool = False


@dataclass(slots=True)
class TrailLine3D:
    points: list[tuple[float, float]]
    z: float = 0.12
    color: str = '#4db6ff'
    selected: bool = False


@dataclass(slots=True)
class Scene3DFrame:
    bounds: tuple[float, float, float, float]
    roads: list[RoadMesh3D] = field(default_factory=list)
    barriers: list[LineWall3D] = field(default_factory=list)
    terrain_edges: list[LineWall3D] = field(default_factory=list)
    buildings: list[PrismMesh3D] = field(default_factory=list)
    ground_surfaces: list[SurfacePolygon3D] = field(default_factory=list)
    vegetation_zones: list[SurfacePolygon3D] = field(default_factory=list)
    receivers: list[Marker3D] = field(default_factory=list)
    vehicles: list[VehicleMarker3D] = field(default_factory=list)
    vehicle_trails: list[TrailLine3D] = field(default_factory=list)
    noise_cells: list[NoiseCell3D] = field(default_factory=list)
    grid_region: GridRegion3D | None = None
