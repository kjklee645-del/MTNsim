from __future__ import annotations

import argparse
import json
from pathlib import Path

from mtnsim.app.runner import AppRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MTNsim application entry point")
    parser.add_argument("--manifest", default=None, help="Path to project manifest TOML")
    parser.add_argument("--scenario", default=None, help="Path to scenario TOML")
    parser.add_argument("--compare-scenario", default=None, help="Second scenario TOML path for comparison")
    parser.add_argument("--run", action="store_true", help="Run the simulation instead of only printing a summary")
    parser.add_argument("--calibrate", action="store_true", help="Run calibration against measurement CSV")
    parser.add_argument("--measurement", default=None, help="Measurement CSV path for calibration")
    parser.add_argument("--measurement-meta", default=None, help="Measurement sensor metadata CSV path for calibration")
    parser.add_argument("--result-summary", default=None, help="Existing run_result_summary.json path for calibration")
    parser.add_argument("--auto-time-sync", action="store_true", help="Automatically estimate per-sensor time offsets during calibration")
    parser.add_argument("--max-time-offset-steps", type=int, default=5, help="Maximum absolute time-offset search window for auto sync")
    parser.add_argument("--outlier-error-threshold-db", type=float, default=None, help="Reject calibration samples whose absolute error exceeds this dB threshold")
    parser.add_argument("--min-alignment-samples", type=int, default=3, help="Minimum overlapping samples required to accept an auto time offset")
    parser.add_argument("--cpu", action="store_true", help="Force CPU noise calculation")
    parser.add_argument("--benchmark-propagation", action="store_true", help="Run propagation benchmark cases")
    parser.add_argument("--benchmark-file", default=None, help="Propagation benchmark JSON path")
    parser.add_argument("--tune-propagation", action="store_true", help="Tune propagation parameters against benchmark cases")
    parser.add_argument("--tuning-file", default=None, help="Propagation tuning-space JSON path")
    return parser


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    parser = build_parser()
    args = parser.parse_args()

    manifest_path = Path(args.manifest) if args.manifest else root / "examples" / "project.toml"
    scenario_path = Path(args.scenario) if args.scenario else root / "examples" / "scenarios" / "baseline.toml"

    runner = AppRunner()

    if args.benchmark_propagation:
        benchmark_file = Path(args.benchmark_file) if args.benchmark_file else root / 'benchmarks' / 'propagation_reference_cases.json'
        result = runner.run_propagation_benchmarks(benchmark_file)
        print(json.dumps(result, indent=2))
        return

    if args.tune_propagation:
        benchmark_file = Path(args.benchmark_file) if args.benchmark_file else root / 'benchmarks' / 'propagation_reference_cases.json'
        tuning_file = Path(args.tuning_file) if args.tuning_file else root / 'benchmarks' / 'propagation_tuning_space.json'
        result = runner.tune_propagation(benchmark_file, tuning_file)
        print(json.dumps(result, indent=2))
        return

    if args.calibrate and args.result_summary:
        if not args.measurement:
            raise SystemExit('--measurement is required when using --calibrate with --result-summary')
        calibration = runner.calibrate_existing_result(
            Path(args.result_summary),
            Path(args.measurement),
            measurement_metadata_path=Path(args.measurement_meta) if args.measurement_meta else None,
            auto_time_sync=args.auto_time_sync,
            max_time_offset_steps=args.max_time_offset_steps,
            outlier_error_threshold_db=args.outlier_error_threshold_db,
            min_alignment_samples=args.min_alignment_samples,
        )
        print(json.dumps(calibration, indent=2))
        return

    if args.calibrate and args.run:
        calibration = runner.calibrate_project_run(
            manifest_path,
            scenario_path,
            measurement_path=args.measurement,
            measurement_metadata_path=args.measurement_meta,
            use_gpu=not args.cpu,
            auto_time_sync=args.auto_time_sync,
            max_time_offset_steps=args.max_time_offset_steps,
            outlier_error_threshold_db=args.outlier_error_threshold_db,
            min_alignment_samples=args.min_alignment_samples,
        )
        print(json.dumps(calibration, indent=2))
        return

    if args.compare_scenario and args.run:
        comparison = runner.compare_project_runs(manifest_path, scenario_path, Path(args.compare_scenario), use_gpu=not args.cpu)
        print(json.dumps(comparison, indent=2))
        return

    if args.compare_scenario:
        comparison = runner.compare_projects(manifest_path, scenario_path, Path(args.compare_scenario))
        print(json.dumps(comparison, indent=2))
        return

    if args.run:
        artifacts = runner.run_project(manifest_path, scenario_path, use_gpu=not args.cpu)
        print(
            json.dumps(
                {
                    "run_id": artifacts.run_id,
                    "output_dir": str(artifacts.output_dir),
                    "manifest_file": str(artifacts.manifest_file),
                    "result_summary_file": str(artifacts.result_summary_file),
                    "run_summary": artifacts.run_summary.to_dict(),
                    "receiver_history_files": {k: str(v) for k, v in artifacts.receiver_history_files.items()},
                    "final_grid_snapshot_file": str(artifacts.final_grid_snapshot_file) if artifacts.final_grid_snapshot_file else None,
                },
                indent=2,
            )
        )
    else:
        summary = runner.summarize_project(manifest_path, scenario_path)
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
