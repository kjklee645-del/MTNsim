from __future__ import annotations

from pathlib import Path
import tomllib
import toml

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
    def save_scenario_variant(self, source_path: str | Path, destination_path: str | Path, updates: dict) -> Path:
        source_path = Path(source_path).resolve()
        destination_path = Path(destination_path).resolve()
        with source_path.open('rb') as handle:
            data = tomllib.load(handle)

        scenario_block = data.setdefault('scenario', {})
        traffic_block = data.setdefault('traffic', {})
        controls_block = data.setdefault('controls', {})
        noise_block = data.setdefault('noise', {})
        grid_block = data.setdefault('grid', {})

        scenario_block['name'] = updates.get('scenario_name') or scenario_block.get('name') or destination_path.stem
        scenario_block['description'] = updates.get('description', scenario_block.get('description', ''))
        traffic_block['max_vehicles'] = int(updates['traffic.max_vehicles'])
        traffic_block['start_speed_kmh'] = float(updates['traffic.start_speed_kmh'])
        traffic_block['vehicle_interval_seconds'] = float(updates['traffic.vehicle_interval_seconds'])
        controls_block['post_distance_meters'] = float(updates['controls.post_distance_meters'])
        controls_block['post_target_speed_kmh'] = float(updates['controls.post_target_speed_kmh'])
        controls_block['lane_change_mode'] = str(updates['controls.lane_change_mode'])
        controls_block['lane_change_strategy'] = str(updates['controls.lane_change_strategy'])
        controls_block['post_distance_speed_control'] = bool(updates['controls.post_distance_speed_control'])
        controls_block['lane_change_force_change'] = bool(updates['controls.lane_change_force_change'])
        noise_block['background_noise_db'] = float(updates['noise.background_noise_db'])
        noise_block['max_area_meters'] = float(updates['noise.max_area_meters'])
        noise_block['grid_size_meters'] = float(updates['noise.grid_size_meters'])
        noise_block['receiver_height_meters'] = float(updates['noise.receiver_height_meters'])
        grid_block['margin_x_start'] = float(updates['grid.margin_x_start'])
        grid_block['margin_x_end'] = float(updates['grid.margin_x_end'])
        grid_block['extra_y_extent'] = float(updates['grid.extra_y_extent'])
        data['receivers'] = [
            {
                'id': str(item['id']),
                'x': float(item['x']),
                'y': float(item['y']),
                'z': float(item['z']),
            }
            for item in updates['receivers']
        ]

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_text(toml.dumps(data), encoding='utf-8')
        return destination_path

