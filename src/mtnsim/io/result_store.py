from __future__ import annotations

from pathlib import Path
import csv
import json

from mtnsim.schemas.calibration import CalibrationSummary
from mtnsim.schemas.results import RunResultSummary
from mtnsim.schemas.run import RunSummary
from mtnsim.schemas.validation import ValidationSuiteSummary
from mtnsim.schemas.field_campaign import FieldCampaignValidationSummary


def write_receiver_history(output_dir: str | Path, receiver_id: str, values: list[float]) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    target = output_path / f"{receiver_id}.csv"
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time_index", "value_db"])
        for idx, value in enumerate(values):
            writer.writerow([idx, value])
    return target


def write_receiver_histories(output_dir: str | Path, histories: dict[str, list[float]]) -> dict[str, Path]:
    return {
        receiver_id: write_receiver_history(output_dir, receiver_id, values)
        for receiver_id, values in histories.items()
    }


def write_run_manifest(output_dir: str | Path, payload: RunSummary | dict) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    target = output_path / 'run_manifest.json'
    content = payload.to_dict() if hasattr(payload, 'to_dict') else payload
    target.write_text(json.dumps(content, indent=2), encoding='utf-8')
    return target


def write_run_result_summary(output_dir: str | Path, payload: RunResultSummary | dict) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    target = output_path / 'run_result_summary.json'
    content = payload.to_dict() if hasattr(payload, 'to_dict') else payload
    target.write_text(json.dumps(content, indent=2), encoding='utf-8')
    return target


def write_calibration_summary(output_dir: str | Path, payload: CalibrationSummary | dict) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    target = output_path / 'calibration_summary.json'
    content = payload.to_dict() if hasattr(payload, 'to_dict') else payload
    target.write_text(json.dumps(content, indent=2), encoding='utf-8')
    return target


def write_validation_suite_summary(output_dir: str | Path, payload: ValidationSuiteSummary | dict, file_name: str = 'validation_suite_summary.json') -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    target = output_path / file_name
    content = payload.to_dict() if hasattr(payload, 'to_dict') else payload
    target.write_text(json.dumps(content, indent=2), encoding='utf-8')
    return target


def write_field_campaign_validation_summary(output_dir: str | Path, payload: FieldCampaignValidationSummary | dict, file_name: str = 'campaign_validation_summary.json') -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    target = output_path / file_name
    content = payload.to_dict() if hasattr(payload, 'to_dict') else payload
    target.write_text(json.dumps(content, indent=2), encoding='utf-8')
    return target
