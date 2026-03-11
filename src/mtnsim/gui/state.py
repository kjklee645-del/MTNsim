from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from mtnsim.schemas.project import ProjectManifest
from mtnsim.schemas.scenario import ScenarioConfig


@dataclass(slots=True)
class GuiProjectState:
    manifest_path: Path | None = None
    project: ProjectManifest | None = None
    scenario_paths: list[Path] = field(default_factory=list)
    selected_scenario_path: Path | None = None
    selected_scenario: ScenarioConfig | None = None


@dataclass(slots=True)
class GuiSessionState:
    project_state: GuiProjectState = field(default_factory=GuiProjectState)
    recent_log_lines: list[str] = field(default_factory=list)
