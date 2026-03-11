from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from mtnsim.schemas.project import ProjectManifest
from mtnsim.schemas.scenario import ScenarioConfig
from mtnsim.services.run_service import RunService


def resolve_project_relative(project: ProjectManifest, raw_path: str | Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    if project.source_path is None:
        return path
    source_parent = project.source_path.parent
    project_root = source_parent.parent if source_parent.name == 'examples' else source_parent
    return project_root / path


def read_receiver_history(path: str | Path) -> list[tuple[int, float]]:
    rows: list[tuple[int, float]] = []
    with Path(path).open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append((int(row['time_index']), float(row['value_db'])))
    return rows


def write_measurement_file(output_path: Path, receiver_history_files: dict[str, str]) -> int:
    sample_count = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['sensor_id', 'receiver_id', 'time_index', 'value_db'])
        writer.writeheader()
        for receiver_id, history_file in sorted(receiver_history_files.items()):
            for time_index, value_db in read_receiver_history(history_file):
                writer.writerow(
                    {
                        'sensor_id': receiver_id,
                        'receiver_id': receiver_id,
                        'time_index': time_index,
                        'value_db': value_db,
                    }
                )
                sample_count += 1
    return sample_count


def main() -> None:
    parser = argparse.ArgumentParser(description='Generate reference measurement CSV files from scenario outputs.')
    parser.add_argument('--manifest', default='examples/project.toml')
    parser.add_argument('--scenario', action='append', required=True, help='Scenario TOML path. May be provided multiple times.')
    parser.add_argument('--output-dir', default='data/measurements')
    parser.add_argument('--gpu', action='store_true', help='Use GPU if available and appropriate.')
    args = parser.parse_args()

    project = ProjectManifest.load(args.manifest)
    run_service = RunService()
    output_dir = resolve_project_relative(project, args.output_dir)

    generated: list[dict[str, object]] = []
    for raw_scenario in args.scenario:
        scenario_path = resolve_project_relative(project, raw_scenario)
        scenario = ScenarioConfig.load(scenario_path)
        context = run_service.create_run_context(project, scenario)
        artifacts = run_service.run_simulation(context, use_gpu=args.gpu)
        output_path = output_dir / f'{scenario.scenario.name}_reference_measurements.csv'
        sample_count = write_measurement_file(output_path, artifacts.result_summary.receiver_history_files)
        generated.append(
            {
                'scenario': str(scenario_path),
                'result_summary_file': str(artifacts.result_summary_file),
                'measurement_file': str(output_path),
                'sample_count': sample_count,
            }
        )

    print(json.dumps({'generated': generated}, indent=2))


if __name__ == '__main__':
    main()
