from pathlib import Path

from mtnsim.schemas.project import ProjectManifest
from mtnsim.schemas.scenario import ScenarioConfig


def test_project_manifest_loads() -> None:
    root = Path(__file__).resolve().parents[2]
    manifest = ProjectManifest.load(root / "examples" / "project.toml")
    assert manifest.project.name == "mtnsim-demo"
    assert manifest.agent.mode == "bounded"


def test_scenario_loads() -> None:
    root = Path(__file__).resolve().parents[2]
    scenario = ScenarioConfig.load(root / "examples" / "scenarios" / "baseline.toml")
    assert scenario.scenario.name == "baseline"
    assert len(scenario.receivers) == 8
    assert scenario.controls.lane_change_strategy == "custom"
    assert scenario.controls.lane_change_target_positions == [(500.0, 0.0)]
