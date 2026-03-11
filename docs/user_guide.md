# MTNsim User Guide

## 1. Purpose

MTNsim is a CLI-based microscopic traffic noise simulation prototype.
It currently supports:

- project/scenario-based execution
- SUMO-backed traffic simulation
- receiver/grid noise calculation
- scenario comparison
- propagation benchmark and tuning
- calibration against measurement CSV
- propagation-model override through scenario files

## 2. Environment Assumptions

Validated environment in this repository:

- workspace: `D:\Codex\MTNsim`
- Python: `C:\Users\user\miniconda3\envs\Trac\python.exe`

Recommended shell setup:

```powershell
cd D:\Codex\MTNsim
$env:PYTHONPATH='D:\Codex\MTNsim\src'
```

## 3. Important Input Files

Default project manifest:
- `examples/project.toml`

Main example scenarios:
- `examples/scenarios/baseline.toml`
- `examples/scenarios/speed_drop_80.toml`
- `examples/scenarios/lane_change_enforce.toml`
- `examples/scenarios/barrier_shielding.toml`
- `examples/scenarios/building_shielding_default.toml`
- `examples/scenarios/building_shielding.toml`
- `examples/scenarios/propagation_override_example.toml`

Reference benchmark files:
- `benchmarks/propagation_reference_cases.json`
- `benchmarks/propagation_tuning_space.json`

Measurement examples:
- `data/measurements/sensors.csv`
- `data/measurements/sensor_metadata.csv`
- `data/measurements/baseline_reference_measurements.csv`
- `data/measurements/speed_drop_80_reference_measurements.csv`
- `data/measurements/barrier_shielding_reference_measurements.csv`
- `data/measurements/building_shielding_default_reference_measurements.csv`
- `data/measurements/synthetic_shifted_outlier.csv`
- `data/measurements/synthetic_shifted_outlier_meta.csv`
- `data/field/demo_seeded_campaign/campaign.json`
- `data/field/template_campaign/campaign.json`

## 4. Basic Commands

### 4.1 Print Default Summary

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main
```

What it does:
- loads `examples/project.toml`
- loads `examples/scenarios/baseline.toml`
- prints run summary only

### 4.2 Print Summary For A Specific Scenario

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --scenario 'D:\Codex\MTNsim\examples\scenarios\building_shielding.toml'
```

### 4.3 Run A Simulation

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --run --cpu
```

Notes:
- `--cpu` is recommended when shielding/buildings are present.
- shielding-aware GPU path is not implemented yet.

Typical outputs:
- `outputs/<run_id>/run_manifest.json`
- `outputs/<run_id>/run_result_summary.json`
- `outputs/<run_id>/poi_*.csv`
- `outputs/<run_id>/grid_final_snapshot.json`

## 5. Scenario Comparison

### 5.1 Compare Configuration Only

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --scenario 'D:\Codex\MTNsim\examples\scenarios\baseline.toml' --compare-scenario 'D:\Codex\MTNsim\examples\scenarios\speed_drop_80.toml'
```

What it returns:
- changed fields between the two scenario files
- no simulation is executed

### 5.2 Compare Actual Run Results

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --scenario 'D:\Codex\MTNsim\examples\scenarios\building_shielding_default.toml' --compare-scenario 'D:\Codex\MTNsim\examples\scenarios\building_shielding.toml' --run --cpu
```

What it returns:
- two run artifact paths
- receiver-level dB deltas
- aggregate comparison summary

## 6. Propagation Benchmark And Tuning

### 6.1 Run Propagation Benchmark

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --benchmark-propagation
```

Optional benchmark file override:

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --benchmark-propagation --benchmark-file 'D:\Codex\MTNsim\benchmarks\propagation_reference_cases.json'
```

### 6.2 Run Propagation Tuning

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --tune-propagation
```

What it does:
- searches candidate reflection/diffraction parameter sets
- evaluates them against benchmark cases
- returns the best-performing setting set

## 7. Calibration Workflow

### 7.1 Run Simulation And Calibrate In One Command

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --scenario 'D:\Codex\MTNsim\examples\scenarios\baseline.toml' --run --calibrate --cpu
```

Uses default measurement paths from `examples/project.toml` unless overridden.

### 7.2 Calibrate An Existing Run Result

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --calibrate --result-summary 'D:\Codex\MTNsim\outputs\be401a48c4c54839afc453dcd0b8e6ce\run_result_summary.json' --measurement 'D:\Codex\MTNsim\data\measurements\sensors.csv' --measurement-meta 'D:\Codex\MTNsim\data\measurements\sensor_metadata.csv'
```

### 7.3 Calibration With Auto Time Sync And Outlier Rejection

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --calibrate --result-summary 'D:\Codex\MTNsim\outputs\be401a48c4c54839afc453dcd0b8e6ce\run_result_summary.json' --measurement 'D:\Codex\MTNsim\data\measurements\synthetic_shifted_outlier.csv' --measurement-meta 'D:\Codex\MTNsim\data\measurements\synthetic_shifted_outlier_meta.csv' --auto-time-sync --max-time-offset-steps 3 --outlier-error-threshold-db 10
```

Important calibration options:
- `--auto-time-sync`: estimate sensor time offsets automatically
- `--max-time-offset-steps`: search range for auto sync
- `--outlier-error-threshold-db`: reject calibration samples beyond this absolute error
- `--min-alignment-samples`: minimum overlap required to accept an estimated offset

Calibration output includes:
- `overall_mean_bias_db`
- `overall_mae_db`
- `overall_rmse_db`
- `effective_sensor_time_offsets`
- `outlier_rejected_sample_count`

## 7.4 Run Validation Suite

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --validate-suite --cpu
```

Optional validation file override:

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --validate-suite --validation-file 'D:\Codex\MTNsim\benchmarks\validation_suite.json' --cpu
```

What it does:
- runs each case in `benchmarks/validation_suite.json`
- executes simulation + calibration + threshold checks
- currently covers baseline reference data, shifted/outlier recovery, speed-drop reference data, barrier reference data, and building-default reference data
- writes a repository-level summary to `outputs/validation_suite_summary.json`

## 7.5 Generate Seeded Reference Measurements

Use the helper script when you want to refresh validation reference datasets after an intentional model update.

```powershell
$env:PYTHONPATH='D:\Codex\MTNsim\src'
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' scripts\generate_reference_measurements.py --manifest examples\project.toml --scenario examples\scenarios\baseline.toml --scenario examples\scenarios\speed_drop_80.toml --scenario examples\scenarios\barrier_shielding.toml --scenario examples\scenarios\building_shielding_default.toml
```

Notes:
- generated files are written under `data/measurements`
- seeded execution is used so reruns are reproducible
- refresh these files only when you intentionally accept a new model baseline

## 7.6 Inspect A Field Campaign Package

Use this when a real or staged field campaign folder has been assembled and you want a structural quality report before running validation.

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --inspect-field-campaign --campaign-file 'D:\Codex\MTNsim\data\field\demo_seeded_campaign\campaign.json'
```

What it does:
- loads the campaign manifest
- checks measurement, metadata, traffic, scene, and notes inputs
- validates `traffic_metadata.json` and `scene/scene_manifest.json` against the campaign contract
- reports missing files, duplicate sensor/time keys, missing mappings, and basic data-quality issues
- writes campaign reports into the campaign `reports/` folder

Useful paths:
- demo campaign: `data/field/demo_seeded_campaign/campaign.json`
- empty template: `data/field/template_campaign/campaign.json`
- import contract: `docs/campaign_import_standard.md`

## 7.7 Run Campaign-Aware Validation

Use this when a campaign package is structurally ready and you want MTNsim to run the linked scenario, calibrate against the campaign data, and write a campaign validation report.

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --validate-field-campaign --campaign-file 'D:\Codex\MTNsim\data\field\demo_seeded_campaign\campaign.json' --cpu
```

What it does:
- inspects the campaign package first
- runs the scenario referenced by the campaign manifest
- calibrates against campaign measurements
- checks campaign-level thresholds
- writes `campaign_validation_summary.json` and `campaign_validation_report.md` into the campaign `reports/` folder

## 8. Propagation Model Overrides

You can override tuned propagation defaults in a scenario file.

Example:

```toml
[propagation_model.reflection]
energy_scale = 2.8
max_gain_db = 4.0
min_normal_alignment = 0.15

[propagation_model.diffraction]
wavelength_meters = 0.68
height_penalty_scale = 0.30
height_penalty_cap_db = 1.6
min_remaining_attenuation_db = 0.5
```

Reference example:
- `examples/scenarios/propagation_override_example.toml`

Run summaries persist the effective reflection/diffraction settings under:
- `propagation_features.reflection_model_settings`
- `propagation_features.diffraction_model_settings`

## 9. Manifest And Scenario Paths

Default project manifest:
- `examples/project.toml`

You can override the manifest path:

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --manifest 'D:\Codex\MTNsim\examples\project.toml' --scenario 'D:\Codex\MTNsim\examples\scenarios\baseline.toml'
```

## 10. Output Files

Typical per-run outputs:
- `run_manifest.json`: run identity and basic summary
- `run_result_summary.json`: receiver stats, output paths, propagation feature summary
- `poi_*.csv`: receiver time series
- `grid_final_snapshot.json`: final grid values
- `calibration_summary.json`: created only when calibration is executed

## 11. Current Limitations

- no GUI yet
- shielding-aware runs currently use CPU
- terrain surfaces, vegetation, and richer 3D scene objects are not implemented yet
- propagation models are improved but still not fully field-validated
- report generation is not implemented yet
- AI-agent control is not implemented as a user-facing feature yet

## 12. Recommended Starting Workflow

For first-time use, this order is recommended:

1. Run summary for `baseline`
2. Run `baseline` on CPU
3. Compare `baseline` with `speed_drop_80`
4. Run propagation benchmark
5. Run calibration on an existing result
6. Try a scenario with `propagation_model` overrides
