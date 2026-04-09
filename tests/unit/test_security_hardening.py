import json
import tomllib
from pathlib import Path

import pytest

from mtnsim.gui.controllers.project_controller import ProjectController
from mtnsim.scene.grid import read_network_bounds
from mtnsim.security import ConfigValidationError, PathSecurityError
from mtnsim.security.paths import resolve_project_output_root, resolve_project_path
from mtnsim.schemas.field_campaign import FieldCampaignManifest
from mtnsim.schemas.project import ProjectManifest
from mtnsim.schemas.scenario import ScenarioConfig
from mtnsim.traffic.sumo_adapter import SumoAdapter


def test_safe_xml_parsing_allows_normal_network_and_sumo_files() -> None:
    root = Path(__file__).resolve().parents[2]
    bounds = read_network_bounds(root / "tests" / "newProject" / "data" / "sumo" / "map_SS2.net.xml")
    inspection = ProjectController().inspect_sumo_project(root / "tests" / "newProject" / "data" / "sumo" / "SS2.sumocfg")

    assert len(bounds) == 4
    assert inspection.network_path is not None
    assert inspection.route_paths


def test_safe_xml_parsing_rejects_entity_expansion_payloads(tmp_path: Path) -> None:
    malicious_network = tmp_path / "malicious.net.xml"
    malicious_network.write_text(
        """<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<net>
  <location convBoundary="&xxe;"/>
</net>
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigValidationError):
        read_network_bounds(malicious_network)


def test_project_manifest_rejects_path_traversal() -> None:
    root = Path(__file__).resolve().parents[2]
    payload = tomllib.loads((root / "examples" / "project.toml").read_text(encoding="utf-8"))
    payload["paths"]["outputs"] = "../escaped"

    with pytest.raises(PathSecurityError):
        ProjectManifest.from_dict(payload, source_path=root / "examples" / "project.toml")


def test_field_campaign_manifest_rejects_external_assets(tmp_path: Path) -> None:
    campaign_file = tmp_path / "campaign.json"
    campaign_file.write_text(
        json.dumps(
            {
                "campaign_id": "demo",
                "name": "Demo",
                "measurement_file": "../measurements.csv",
                "sensor_metadata_file": "sensor_metadata.csv",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(PathSecurityError):
        FieldCampaignManifest.load(campaign_file)


def test_resolve_project_path_rejects_external_scenarios() -> None:
    root = Path(__file__).resolve().parents[2]
    manifest = ProjectManifest.load(root / "examples" / "project.toml")

    resolved = resolve_project_path(manifest, "data/sumo/4lane.net.xml", label="network path", must_exist=False)
    assert resolved == (root / "data" / "sumo" / "4lane.net.xml").resolve()

    with pytest.raises(PathSecurityError):
        resolve_project_path(manifest, "../outside.toml", label="scenario path", must_exist=False)


def test_resolve_project_output_root_stays_within_project() -> None:
    root = Path(__file__).resolve().parents[2]
    manifest = ProjectManifest.load(root / "examples" / "project.toml")

    output_root = resolve_project_output_root(manifest)
    assert output_root == (root / "outputs").resolve()


def test_scenario_validation_rejects_mismatched_vehicle_weights() -> None:
    root = Path(__file__).resolve().parents[2]
    payload = tomllib.loads((root / "examples" / "scenarios" / "baseline.toml").read_text(encoding="utf-8"))
    payload["traffic"]["vehicle_weights"] = [100.0]

    with pytest.raises(ConfigValidationError):
        ScenarioConfig.from_dict(payload, source_path=root / "examples" / "scenarios" / "baseline.toml")


def test_scenario_validation_rejects_duplicate_receivers() -> None:
    root = Path(__file__).resolve().parents[2]
    payload = tomllib.loads((root / "examples" / "scenarios" / "baseline.toml").read_text(encoding="utf-8"))
    payload["receivers"][1]["id"] = payload["receivers"][0]["id"]

    with pytest.raises(ConfigValidationError):
        ScenarioConfig.from_dict(payload, source_path=root / "examples" / "scenarios" / "baseline.toml")


def test_scenario_validation_rejects_invalid_grid_override() -> None:
    root = Path(__file__).resolve().parents[2]
    payload = tomllib.loads((root / "examples" / "scenarios" / "baseline.toml").read_text(encoding="utf-8"))
    payload["grid"]["override_enabled"] = True
    payload["grid"]["override_min_x"] = 10.0
    payload["grid"]["override_max_x"] = 5.0
    payload["grid"]["override_min_y"] = 0.0
    payload["grid"]["override_max_y"] = 1.0

    with pytest.raises(ConfigValidationError):
        ScenarioConfig.from_dict(payload, source_path=root / "examples" / "scenarios" / "baseline.toml")


def test_example_campaign_packages_remain_loadable() -> None:
    root = Path(__file__).resolve().parents[2]
    seeded = FieldCampaignManifest.load(root / "data" / "field" / "demo_seeded_campaign" / "campaign.json")
    speed_drop = FieldCampaignManifest.load(root / "data" / "field" / "demo_speed_drop_campaign" / "campaign.json")

    assert seeded.measurement_file == "measurements.csv"
    assert speed_drop.scenario_file == "scenario.toml"


def test_import_flow_materializes_external_sumo_assets_even_when_copy_flag_disabled(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    result = ProjectController().create_project_from_sumo(
        project_root=tmp_path / "imported_project",
        project_name="imported",
        description="security test",
        sumo_config_path=root / "tests" / "newProject" / "data" / "sumo" / "SS2.sumocfg",
        copy_sumo_files=False,
        overwrite_existing=True,
    )

    manifest = tomllib.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert Path(manifest["paths"]["sumo_config"]).parts[:2] == ("data", "sumo")
    assert Path(manifest["paths"]["network"]).parts[:2] == ("data", "sumo")
    assert not Path(manifest["paths"]["sumo_config"]).is_absolute()


def test_sumo_adapter_rejects_missing_binary_before_traci(tmp_path: Path) -> None:
    config_file = tmp_path / "demo.sumocfg"
    config_file.write_text("<configuration><input /></configuration>", encoding="utf-8")

    with pytest.raises(ConfigValidationError):
        SumoAdapter().start(config_file, binary="missing-sumo-binary-for-tests")
