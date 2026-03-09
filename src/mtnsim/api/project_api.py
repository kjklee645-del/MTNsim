from __future__ import annotations

from pathlib import Path

from mtnsim.services.project_service import ProjectService


class ProjectAPI:
    def __init__(self, service: ProjectService | None = None) -> None:
        self.service = service or ProjectService()

    def load_manifest(self, manifest_path: str | Path):
        return self.service.load_project(manifest_path)

    def load_scenario(self, scenario_path: str | Path):
        return self.service.load_scenario(scenario_path)
