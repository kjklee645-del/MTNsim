from __future__ import annotations

from pathlib import Path

from mtnsim.api.project_api import ProjectAPI
from mtnsim.gui.state import GuiProjectState


class ProjectController:
    def __init__(self, project_api: ProjectAPI | None = None) -> None:
        self.project_api = project_api or ProjectAPI()

    def load_project(self, manifest_path: str | Path) -> GuiProjectState:
        manifest_path = Path(manifest_path).resolve()
        project = self.project_api.load_manifest(manifest_path)
        scenario_paths = self.discover_scenarios(manifest_path)
        selected_scenario_path = self._pick_default_scenario(project.project.default_scenario, scenario_paths)
        selected_scenario = self.project_api.load_scenario(selected_scenario_path) if selected_scenario_path else None
        return GuiProjectState(
            manifest_path=manifest_path,
            project=project,
            scenario_paths=scenario_paths,
            selected_scenario_path=selected_scenario_path,
            selected_scenario=selected_scenario,
        )

    def load_scenario(self, scenario_path: str | Path):
        return self.project_api.load_scenario(scenario_path)

    def discover_scenarios(self, manifest_path: str | Path) -> list[Path]:
        manifest_path = Path(manifest_path).resolve()
        candidates = [
            manifest_path.parent / 'scenarios',
            self._project_root(manifest_path) / 'examples' / 'scenarios',
        ]
        for candidate in candidates:
            if candidate.exists() and candidate.is_dir():
                return sorted(candidate.glob('*.toml'))
        return []

    def _project_root(self, manifest_path: Path) -> Path:
        if manifest_path.parent.name == 'examples':
            return manifest_path.parent.parent
        return manifest_path.parent

    def _pick_default_scenario(self, default_scenario_name: str, scenario_paths: list[Path]) -> Path | None:
        for path in scenario_paths:
            if path.stem == default_scenario_name:
                return path
        return scenario_paths[0] if scenario_paths else None
