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

## 3. GUI Prototype

Launch the current GUI shell:

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --gui
```

Current GUI scope in Phase 3 + playback + comparison + limited editor:
- open an existing project manifest
- create a new empty MTNsim project shell
- create a new MTNsim project from a SUMO `.sumocfg` file
- import an existing SUMO case into a new MTNsim project folder
- attach SUMO later to an already created empty project
- use the Project Home recent-run panel to reopen recent result summaries or jump to the latest output folder
- review project readiness/status hints on Project Home before running
- use the Run Monitor completion summary and direct Result Viewer shortcut after a run
- browse discovered scenarios
- inspect read-only scenario details
- run the selected scenario in the background
- watch run progress in a run-monitor view
- inspect a 2D scene view with road geometry, receivers, and scenario objects
- inspect output paths after completion
- compare two scenario configurations in a dedicated comparison view and export comparison summaries as JSON or Markdown
- run two scenarios from the comparison view and inspect receiver delta tables plus overlay charts
- open a field campaign package, inspect campaign quality, validate it from the Campaign Validation view, and open generated summary/report/result files directly
- edit selected high-value scenario parameters, including lane-change, noise/grid settings, and a multi-row receiver table, preview valid unsaved changes live in the scene/details view, then save a derived scenario from the Scenario Editor view
- jump directly into config comparison between the source and saved derived scenario
- block invalid saves with editor-side validation checks before writing a new TOML file
- browse recent result summaries and open/export the current result summary artifacts
- inspect receiver summary statistics and receiver time-series
- replay recorded vehicle movement with a time slider and play/pause controls
- zoom with the mouse wheel, pan by dragging, and inspect receivers/vehicles/lanes/grid cells with hover info
- view a minimap inset, speed-colored vehicles, short vehicle tail trails, a playback-synchronized grid heatmap overlay, playback-side layer/range/opacity controls, a receiver-series cursor that follows playback time, nearby-frame heatmap prefetch, click-to-select vehicle details, selected-vehicle contribution-only heatmap / receiver summaries, timeline event markers for vehicle enter/exit, speed shifts, and heading shifts, camera follow mode for a selected vehicle, and export the current playback as a PNG frame sequence, animated GIF, or MP4 video


### 3.1 Create or Import a Project

From `Project Home` or the main toolbar you can now use:
- `New Project`
- `Import SUMO Project`
- `Attach SUMO To Project`

Current first-pass behavior:
- choose a project folder
- optionally leave `Attach SUMO now` off to create an empty project shell
- or choose a SUMO `.sumocfg` and inspect detected network, route, additional files, route IDs, and vehicle types
- review a pre-creation validation summary including target manifest/scenario paths
- choose whether existing manifest/scenario files may be overwritten
- generate a new `project.toml`
- generate a starter `scenarios/baseline.toml`
- auto-open the new project in the GUI and show a first-run guidance note

Current behavior:
- empty projects open in Scene/Editor mode with `Run` disabled
- use `Attach SUMO To Project` later to make the project runnable without manually editing `project.toml`
- optionally attach a scene file, measurements file, and measurement metadata file during new/import/attach flows
- in attach mode you can now choose whether to refresh only the selected scenario or all scenarios, and whether traffic metadata, vehicle coefficients, placeholder receivers, and lane-change targets should be updated automatically

## 4. Important Input Files

Default project manifest:
- `examples/project.toml`

Main example scenarios:
- `examples/scenarios/baseline.toml`
- `examples/scenarios/speed_drop_80.toml`
- `examples/scenarios/lane_change_enforce.toml`
- `examples/scenarios/barrier_shielding.toml`
- `examples/scenarios/building_shielding_default.toml`
- `examples/scenarios/building_shielding.toml`
- `examples/scenarios/terrain_ground_vegetation.toml`
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

## 5. Basic Commands

### 5.1 Print Default Summary

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main
```

What it does:
- loads `examples/project.toml`
- loads `examples/scenarios/baseline.toml`
- prints run summary only

### 5.2 Print Summary For A Specific Scenario

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --scenario 'D:\Codex\MTNsim\examples\scenarios\building_shielding.toml'
```

### 5.3 Run A Simulation

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --run --cpu
```

Notes:
- `--cpu` is still useful for explicit reference runs.
- a scene-aware hybrid GPU path now exists, but full tensorized scene-aware GPU correction is not implemented yet.

Typical outputs:
- `outputs/<run_id>/run_manifest.json`
- `outputs/<run_id>/run_result_summary.json`
- `outputs/<run_id>/poi_*.csv`
- `outputs/<run_id>/grid_final_snapshot.json`

Performance note:
- the default project stores a final grid snapshot, not a full grid time series, so the grid is only computed on the last step by default.
- if you explicitly turn `store_grid_timeseries` back on, scene-aware CPU runs will become heavier again.

## 6. Scenario Comparison

### 6.1 Compare Configuration Only

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --scenario 'D:\Codex\MTNsim\examples\scenarios\baseline.toml' --compare-scenario 'D:\Codex\MTNsim\examples\scenarios\speed_drop_80.toml'
```

What it returns:
- changed fields between the two scenario files
- no simulation is executed

### 6.2 Compare Actual Run Results

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
- checks campaign-level thresholds including coverage, outlier rejection, and effective time-offset limits
- writes `campaign_validation_summary.json` and `campaign_validation_report.md` into the campaign `reports/` folder

Recommended campaign validation thresholds:
- `min_coverage_ratio`
- `min_receiver_coverage_ratio`
- `max_overall_rmse_db`
- `max_receiver_rmse_db`
- `max_worst_receiver_rmse_db`
- `max_outlier_rejection_ratio`
- `max_abs_effective_time_offset_steps`

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


## Calibration Recommendations

Calibration summaries now include structured recommendation fields:
- `recommended_global_offset_db`
- `suggested_sensor_time_offset_updates`
- `suggested_receiver_offset_db`
- `high_priority_receiver_ids`
- `recommendations`

These are intended as review candidates, not automatic truth. Use them to decide whether to apply a global level offset, adjust sensor clock alignment, or inspect geometry/traffic assumptions at specific receivers.
Campaign validation reports now surface the same recommendation set directly, so campaign review can be done without opening `calibration_summary.json` separately. Campaign reports also include an acceptance decision, comparison insights, and recommended next actions.

## Field Campaign Comparison

You can compare two field campaign packages end-to-end. This runs validation for both campaigns and writes a comparison summary plus a markdown report.

Example:
```powershell
$env:PYTHONPATH='D:\Codex\MTNsim\src'
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --compare-field-campaigns --campaign-file 'D:\Codex\MTNsim\data\field\demo_seeded_campaign\campaign.json' --compare-campaign-file 'D:\Codex\MTNsim\data\field\demo_speed_drop_campaign\campaign.json' --cpu
```

## Receiver Group Diagnostics

Field campaign manifests may declare `receiver_groups` such as `near_field`, `far_field`, `shielded`, or `unshielded`.
Campaign validation will then report group-level coverage, bias, MAE, and RMSE, and can enforce group-level acceptance thresholds through:
- `validation_thresholds.max_receiver_group_rmse_db`
- `validation_thresholds.max_receiver_group_abs_mean_bias_db`
- `validation_thresholds.min_receiver_group_coverage_ratio`

## Toolbar Layout

The top toolbar is now organized as menus:
- `Project`
- `Run`
- `Results`
- `Validation`
- `Help`

A single quick action, `Run Selected`, remains on the right side of the toolbar for the most common operation.

## Workspace Navigation

The left dock now acts as a workspace switcher rather than an action toolbar.
- `Home`
- `Scene`
- `Editor`
- `Compare`
- `Validation`
- `Run Monitor`
- `Results`
- `Playback`

Project creation/import/attach actions live in the top toolbar menus, while Project Home focuses on status, recent work, and next-step shortcuts.
