from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(slots=True)
class ProjectInfo:
    name: str
    version: str
    default_scenario: str
    description: str = ""


@dataclass(slots=True)
class ProjectPaths:
    network: str
    route: str
    sumo_config: str
    outputs: str
    scene: str | None = None
    measurements: str | None = None


@dataclass(slots=True)
class SimulationDefaults:
    time_step_seconds: float
    max_steps: int
    random_seed: int
    engine: str


@dataclass(slots=True)
class AgentSettings:
    enabled: bool
    mode: str
    requires_approval_for: list[str]


@dataclass(slots=True)
class OutputSettings:
    store_run_manifest: bool
    store_receiver_timeseries: bool
    store_grid_timeseries: bool
    format: list[str]


@dataclass(slots=True)
class ProjectManifest:
    project: ProjectInfo
    paths: ProjectPaths
    simulation_defaults: SimulationDefaults
    agent: AgentSettings
    outputs: OutputSettings
    source_path: Path | None = None

    @classmethod
    def from_dict(cls, data: dict, source_path: str | Path | None = None) -> "ProjectManifest":
        return cls(
            project=ProjectInfo(**data["project"]),
            paths=ProjectPaths(**data["paths"]),
            simulation_defaults=SimulationDefaults(**data["simulation_defaults"]),
            agent=AgentSettings(**data["agent"]),
            outputs=OutputSettings(**data["outputs"]),
            source_path=Path(source_path) if source_path is not None else None,
        )

    @classmethod
    def load(cls, path: str | Path) -> "ProjectManifest":
        path = Path(path)
        with path.open("rb") as handle:
            data = tomllib.load(handle)
        return cls.from_dict(data, source_path=path)
