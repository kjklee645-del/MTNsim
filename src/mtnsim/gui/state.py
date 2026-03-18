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
class GuiRunState:
    is_running: bool = False
    progress_percent: int = 0
    progress_label: str = 'Idle'
    project_name: str | None = None
    scenario_name: str | None = None
    requested_use_gpu: bool = True
    readiness_summary: str = ''
    run_id: str | None = None
    output_dir: Path | None = None
    result_summary_file: Path | None = None
    manifest_file: Path | None = None
    final_grid_snapshot_file: Path | None = None
    vehicle_trace_file: Path | None = None
    receiver_history_files: dict[str, Path] = field(default_factory=dict)
    receiver_count: int | None = None
    used_gpu: bool | None = None
    error_message: str | None = None


@dataclass(slots=True)
class GuiSessionState:
    project_state: GuiProjectState = field(default_factory=GuiProjectState)
    run_state: GuiRunState = field(default_factory=GuiRunState)
    recent_result_summaries: list[Path] = field(default_factory=list)
    recent_log_lines: list[str] = field(default_factory=list)
