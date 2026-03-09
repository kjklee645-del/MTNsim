from __future__ import annotations

from dataclasses import dataclass

from mtnsim.schemas.project import ProjectManifest
from mtnsim.schemas.scenario import ScenarioConfig


@dataclass(slots=True)
class RunContext:
    project: ProjectManifest
    scenario: ScenarioConfig
    run_id: str
