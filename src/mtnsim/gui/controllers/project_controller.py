from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import tomllib
import xml.etree.ElementTree as ET

import toml

from mtnsim.api.project_api import ProjectAPI
from mtnsim.gui.state import GuiProjectState


@dataclass(slots=True)
class SumoProjectInspection:
    sumo_config_path: Path
    network_path: Path | None
    route_paths: list[Path]
    additional_paths: list[Path]
    missing_paths: list[Path]
    route_ids: list[str]
    vehicle_types: list[str]
    bounds: tuple[float, float, float, float] | None
    warnings: list[str]

    def to_summary_text(self) -> str:
        lines = [
            f'SUMO config: {self.sumo_config_path}',
            f'Network: {self.network_path if self.network_path is not None else "not found"}',
            f'Routes: {len(self.route_paths)} file(s), {len(self.route_ids)} route id(s)',
            f'Vehicle types: {", ".join(self.vehicle_types) if self.vehicle_types else "not found"}',
            f'Additional files: {len(self.additional_paths)}',
        ]
        if self.missing_paths:
            lines.append('Missing:')
            lines.extend(f'- {path}' for path in self.missing_paths)
        if self.warnings:
            lines.append('Warnings:')
            lines.extend(f'- {warning}' for warning in self.warnings)
        return '\n'.join(lines)


@dataclass(slots=True)
class ProjectCreationResult:
    manifest_path: Path
    scenario_path: Path
    inspection: SumoProjectInspection | None


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

    def inspect_sumo_project(self, sumo_config_path: str | Path) -> SumoProjectInspection:
        sumo_config_path = Path(sumo_config_path).resolve()
        if not sumo_config_path.exists():
            raise FileNotFoundError(f'SUMO config not found: {sumo_config_path}')
        root = ET.parse(sumo_config_path).getroot()
        input_node = self._resolve_sumo_input_container(root)

        warnings: list[str] = []
        if input_node is root:
            warnings.append('SUMO config stores input files at the top level without an <input> section; MTNsim will handle this layout automatically.')
        network_path = self._resolve_optional_input_path(input_node, 'net-file', sumo_config_path.parent)
        route_paths = self._resolve_input_path_list(input_node, 'route-files', sumo_config_path.parent)
        additional_paths = self._resolve_input_path_list(input_node, 'additional-files', sumo_config_path.parent)
        missing_paths: list[Path] = []
        if network_path is None:
            warnings.append('Network file is not declared in the SUMO config.')
        elif not network_path.exists():
            missing_paths.append(network_path)
        for path in [*route_paths, *additional_paths]:
            if not path.exists():
                missing_paths.append(path)
        if not route_paths:
            warnings.append('No route-files entry was found in the SUMO config.')
        route_ids, vehicle_types = self._collect_route_and_vehicle_types(route_paths, additional_paths)
        if not route_ids:
            warnings.append('No reusable route IDs were detected; starter scenario execution may not be possible.')
        if not vehicle_types:
            vehicle_types = ['DEFAULT_VEHTYPE']
            warnings.append('No vType IDs were detected; starter scenario will use DEFAULT_VEHTYPE.')
        bounds = self._read_network_bounds(network_path) if network_path is not None and network_path.exists() else None
        if bounds is None:
            warnings.append('Network bounds could not be determined; starter receivers will use a generic placeholder layout.')
        return SumoProjectInspection(
            sumo_config_path=sumo_config_path,
            network_path=network_path,
            route_paths=route_paths,
            additional_paths=additional_paths,
            missing_paths=missing_paths,
            route_ids=route_ids,
            vehicle_types=vehicle_types,
            bounds=bounds,
            warnings=warnings,
        )

    def create_project_from_sumo(
        self,
        *,
        project_root: str | Path,
        project_name: str,
        description: str,
        sumo_config_path: str | Path,
        default_scenario: str = 'baseline',
        copy_sumo_files: bool = True,
        overwrite_existing: bool = False,
        scene_path: str | Path | None = None,
        measurements_path: str | Path | None = None,
        measurement_metadata_path: str | Path | None = None,
        default_directivity_preset: str = 'custom',
        default_directivity_mode: str = 'isotropic',
        default_directivity_response_profile: str = 'physical',
        default_directivity_strength_db: float = 6.0,
        default_directivity_wedge_angle_deg: float = 70.0,
        default_directivity_vertical_strength_db: float = 0.0,
        default_directivity_vertical_angle_deg: float = 55.0,
    ) -> ProjectCreationResult:
        project_root = Path(project_root).resolve()
        inspection = self.inspect_sumo_project(sumo_config_path)
        if inspection.network_path is None:
            raise ValueError('SUMO import requires a resolvable network file.')
        if inspection.missing_paths:
            missing = '\n'.join(str(path) for path in inspection.missing_paths)
            raise FileNotFoundError(f'SUMO import is missing required files:\n{missing}')
        if not inspection.route_ids:
            raise ValueError('No route IDs were found in the imported route files, so a starter scenario cannot be generated.')

        manifest_path = project_root / 'project.toml'
        scenario_dir = project_root / 'scenarios'
        scenario_path = scenario_dir / f'{default_scenario}.toml'
        if manifest_path.exists() and not overwrite_existing:
            raise FileExistsError(f'Project manifest already exists: {manifest_path}')
        if scenario_path.exists() and not overwrite_existing:
            raise FileExistsError(f'Default scenario already exists: {scenario_path}')

        (project_root / 'data' / 'sumo').mkdir(parents=True, exist_ok=True)
        (project_root / 'data' / 'scene').mkdir(parents=True, exist_ok=True)
        (project_root / 'data' / 'measurements').mkdir(parents=True, exist_ok=True)
        scenario_dir.mkdir(parents=True, exist_ok=True)
        (project_root / 'outputs').mkdir(parents=True, exist_ok=True)

        asset_paths = self._materialize_sumo_assets(project_root, inspection, copy_sumo_files=copy_sumo_files)
        asset_paths.update(
            self._materialize_optional_project_assets(
                project_root,
                scene_path=scene_path,
                measurements_path=measurements_path,
                measurement_metadata_path=measurement_metadata_path,
                copy_external_files=copy_sumo_files,
            )
        )
        manifest_data = self._build_project_manifest_data(
            project_name=project_name,
            description=description,
            default_scenario=default_scenario,
            asset_paths=asset_paths,
        )
        scenario_data = self._build_starter_scenario_data(
            project_name=project_name,
            scenario_name=default_scenario,
            description='Starter scenario generated by the MTNsim project wizard',
            inspection=inspection,
            default_directivity_preset=default_directivity_preset,
            default_directivity_mode=default_directivity_mode,
            default_directivity_response_profile=default_directivity_response_profile,
            default_directivity_strength_db=default_directivity_strength_db,
            default_directivity_wedge_angle_deg=default_directivity_wedge_angle_deg,
            default_directivity_vertical_strength_db=default_directivity_vertical_strength_db,
            default_directivity_vertical_angle_deg=default_directivity_vertical_angle_deg,
        )

        manifest_path.write_text(toml.dumps(manifest_data), encoding='utf-8')
        scenario_path.write_text(toml.dumps(scenario_data), encoding='utf-8')
        return ProjectCreationResult(manifest_path=manifest_path, scenario_path=scenario_path, inspection=inspection)

    def import_sumo_project(self, **kwargs) -> ProjectCreationResult:
        return self.create_project_from_sumo(**kwargs)

    def attach_sumo_to_project(
        self,
        *,
        manifest_path: str | Path,
        sumo_config_path: str | Path,
        copy_sumo_files: bool = True,
        overwrite_existing: bool = True,
        scenario_path: str | Path | None = None,
        refresh_selected_scenario_only: bool = True,
        update_traffic_metadata: bool = True,
        update_vehicle_coefficients: bool = True,
        replace_placeholder_receivers: bool = True,
        update_lane_change_targets: bool = True,
        scene_path: str | Path | None = None,
        measurements_path: str | Path | None = None,
        measurement_metadata_path: str | Path | None = None,
    ) -> ProjectCreationResult:
        manifest_path = Path(manifest_path).resolve()
        if not manifest_path.exists():
            raise FileNotFoundError(f'Project manifest not found: {manifest_path}')

        project_root = self._project_root(manifest_path)
        inspection = self.inspect_sumo_project(sumo_config_path)
        if inspection.network_path is None:
            raise ValueError('SUMO attachment requires a resolvable network file.')
        if inspection.missing_paths:
            missing = '\n'.join(str(path) for path in inspection.missing_paths)
            raise FileNotFoundError(f'SUMO attachment is missing required files:\n{missing}')
        if not inspection.route_ids:
            raise ValueError('No route IDs were found in the imported route files, so the attached project cannot build a runnable starter scenario.')

        with manifest_path.open('rb') as handle:
            manifest_data = tomllib.load(handle)
        asset_paths = self._materialize_sumo_assets(project_root, inspection, copy_sumo_files=copy_sumo_files)
        asset_paths.update(
            self._materialize_optional_project_assets(
                project_root,
                scene_path=scene_path,
                measurements_path=measurements_path,
                measurement_metadata_path=measurement_metadata_path,
                copy_external_files=copy_sumo_files,
            )
        )
        manifest_paths = manifest_data.setdefault('paths', {})
        manifest_paths['network'] = asset_paths['network']
        manifest_paths['route'] = asset_paths['route']
        manifest_paths['sumo_config'] = asset_paths['sumo_config']
        if asset_paths.get('scene'):
            manifest_paths['scene'] = asset_paths['scene']
        if asset_paths.get('measurements'):
            manifest_paths['measurements'] = asset_paths['measurements']
        if asset_paths.get('measurement_metadata'):
            manifest_paths['measurement_metadata'] = asset_paths['measurement_metadata']
        manifest_path.write_text(toml.dumps(manifest_data), encoding='utf-8')

        target_scenario_path = self._resolve_attach_target_scenario_path(
            manifest_path=manifest_path,
            manifest_data=manifest_data,
            scenario_path=scenario_path,
        )
        scenario_targets = [target_scenario_path]
        if not refresh_selected_scenario_only:
            discovered = self.discover_scenarios(manifest_path)
            if discovered:
                scenario_targets = discovered
        for candidate in scenario_targets:
            self._refresh_scenario_for_attached_sumo(
                candidate,
                inspection,
                update_traffic_metadata=update_traffic_metadata,
                update_vehicle_coefficients=update_vehicle_coefficients,
                replace_placeholder_receivers=replace_placeholder_receivers,
                update_lane_change_targets=update_lane_change_targets,
            )
        return ProjectCreationResult(
            manifest_path=manifest_path,
            scenario_path=target_scenario_path,
            inspection=inspection,
        )

    def create_empty_project(
        self,
        *,
        project_root: str | Path,
        project_name: str,
        description: str,
        default_scenario: str = 'baseline',
        overwrite_existing: bool = False,
        scene_path: str | Path | None = None,
        measurements_path: str | Path | None = None,
        measurement_metadata_path: str | Path | None = None,
        copy_external_files: bool = True,
        default_directivity_preset: str = 'custom',
        default_directivity_mode: str = 'isotropic',
        default_directivity_response_profile: str = 'physical',
        default_directivity_strength_db: float = 6.0,
        default_directivity_wedge_angle_deg: float = 70.0,
        default_directivity_vertical_strength_db: float = 0.0,
        default_directivity_vertical_angle_deg: float = 55.0,
    ) -> ProjectCreationResult:
        project_root = Path(project_root).resolve()
        manifest_path = project_root / 'project.toml'
        scenario_dir = project_root / 'scenarios'
        scenario_path = scenario_dir / f'{default_scenario}.toml'
        if manifest_path.exists() and not overwrite_existing:
            raise FileExistsError(f'Project manifest already exists: {manifest_path}')
        if scenario_path.exists() and not overwrite_existing:
            raise FileExistsError(f'Default scenario already exists: {scenario_path}')

        (project_root / 'data' / 'sumo').mkdir(parents=True, exist_ok=True)
        (project_root / 'data' / 'scene').mkdir(parents=True, exist_ok=True)
        (project_root / 'data' / 'measurements').mkdir(parents=True, exist_ok=True)
        scenario_dir.mkdir(parents=True, exist_ok=True)
        (project_root / 'outputs').mkdir(parents=True, exist_ok=True)

        asset_paths = {'network': '', 'route': '', 'sumo_config': ''}
        asset_paths.update(
            self._materialize_optional_project_assets(
                project_root,
                scene_path=scene_path,
                measurements_path=measurements_path,
                measurement_metadata_path=measurement_metadata_path,
                copy_external_files=copy_external_files,
            )
        )
        manifest_data = self._build_project_manifest_data(
            project_name=project_name,
            description=description,
            default_scenario=default_scenario,
            asset_paths=asset_paths,
        )
        scenario_data = self._build_empty_starter_scenario_data(
            project_name=project_name,
            scenario_name=default_scenario,
            description='Starter scenario generated by the MTNsim project wizard (SUMO not attached yet)',
            default_directivity_preset=default_directivity_preset,
            default_directivity_mode=default_directivity_mode,
            default_directivity_response_profile=default_directivity_response_profile,
            default_directivity_strength_db=default_directivity_strength_db,
            default_directivity_wedge_angle_deg=default_directivity_wedge_angle_deg,
            default_directivity_vertical_strength_db=default_directivity_vertical_strength_db,
            default_directivity_vertical_angle_deg=default_directivity_vertical_angle_deg,
        )
        manifest_path.write_text(toml.dumps(manifest_data), encoding='utf-8')
        scenario_path.write_text(toml.dumps(scenario_data), encoding='utf-8')
        return ProjectCreationResult(manifest_path=manifest_path, scenario_path=scenario_path, inspection=None)

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
        noise_block['directivity'] = {
            'preset': str(updates.get('noise.directivity.preset', 'custom')),
            'mode': str(updates['noise.directivity.mode']),
            'response_profile': str(updates.get('noise.directivity.response_profile', 'physical')),
            'strength_db': float(updates['noise.directivity.strength_db']),
            'wedge_angle_deg': float(updates['noise.directivity.wedge_angle_deg']),
            'vertical_strength_db': float(updates['noise.directivity.vertical_strength_db']),
            'vertical_angle_deg': float(updates['noise.directivity.vertical_angle_deg']),
        }
        grid_block['margin_x_start'] = float(updates['grid.margin_x_start'])
        grid_block['margin_x_end'] = float(updates['grid.margin_x_end'])
        grid_block['extra_y_extent'] = float(updates['grid.extra_y_extent'])
        override_enabled = bool(updates.get('grid.override_enabled', False))
        grid_block['override_enabled'] = override_enabled
        if override_enabled:
            grid_block['override_min_x'] = float(updates['grid.override_min_x'])
            grid_block['override_max_x'] = float(updates['grid.override_max_x'])
            grid_block['override_min_y'] = float(updates['grid.override_min_y'])
            grid_block['override_max_y'] = float(updates['grid.override_max_y'])
        else:
            for key in ['override_min_x', 'override_max_x', 'override_min_y', 'override_max_y']:
                grid_block.pop(key, None)
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

    def save_scene_object_variant(self, source_path: str | Path, destination_path: str | Path, updates: dict) -> Path:
        source_path = Path(source_path).resolve()
        destination_path = Path(destination_path).resolve()
        with source_path.open('rb') as handle:
            data = tomllib.load(handle)

        scenario_block = data.setdefault('scenario', {})
        scenario_block['name'] = updates.get('scenario_name') or scenario_block.get('name') or destination_path.stem
        scenario_block['description'] = updates.get('description', scenario_block.get('description', ''))

        scene_block = data.setdefault('scene', {})
        scene_block.pop('barriers', None)
        scene_payload = updates.get('scene', {})
        scene_block['noise_barriers'] = list(scene_payload.get('noise_barriers', []))
        scene_block['buildings'] = list(scene_payload.get('buildings', []))
        scene_block['terrain_edges'] = list(scene_payload.get('terrain_edges', []))
        scene_block['ground_surfaces'] = list(scene_payload.get('ground_surfaces', []))
        scene_block['vegetation_zones'] = list(scene_payload.get('vegetation_zones', []))

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_text(toml.dumps(data), encoding='utf-8')
        return destination_path

    def _materialize_optional_project_assets(
        self,
        project_root: Path,
        *,
        scene_path: str | Path | None,
        measurements_path: str | Path | None,
        measurement_metadata_path: str | Path | None,
        copy_external_files: bool,
    ) -> dict[str, str]:
        assets = {
            'scene': 'data/scene/scene.geojson',
            'measurements': 'data/measurements/sensors.csv',
            'measurement_metadata': 'data/measurements/sensor_metadata.csv',
        }
        mapping = [
            ('scene', scene_path, project_root / 'data' / 'scene'),
            ('measurements', measurements_path, project_root / 'data' / 'measurements'),
            ('measurement_metadata', measurement_metadata_path, project_root / 'data' / 'measurements'),
        ]
        for key, raw_path, target_dir in mapping:
            if raw_path is None or str(raw_path).strip() == '':
                continue
            source = Path(raw_path).expanduser().resolve()
            if not source.exists():
                raise FileNotFoundError(f'Imported support file not found: {source}')
            if copy_external_files:
                target_dir.mkdir(parents=True, exist_ok=True)
                destination = target_dir / source.name
                if source != destination:
                    shutil.copy2(source, destination)
                assets[key] = str(destination.relative_to(project_root))
            else:
                assets[key] = str(source)
        return assets

    def _resolve_attach_target_scenario_path(
        self,
        *,
        manifest_path: Path,
        manifest_data: dict,
        scenario_path: str | Path | None,
    ) -> Path:
        if scenario_path is not None:
            return Path(scenario_path).resolve()
        default_scenario = manifest_data.get('project', {}).get('default_scenario', 'baseline')
        candidates = self.discover_scenarios(manifest_path)
        preferred = [path for path in candidates if path.stem == default_scenario]
        if preferred:
            return preferred[0]
        if candidates:
            return candidates[0]
        fallback = manifest_path.parent / 'scenarios' / f'{default_scenario}.toml'
        fallback.parent.mkdir(parents=True, exist_ok=True)
        if not fallback.exists():
            fallback.write_text(
                toml.dumps(
                    self._build_empty_starter_scenario_data(
                        project_name=manifest_data.get('project', {}).get('name', manifest_path.parent.name),
                        scenario_name=default_scenario,
                        description='Starter scenario created while attaching SUMO later.',
                    )
                ),
                encoding='utf-8',
            )
        return fallback.resolve()

    def _refresh_scenario_for_attached_sumo(
        self,
        scenario_path: Path,
        inspection: SumoProjectInspection,
        *,
        update_traffic_metadata: bool,
        update_vehicle_coefficients: bool,
        replace_placeholder_receivers: bool,
        update_lane_change_targets: bool,
    ) -> None:
        with scenario_path.open('rb') as handle:
            scenario_data = tomllib.load(handle)

        traffic_block = scenario_data.setdefault('traffic', {})
        noise_block = scenario_data.setdefault('noise', {})
        controls_block = scenario_data.setdefault('controls', {})
        receivers_block = scenario_data.setdefault('receivers', [])

        vehicle_types = inspection.vehicle_types or ['DEFAULT_VEHTYPE']
        if update_traffic_metadata:
            traffic_block['vehicle_types'] = vehicle_types
            traffic_block['vehicle_weights'] = [round(100 / len(vehicle_types), 2)] * len(vehicle_types)
            traffic_block['route_types'] = inspection.route_ids

        noise_block.setdefault('background_noise_db', 40.0)
        noise_block.setdefault('max_area_meters', 400.0)
        noise_block.setdefault('grid_size_meters', 5.0)
        noise_block.setdefault('receiver_height_meters', 1.5)
        if update_vehicle_coefficients:
            noise_block['vehicle_coefficients'] = {
                vehicle_type: {'a': 44.4 + (index * 3.0), 'b': 31.5}
                for index, vehicle_type in enumerate(vehicle_types)
            }

        refreshed_receivers = self._build_starter_receivers(inspection.bounds)
        if replace_placeholder_receivers and self._should_replace_placeholder_receivers(receivers_block):
            scenario_data['receivers'] = refreshed_receivers
            receivers_block = scenario_data['receivers']

        if update_lane_change_targets and receivers_block:
            first_receiver = receivers_block[0]
            controls_block['lane_change_target_positions'] = [[float(first_receiver.get('x', 100.0)), 0.0]]

        scenario_path.write_text(toml.dumps(scenario_data), encoding='utf-8')

    def _should_replace_placeholder_receivers(self, receivers_block: list[dict]) -> bool:
        if not receivers_block:
            return True
        if len(receivers_block) != 4:
            return False
        expected_ids = {'poi_1', 'poi_2', 'poi_3', 'poi_4'}
        ids = {str(item.get('id', '')) for item in receivers_block}
        if ids != expected_ids:
            return False
        for item in receivers_block:
            try:
                x_value = float(item.get('x', 0.0))
                z_value = float(item.get('z', 0.0))
            except (TypeError, ValueError):
                return False
            if abs(x_value - 100.0) > 1e-6 or abs(z_value - 1.5) > 1e-6:
                return False
        return True

    def _project_root(self, manifest_path: Path) -> Path:
        if manifest_path.parent.name == 'examples':
            return manifest_path.parent.parent
        return manifest_path.parent

    def _pick_default_scenario(self, default_scenario_name: str, scenario_paths: list[Path]) -> Path | None:
        for path in scenario_paths:
            if path.stem == default_scenario_name:
                return path
        return scenario_paths[0] if scenario_paths else None

    def _resolve_sumo_input_container(self, root: ET.Element) -> ET.Element:
        input_node = root.find('input')
        if input_node is not None:
            return input_node
        # Some SUMO configs place net-file/route-files directly under <configuration>.
        if any(root.find(tag) is not None for tag in ('net-file', 'route-files', 'additional-files')):
            return root
        raise ValueError('SUMO config does not define net-file/route-files in either an <input> section or the top-level <configuration> node.')

    def _resolve_optional_input_path(self, input_node: ET.Element, tag: str, base_dir: Path) -> Path | None:
        child = input_node.find(tag)
        raw = None if child is None else (child.attrib.get('value') or child.text)
        if raw is None or not raw.strip():
            return None
        return self._resolve_external_path(base_dir, raw.strip())

    def _resolve_input_path_list(self, input_node: ET.Element, tag: str, base_dir: Path) -> list[Path]:
        child = input_node.find(tag)
        raw = None if child is None else (child.attrib.get('value') or child.text)
        if raw is None or not raw.strip():
            return []
        return [self._resolve_external_path(base_dir, item.strip()) for item in raw.split(',') if item.strip()]

    def _resolve_external_path(self, base_dir: Path, raw_path: str) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path.resolve()
        return (base_dir / path).resolve()

    def _collect_route_and_vehicle_types(self, route_paths: list[Path], additional_paths: list[Path]) -> tuple[list[str], list[str]]:
        route_ids: list[str] = []
        vehicle_types: list[str] = []
        for path in [*route_paths, *additional_paths]:
            if not path.exists():
                continue
            try:
                root = ET.parse(path).getroot()
            except ET.ParseError:
                continue
            for node in root.iter():
                node_id = node.attrib.get('id')
                if node.tag == 'route' and node_id:
                    route_ids.append(node_id)
                if node.tag == 'vType' and node_id:
                    vehicle_types.append(node_id)
                type_id = node.attrib.get('type')
                if type_id:
                    vehicle_types.append(type_id)
        route_ids = sorted(dict.fromkeys(route_ids))
        vehicle_types = sorted(dict.fromkeys(vehicle_types))
        return route_ids, vehicle_types

    def _read_network_bounds(self, network_path: Path) -> tuple[float, float, float, float] | None:
        try:
            root = ET.parse(network_path).getroot()
        except ET.ParseError:
            return None
        location = root.find('location')
        if location is not None:
            conv = location.attrib.get('convBoundary')
            if conv:
                parts = [float(item) for item in conv.split(',')]
                if len(parts) == 4:
                    return tuple(parts)
        coords: list[tuple[float, float]] = []
        for lane in root.iter('lane'):
            shape = lane.attrib.get('shape')
            if not shape:
                continue
            for point in shape.split():
                try:
                    x_str, y_str = point.split(',')
                    coords.append((float(x_str), float(y_str)))
                except ValueError:
                    continue
        if not coords:
            return None
        xs = [point[0] for point in coords]
        ys = [point[1] for point in coords]
        return (min(xs), min(ys), max(xs), max(ys))

    def _materialize_sumo_assets(self, project_root: Path, inspection: SumoProjectInspection, *, copy_sumo_files: bool) -> dict[str, str]:
        if not copy_sumo_files:
            return {
                'sumo_config': str(inspection.sumo_config_path),
                'network': str(inspection.network_path),
                'route': str(inspection.route_paths[0]),
            }

        sumo_dir = project_root / 'data' / 'sumo'
        copied_map: dict[Path, Path] = {}
        for source in [inspection.sumo_config_path, inspection.network_path, *inspection.route_paths, *inspection.additional_paths]:
            if source is None:
                continue
            source = Path(source).resolve()
            destination = sumo_dir / source.name
            if source.resolve() != destination.resolve():
                shutil.copy2(source, destination)
            copied_map[source] = destination

        copied_config = copied_map[inspection.sumo_config_path.resolve()]
        self._rewrite_copied_sumo_config(
            copied_config,
            network_name=copied_map[inspection.network_path.resolve()].name,
            route_names=[copied_map[path.resolve()].name for path in inspection.route_paths],
            additional_names=[copied_map[path.resolve()].name for path in inspection.additional_paths],
        )
        return {
            'sumo_config': str(Path('data') / 'sumo' / copied_config.name),
            'network': str(Path('data') / 'sumo' / copied_map[inspection.network_path.resolve()].name),
            'route': str(Path('data') / 'sumo' / copied_map[inspection.route_paths[0].resolve()].name),
        }

    def _rewrite_copied_sumo_config(self, copied_config: Path, *, network_name: str, route_names: list[str], additional_names: list[str]) -> None:
        tree = ET.parse(copied_config)
        root = tree.getroot()
        input_node = self._resolve_sumo_input_container(root)
        self._set_input_text(input_node, 'net-file', network_name)
        if route_names:
            self._set_input_text(input_node, 'route-files', ','.join(route_names))
        if additional_names:
            self._set_input_text(input_node, 'additional-files', ','.join(additional_names))
        ET.indent(tree)
        tree.write(copied_config, encoding='utf-8', xml_declaration=True)

    def _set_input_text(self, input_node: ET.Element, tag: str, value: str) -> None:
        child = input_node.find(tag)
        if child is None:
            child = ET.SubElement(input_node, tag)
        child.attrib['value'] = value
        child.text = None

    def _build_project_manifest_data(self, *, project_name: str, description: str, default_scenario: str, asset_paths: dict[str, str]) -> dict:
        return {
            'project': {
                'name': project_name,
                'version': '0.1',
                'description': description or f'{project_name} project created from the MTNsim GUI',
                'default_scenario': default_scenario,
            },
            'paths': {
                'network': asset_paths['network'],
                'route': asset_paths['route'],
                'sumo_config': asset_paths['sumo_config'],
                'scene': asset_paths.get('scene', 'data/scene/scene.geojson'),
                'measurements': asset_paths.get('measurements', 'data/measurements/sensors.csv'),
                'measurement_metadata': asset_paths.get('measurement_metadata', 'data/measurements/sensor_metadata.csv'),
                'outputs': 'outputs',
            },
            'simulation_defaults': {
                'time_step_seconds': 1.0,
                'max_steps': 600,
                'random_seed': 42,
                'engine': 'sumo',
            },
            'agent': {
                'enabled': True,
                'mode': 'bounded',
                'requires_approval_for': ['run_simulation', 'overwrite_outputs', 'export_report'],
            },
            'outputs': {
                'store_run_manifest': True,
                'store_receiver_timeseries': True,
                'store_grid_timeseries': False,
                'format': ['json', 'csv'],
            },
        }

    def _build_empty_starter_scenario_data(
        self,
        *,
        project_name: str,
        scenario_name: str,
        description: str,
        default_directivity_preset: str = 'custom',
        default_directivity_mode: str = 'isotropic',
        default_directivity_response_profile: str = 'physical',
        default_directivity_strength_db: float = 6.0,
        default_directivity_wedge_angle_deg: float = 70.0,
        default_directivity_vertical_strength_db: float = 0.0,
        default_directivity_vertical_angle_deg: float = 55.0,
    ) -> dict:
        return {
            'scenario': {
                'name': scenario_name,
                'description': description,
                'project': project_name,
            },
            'traffic': {
                'max_vehicles': 100,
                'vehicle_types': ['DEFAULT_VEHTYPE'],
                'vehicle_weights': [100.0],
                'start_mode': 'interval',
                'vehicle_interval_seconds': 5.0,
                'start_speed_kmh': 80.0,
                'route_types': ['route_0'],
            },
            'controls': {
                'lane_change_mode': 'disable',
                'lane_change_ratio': 1.0,
                'lane_change_strategy': 'custom',
                'lane_change_force_change': True,
                'lane_change_check_radius_meters': 20.0,
                'lane_change_restore_time_seconds': 10.0,
                'target_lane_index': 1,
                'designated_lane': 0,
                'lane_change_target_positions': [[100.0, 0.0]],
                'post_distance_speed_control': True,
                'post_distance_meters': 300.0,
                'post_target_speed_kmh': 80.0,
            },
            'noise': {
                'background_noise_db': 40.0,
                'max_area_meters': 400.0,
                'grid_size_meters': 5.0,
                'receiver_height_meters': 1.5,
                'vehicle_coefficients': {
                    'DEFAULT_VEHTYPE': {'a': 44.4, 'b': 31.5},
                },
                'directivity': {
                    'preset': default_directivity_preset,
                    'mode': default_directivity_mode,
                    'response_profile': default_directivity_response_profile,
                    'strength_db': float(default_directivity_strength_db),
                    'wedge_angle_deg': float(default_directivity_wedge_angle_deg),
                    'vertical_strength_db': float(default_directivity_vertical_strength_db),
                    'vertical_angle_deg': float(default_directivity_vertical_angle_deg),
                },
            },
            'grid': {
                'margin_x_start': 50.0,
                'margin_x_end': 50.0,
                'extra_y_extent': 230.0,
            },
            'receivers': [
                {'id': 'poi_1', 'x': 100.0, 'y': 25.0, 'z': 1.5},
                {'id': 'poi_2', 'x': 100.0, 'y': 45.0, 'z': 1.5},
                {'id': 'poi_3', 'x': 100.0, 'y': 65.0, 'z': 1.5},
                {'id': 'poi_4', 'x': 100.0, 'y': 85.0, 'z': 1.5},
            ],
        }

    def _build_starter_scenario_data(
        self,
        *,
        project_name: str,
        scenario_name: str,
        description: str,
        inspection: SumoProjectInspection,
        default_directivity_preset: str = 'custom',
        default_directivity_mode: str = 'isotropic',
        default_directivity_response_profile: str = 'physical',
        default_directivity_strength_db: float = 6.0,
        default_directivity_wedge_angle_deg: float = 70.0,
        default_directivity_vertical_strength_db: float = 0.0,
        default_directivity_vertical_angle_deg: float = 55.0,
    ) -> dict:
        vehicle_types = inspection.vehicle_types or ['DEFAULT_VEHTYPE']
        weights = [round(100 / len(vehicle_types), 2)] * len(vehicle_types)
        receivers = self._build_starter_receivers(inspection.bounds)
        noise_height = receivers[0]['z'] if receivers else 1.5
        coefficients = {
            vehicle_type: {'a': 44.4 + (index * 3.0), 'b': 31.5}
            for index, vehicle_type in enumerate(vehicle_types)
        }
        return {
            'scenario': {
                'name': scenario_name,
                'description': description,
                'project': project_name,
            },
            'traffic': {
                'max_vehicles': 100,
                'vehicle_types': vehicle_types,
                'vehicle_weights': weights,
                'start_mode': 'interval',
                'vehicle_interval_seconds': 5.0,
                'start_speed_kmh': 80.0,
                'route_types': inspection.route_ids,
            },
            'controls': {
                'lane_change_mode': 'disable',
                'lane_change_ratio': 1.0,
                'lane_change_strategy': 'custom',
                'lane_change_force_change': True,
                'lane_change_check_radius_meters': 20.0,
                'lane_change_restore_time_seconds': 10.0,
                'target_lane_index': 1,
                'designated_lane': 0,
                'lane_change_target_positions': [[receivers[0]['x'], 0.0]] if receivers else [[100.0, 0.0]],
                'post_distance_speed_control': True,
                'post_distance_meters': 300.0,
                'post_target_speed_kmh': 80.0,
            },
            'noise': {
                'background_noise_db': 40.0,
                'max_area_meters': 400.0,
                'grid_size_meters': 5.0,
                'receiver_height_meters': noise_height,
                'vehicle_coefficients': coefficients,
                'directivity': {
                    'preset': default_directivity_preset,
                    'mode': default_directivity_mode,
                    'response_profile': default_directivity_response_profile,
                    'strength_db': float(default_directivity_strength_db),
                    'wedge_angle_deg': float(default_directivity_wedge_angle_deg),
                    'vertical_strength_db': float(default_directivity_vertical_strength_db),
                    'vertical_angle_deg': float(default_directivity_vertical_angle_deg),
                },
            },
            'grid': {
                'margin_x_start': 50.0,
                'margin_x_end': 50.0,
                'extra_y_extent': 230.0,
            },
            'receivers': receivers,
        }

    def _build_starter_receivers(self, bounds: tuple[float, float, float, float] | None) -> list[dict[str, float | str]]:
        if bounds is None:
            center_x = 500.0
            base_y = 25.0
            offsets = [0.0, 20.0, 40.0, 60.0]
            return [{'id': f'poi_{index + 1}', 'x': center_x, 'y': base_y + offset, 'z': 1.5} for index, offset in enumerate(offsets)]
        min_x, min_y, max_x, max_y = bounds
        center_x = (min_x + max_x) / 2.0
        span_y = max(max_y - min_y, 20.0)
        base_y = max_y + max(15.0, span_y * 0.4)
        spacing = max(10.0, span_y * 0.25)
        return [
            {'id': f'poi_{int(round(center_x))}_{index + 1}', 'x': round(center_x, 1), 'y': round(base_y + (index * spacing), 1), 'z': 1.5}
            for index in range(4)
        ]
