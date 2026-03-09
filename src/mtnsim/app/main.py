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
    parser.add_argument("--cpu", action="store_true", help="Force CPU noise calculation")
    return parser


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    parser = build_parser()
    args = parser.parse_args()

    manifest_path = Path(args.manifest) if args.manifest else root / "examples" / "project.toml"
    scenario_path = Path(args.scenario) if args.scenario else root / "examples" / "scenarios" / "baseline.toml"

    runner = AppRunner()
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
