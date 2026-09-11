from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

from mtnsim.security.exceptions import ConfigValidationError
from mtnsim.security.paths import project_root_from_manifest_path, validate_path_within_root
from mtnsim.security.validators import (
    ensure_member,
    ensure_non_empty_sequence,
    ensure_non_empty_string,
    ensure_non_negative_number,
    ensure_positive_number,
)


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
    measurement_metadata: str | None = None


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
        resolved_source = Path(source_path).expanduser().resolve() if source_path is not None else None
        try:
            manifest = cls(
                project=ProjectInfo(**data["project"]),
                paths=ProjectPaths(**data["paths"]),
                simulation_defaults=SimulationDefaults(**data["simulation_defaults"]),
                agent=AgentSettings(**data["agent"]),
                outputs=OutputSettings(**data["outputs"]),
                source_path=resolved_source,
            )
        except KeyError as exc:
            raise ConfigValidationError(f"Project manifest is missing required field: {exc}") from exc
        except (TypeError, ValueError) as exc:
            raise ConfigValidationError(f"Project manifest is invalid: {exc}") from exc
        manifest.validate()
        return manifest

    def validate(self) -> None:
        ensure_non_empty_string(self.project.name, "project.name")
        ensure_non_empty_string(self.project.version, "project.version")
        ensure_non_empty_string(self.project.default_scenario, "project.default_scenario")
        ensure_positive_number(self.simulation_defaults.time_step_seconds, "simulation_defaults.time_step_seconds")
        ensure_positive_number(self.simulation_defaults.max_steps, "simulation_defaults.max_steps")
        ensure_non_negative_number(self.simulation_defaults.random_seed, "simulation_defaults.random_seed")
        ensure_member(self.simulation_defaults.engine, {"sumo"}, "simulation_defaults.engine")
        ensure_member(self.agent.mode, {"bounded"}, "agent.mode")
        ensure_non_empty_sequence(self.agent.requires_approval_for, "agent.requires_approval_for")
        ensure_non_empty_sequence(self.outputs.format, "outputs.format")
        for fmt in self.outputs.format:
            ensure_member(str(fmt), {"json", "csv"}, "outputs.format")

        if self.source_path is None:
            return

        project_root = project_root_from_manifest_path(self.source_path)
        validate_path_within_root(project_root, self.paths.outputs, label="paths.outputs")
        for label, raw_path in (
            ("paths.network", self.paths.network),
            ("paths.route", self.paths.route),
            ("paths.sumo_config", self.paths.sumo_config),
        ):
            validate_path_within_root(project_root, raw_path, label=label, allow_empty=True)
        for label, raw_path in (
            ("paths.scene", self.paths.scene),
            ("paths.measurements", self.paths.measurements),
            ("paths.measurement_metadata", self.paths.measurement_metadata),
        ):
            if raw_path is None:
                continue
            validate_path_within_root(project_root, raw_path, label=label)

    @classmethod
    def load(cls, path: str | Path) -> "ProjectManifest":
        path = Path(path).expanduser().resolve()
        try:
            with path.open("rb") as handle:
                data = tomllib.load(handle)
        except tomllib.TOMLDecodeError as exc:
            raise ConfigValidationError(f"Project manifest TOML is invalid: {path}") from exc
        return cls.from_dict(data, source_path=path)
