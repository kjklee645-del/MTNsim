from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import csv
import json

from mtnsim.security.paths import resolve_campaign_path, resolve_path_within_root
from mtnsim.schemas.field_campaign import CampaignQualityCheck, FieldCampaignInspectionSummary, FieldCampaignManifest


@dataclass(slots=True)
class FieldCampaignInspectionArtifacts:
    summary: FieldCampaignInspectionSummary
    output_dir: Path
    summary_file: Path
    report_file: Path


class FieldCampaignService:
    def inspect_campaign(self, campaign_file: str | Path) -> FieldCampaignInspectionArtifacts:
        manifest = FieldCampaignManifest.load(campaign_file)
        campaign_root = manifest.source_path.parent if manifest.source_path else Path.cwd()

        measurement_path = self._resolve(manifest, manifest.measurement_file, label='campaign.measurement_file')
        metadata_path = self._resolve(manifest, manifest.sensor_metadata_file, label='campaign.sensor_metadata_file')
        traffic_path = self._resolve(manifest, manifest.traffic_file, label='campaign.traffic_file') if manifest.traffic_file else None
        traffic_metadata_path = self._resolve(manifest, manifest.traffic_metadata_file, label='campaign.traffic_metadata_file') if manifest.traffic_metadata_file else None
        scene_path = self._resolve(manifest, manifest.scene_path, label='campaign.scene_path') if manifest.scene_path else None
        scene_manifest_path = self._resolve(manifest, manifest.scene_manifest_file, label='campaign.scene_manifest_file') if manifest.scene_manifest_file else None
        notes_path = self._resolve(manifest, manifest.notes_file, label='campaign.notes_file') if manifest.notes_file else None

        checks: list[CampaignQualityCheck] = []

        measurement_stats = self._inspect_measurements(measurement_path, manifest)
        metadata_stats = self._inspect_metadata(metadata_path)
        traffic_stats = self._inspect_traffic(traffic_path)
        traffic_metadata_checks = self._inspect_traffic_metadata(traffic_metadata_path, manifest)
        scene_checks = self._inspect_scene_bundle(scene_path, scene_manifest_path, manifest)

        checks.extend(measurement_stats['checks'])
        checks.extend(metadata_stats['checks'])
        checks.extend(traffic_stats['checks'])
        checks.extend(traffic_metadata_checks)
        checks.extend(scene_checks)
        checks.extend(self._check_optional_path('notes_file_exists', notes_path, expected_kind='file', severity='warning'))

        measurement_sensor_ids = measurement_stats['sensor_ids']
        metadata_sensor_ids = metadata_stats['sensor_ids']
        missing_metadata_ids = sorted(measurement_sensor_ids - metadata_sensor_ids)
        checks.append(
            CampaignQualityCheck(
                check_id='measurement_sensors_mapped_in_metadata',
                passed=not missing_metadata_ids,
                severity='error',
                message='All measurement sensor IDs should exist in sensor metadata.',
                details={'missing_sensor_ids': missing_metadata_ids},
            )
        )

        passed = all(item.passed or item.severity != 'error' for item in checks)
        summary = FieldCampaignInspectionSummary(
            campaign_id=manifest.campaign_id,
            name=manifest.name,
            passed=passed,
            measurement_row_count=measurement_stats['row_count'],
            measurement_sensor_count=len(measurement_sensor_ids),
            metadata_sensor_count=len(metadata_sensor_ids),
            traffic_row_count=traffic_stats['row_count'],
            checks=checks,
        )

        output_dir = campaign_root / 'reports'
        output_dir.mkdir(parents=True, exist_ok=True)
        summary_file = output_dir / 'campaign_inspection_summary.json'
        report_file = output_dir / 'campaign_inspection_report.md'
        summary_file.write_text(json.dumps(summary.to_dict(), indent=2), encoding='utf-8')
        report_file.write_text(
            self._build_markdown_report(
                manifest,
                summary,
                measurement_path,
                metadata_path,
                traffic_path,
                traffic_metadata_path,
                scene_path,
                scene_manifest_path,
                notes_path,
            ),
            encoding='utf-8',
        )
        return FieldCampaignInspectionArtifacts(summary=summary, output_dir=output_dir, summary_file=summary_file, report_file=report_file)

    def _inspect_measurements(self, path: Path, manifest: FieldCampaignManifest) -> dict:
        checks: list[CampaignQualityCheck] = []
        if not path.exists():
            checks.append(CampaignQualityCheck('measurement_file_exists', False, 'error', 'Measurement file must exist.', {'path': str(path)}))
            return {'row_count': 0, 'sensor_ids': set(), 'checks': checks}
        with path.open('r', encoding='utf-8', newline='') as handle:
            rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys()) if rows else []
        has_sensor = 'sensor_id' in fieldnames or 'receiver_id' in fieldnames
        has_value = 'value_db' in fieldnames
        has_time = any(column in fieldnames for column in ('time_index', 'timestamp', 'time_seconds'))
        checks.append(CampaignQualityCheck('measurement_required_columns', has_sensor and has_value and has_time, 'error', 'Measurements need sensor, time, and value columns.', {'columns': sorted(fieldnames)}))
        if manifest.time_column_preference:
            checks.append(
                CampaignQualityCheck(
                    'measurement_preferred_time_column_present',
                    manifest.time_column_preference in fieldnames,
                    'warning',
                    'Measurement file should include the preferred time column declared in the campaign manifest.',
                    {'preferred_time_column': manifest.time_column_preference, 'columns': sorted(fieldnames)},
                )
            )
        sensor_ids: set[str] = set()
        duplicate_counter: Counter[tuple[str, str]] = Counter()
        impossible_db_count = 0
        missing_sensor_count = 0
        missing_time_count = 0
        missing_value_count = 0
        for row in rows:
            sensor_id = str(row.get('sensor_id') or row.get('receiver_id') or '').strip()
            time_token = str(row.get('time_index') or row.get('timestamp') or row.get('time_seconds') or '').strip()
            value_raw = row.get('value_db')
            if not sensor_id:
                missing_sensor_count += 1
            else:
                sensor_ids.add(sensor_id)
            if not time_token:
                missing_time_count += 1
            if value_raw in (None, ''):
                missing_value_count += 1
            else:
                try:
                    value = float(value_raw)
                    if value < 0 or value > 150:
                        impossible_db_count += 1
                except ValueError:
                    impossible_db_count += 1
            if sensor_id and time_token:
                duplicate_counter[(sensor_id, time_token)] += 1
        duplicate_keys = sum(1 for count in duplicate_counter.values() if count > 1)
        checks.append(CampaignQualityCheck('measurement_rows_present', len(rows) > 0, 'error', 'Measurement file should contain at least one row.', {'row_count': len(rows)}))
        checks.append(CampaignQualityCheck('measurement_duplicate_sensor_time_keys', duplicate_keys == 0, 'error', 'Measurement file should not contain duplicate sensor/time pairs.', {'duplicate_key_count': duplicate_keys}))
        checks.append(CampaignQualityCheck('measurement_missing_sensor_ids', missing_sensor_count == 0, 'error', 'Measurement rows should include sensor identifiers.', {'missing_sensor_count': missing_sensor_count}))
        checks.append(CampaignQualityCheck('measurement_missing_time_values', missing_time_count == 0, 'error', 'Measurement rows should include time values.', {'missing_time_count': missing_time_count}))
        checks.append(CampaignQualityCheck('measurement_missing_value_db', missing_value_count == 0, 'error', 'Measurement rows should include dB values.', {'missing_value_count': missing_value_count}))
        checks.append(CampaignQualityCheck('measurement_plausible_db_range', impossible_db_count == 0, 'warning', 'Measurement dB values should stay in a plausible range.', {'impossible_db_count': impossible_db_count}))
        return {'row_count': len(rows), 'sensor_ids': sensor_ids, 'checks': checks}

    def _inspect_metadata(self, path: Path) -> dict:
        checks: list[CampaignQualityCheck] = []
        if not path.exists():
            checks.append(CampaignQualityCheck('sensor_metadata_file_exists', False, 'error', 'Sensor metadata file must exist.', {'path': str(path)}))
            return {'row_count': 0, 'sensor_ids': set(), 'checks': checks}
        with path.open('r', encoding='utf-8', newline='') as handle:
            rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys()) if rows else []
        sensor_ids: set[str] = set()
        duplicate_sensor_ids = 0
        missing_mapping_count = 0
        seen: set[str] = set()
        has_mapping_columns = 'simulation_receiver_id' in fieldnames or {'x', 'y', 'z'}.issubset(set(fieldnames))
        checks.append(CampaignQualityCheck('metadata_required_columns', 'sensor_id' in fieldnames and has_mapping_columns, 'error', 'Metadata should include sensor_id and either simulation_receiver_id or x/y/z coordinates.', {'columns': sorted(fieldnames)}))
        for row in rows:
            sensor_id = str(row.get('sensor_id') or '').strip()
            if not sensor_id:
                continue
            if sensor_id in seen:
                duplicate_sensor_ids += 1
            seen.add(sensor_id)
            sensor_ids.add(sensor_id)
            has_receiver_mapping = bool(str(row.get('simulation_receiver_id') or '').strip())
            has_xyz = all(str(row.get(axis) or '').strip() for axis in ('x', 'y', 'z'))
            if not has_receiver_mapping and not has_xyz:
                missing_mapping_count += 1
        checks.append(CampaignQualityCheck('metadata_rows_present', len(rows) > 0, 'error', 'Sensor metadata should contain at least one row.', {'row_count': len(rows)}))
        checks.append(CampaignQualityCheck('metadata_duplicate_sensor_ids', duplicate_sensor_ids == 0, 'error', 'Sensor metadata should not contain duplicate sensor IDs.', {'duplicate_sensor_id_count': duplicate_sensor_ids}))
        checks.append(CampaignQualityCheck('metadata_mapping_available', missing_mapping_count == 0, 'error', 'Each metadata row should map to a receiver or coordinates.', {'missing_mapping_count': missing_mapping_count}))
        return {'row_count': len(rows), 'sensor_ids': sensor_ids, 'checks': checks}

    def _inspect_traffic(self, path: Path | None) -> dict:
        checks: list[CampaignQualityCheck] = []
        if path is None:
            checks.append(CampaignQualityCheck('traffic_file_declared', False, 'warning', 'Traffic file is not declared in the campaign manifest.', {}))
            return {'row_count': None, 'checks': checks}
        if not path.exists():
            checks.append(CampaignQualityCheck('traffic_file_exists', False, 'warning', 'Traffic file path was declared but does not exist.', {'path': str(path)}))
            return {'row_count': None, 'checks': checks}
        with path.open('r', encoding='utf-8', newline='') as handle:
            rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys()) if rows else []
        has_time = any(column in fieldnames for column in ('time_index', 'timestamp', 'time_seconds', 'interval_start'))
        has_flow = any(column in fieldnames for column in ('traffic_volume', 'vehicle_count', 'flow_veh_per_hour'))
        has_speed = any(column in fieldnames for column in ('average_speed_kmh', 'speed_kmh', 'mean_speed_kmh'))
        has_heavy_share = 'heavy_vehicle_share' in fieldnames or 'heavy_vehicle_fraction' in fieldnames
        checks.append(CampaignQualityCheck('traffic_rows_present', len(rows) > 0, 'warning', 'Traffic file should contain at least one row.', {'row_count': len(rows)}))
        checks.append(CampaignQualityCheck('traffic_minimum_columns', has_time and has_flow and has_speed, 'warning', 'Traffic file should include time, flow, and speed information.', {'columns': sorted(fieldnames)}))
        checks.append(CampaignQualityCheck('traffic_heavy_vehicle_share_column', has_heavy_share, 'warning', 'Traffic file should include heavy-vehicle share if available.', {'columns': sorted(fieldnames)}))
        return {'row_count': len(rows), 'checks': checks}

    def _inspect_traffic_metadata(self, path: Path | None, manifest: FieldCampaignManifest) -> list[CampaignQualityCheck]:
        if path is None:
            return [CampaignQualityCheck('traffic_metadata_file_declared', False, 'warning', 'Traffic metadata file is not declared in the campaign manifest.', {})]
        if not path.exists():
            return [CampaignQualityCheck('traffic_metadata_file_exists', False, 'warning', 'Traffic metadata file path was declared but does not exist.', {'path': str(path)})]
        payload = json.loads(path.read_text(encoding='utf-8'))
        checks: list[CampaignQualityCheck] = []
        checks.append(CampaignQualityCheck('traffic_metadata_required_fields', all(key in payload for key in ('time_zone', 'time_column', 'speed_unit')), 'warning', 'Traffic metadata should include time_zone, time_column, and speed_unit.', {'keys': sorted(payload.keys())}))
        if manifest.expected_time_zone:
            checks.append(CampaignQualityCheck('traffic_metadata_expected_time_zone', payload.get('time_zone') == manifest.expected_time_zone, 'warning', 'Traffic metadata time zone should match the campaign manifest.', {'expected_time_zone': manifest.expected_time_zone, 'actual_time_zone': payload.get('time_zone')}))
        return checks

    def _inspect_scene_bundle(self, scene_path: Path | None, scene_manifest_path: Path | None, manifest: FieldCampaignManifest) -> list[CampaignQualityCheck]:
        checks: list[CampaignQualityCheck] = []
        checks.extend(self._check_optional_path('scene_path_exists', scene_path, expected_kind='dir', severity='warning'))
        if scene_manifest_path is None:
            checks.append(CampaignQualityCheck('scene_manifest_file_declared', False, 'warning', 'Scene manifest file is not declared in the campaign manifest.', {}))
            return checks
        if not scene_manifest_path.exists():
            checks.append(CampaignQualityCheck('scene_manifest_file_exists', False, 'warning', 'Scene manifest file path was declared but does not exist.', {'path': str(scene_manifest_path)}))
            return checks
        payload = json.loads(scene_manifest_path.read_text(encoding='utf-8'))
        checks.append(CampaignQualityCheck('scene_manifest_required_fields', all(key in payload for key in ('coordinate_system', 'layers')), 'warning', 'Scene manifest should include coordinate_system and layers.', {'keys': sorted(payload.keys())}))
        if manifest.coordinate_system:
            checks.append(CampaignQualityCheck('scene_manifest_coordinate_system_match', payload.get('coordinate_system') == manifest.coordinate_system, 'warning', 'Scene manifest coordinate system should match the campaign manifest.', {'expected_coordinate_system': manifest.coordinate_system, 'actual_coordinate_system': payload.get('coordinate_system')}))
        layers = payload.get('layers') or {}
        checks.append(CampaignQualityCheck('scene_manifest_has_relevant_layer', any(key in layers for key in ('buildings', 'barriers', 'terrain', 'ground_surfaces', 'vegetation')), 'warning', 'Scene manifest should reference at least one relevant scene layer.', {'layer_keys': sorted(layers.keys()) if isinstance(layers, dict) else []}))
        if isinstance(layers, dict) and scene_path is not None:
            missing_files: list[str] = []
            for value in layers.values():
                if not value:
                    continue
                target = resolve_path_within_root(
                    scene_path,
                    value,
                    label='campaign scene layer file',
                    must_exist=False,
                    expected_kind='file',
                )
                if not target.exists():
                    missing_files.append(str(target))
            checks.append(CampaignQualityCheck('scene_manifest_layer_files_exist', not missing_files, 'warning', 'Scene manifest referenced files should exist inside or relative to the scene bundle.', {'missing_files': missing_files}))
        return checks

    def _check_optional_path(self, check_id: str, path: Path | None, expected_kind: str, severity: str) -> list[CampaignQualityCheck]:
        if path is None:
            return [CampaignQualityCheck(check_id, False, severity, f'{check_id} is not declared in the campaign manifest.', {})]
        exists = path.is_dir() if expected_kind == 'dir' else path.is_file()
        return [CampaignQualityCheck(check_id, exists, severity, f'{check_id} should point to an existing {expected_kind}.', {'path': str(path)})]

    def _resolve(self, manifest: FieldCampaignManifest, raw_path: str | Path, *, label: str) -> Path:
        resolved = resolve_campaign_path(manifest, raw_path, label=label, must_exist=False)
        assert resolved is not None
        return resolved

    def _build_markdown_report(
        self,
        manifest: FieldCampaignManifest,
        summary: FieldCampaignInspectionSummary,
        measurement_path: Path,
        metadata_path: Path,
        traffic_path: Path | None,
        traffic_metadata_path: Path | None,
        scene_path: Path | None,
        scene_manifest_path: Path | None,
        notes_path: Path | None,
    ) -> str:
        lines = [
            f'# Field Campaign Inspection Report: {manifest.name}',
            '',
            f'- Campaign ID: `{manifest.campaign_id}`',
            f'- Overall status: `{summary.passed}`',
            f'- Measurement file: `{measurement_path}`',
            f'- Sensor metadata file: `{metadata_path}`',
            f'- Traffic file: `{traffic_path}`' if traffic_path else '- Traffic file: not declared',
            f'- Traffic metadata file: `{traffic_metadata_path}`' if traffic_metadata_path else '- Traffic metadata file: not declared',
            f'- Scene path: `{scene_path}`' if scene_path else '- Scene path: not declared',
            f'- Scene manifest file: `{scene_manifest_path}`' if scene_manifest_path else '- Scene manifest file: not declared',
            f'- Notes file: `{notes_path}`' if notes_path else '- Notes file: not declared',
            '',
            '## Summary',
            '',
            f'- Measurement row count: `{summary.measurement_row_count}`',
            f'- Measurement sensor count: `{summary.measurement_sensor_count}`',
            f'- Metadata sensor count: `{summary.metadata_sensor_count}`',
            f'- Traffic row count: `{summary.traffic_row_count}`',
            f'- Expected time zone: `{manifest.expected_time_zone}`',
            f'- Coordinate system: `{manifest.coordinate_system}`',
            '',
            '## Checks',
            '',
        ]
        for check in summary.checks:
            lines.append(f"- [{'x' if check.passed else ' '}] `{check.check_id}` ({check.severity}): {check.message}")
            if check.details:
                lines.append(f"  details: `{json.dumps(check.details, ensure_ascii=True)}`")
        lines.extend(['', '## Next Action', ''])
        if summary.passed:
            lines.append('- Campaign package passes the current structural checks and is ready for simulation-side validation work.')
        else:
            lines.append('- Fix failed `error` checks before treating this campaign as validation-grade data.')
        lines.append('')
        return '\n'.join(lines)
