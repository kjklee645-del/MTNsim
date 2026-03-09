from __future__ import annotations

from pathlib import Path

from mtnsim.io.project_store import load_project_manifest, load_scenario
from mtnsim.schemas.project import ProjectManifest
from mtnsim.schemas.scenario import ScenarioConfig


class ProjectService:
    def load_project(self, manifest_path: str | Path) -> ProjectManifest:
        return load_project_manifest(manifest_path)

    def load_scenario(self, scenario_path: str | Path) -> ScenarioConfig:
        return load_scenario(scenario_path)
