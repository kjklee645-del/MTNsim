from __future__ import annotations

from pathlib import Path

from mtnsim.schemas.project import ProjectManifest
from mtnsim.schemas.scenario import ScenarioConfig


def load_project_manifest(path: str | Path) -> ProjectManifest:
    return ProjectManifest.load(path)


def load_scenario(path: str | Path) -> ScenarioConfig:
    return ScenarioConfig.load(path)
