# MTNsim Current Status

Date: 2026-03-10

## 1. Summary

MTNsim has moved from a single experimental prototype script toward a package-based simulation kernel with reproducible configuration, repeatable scenario execution, and early propagation-module separation.

The codebase now supports:
- project-level manifest loading
- scenario-level experiment control
- SUMO-backed microscopic execution
- receiver and grid output generation
- run/result summary artifacts
- scenario and result comparison
- first-pass shielding using roadside barriers and building footprints
- a first runtime scene-object hierarchy for clearer geometry handling
- a common propagation-property layer for scene objects, plus path-specific material-aware reflection and diffraction effects

## 2. What Has Been Implemented

### 2.1 Configuration and Package Structure

Implemented:
- `examples/project.toml`
- `examples/scenarios/*.toml`
- `schemas/project.schema.json`
- `schemas/scenario.schema.json`
- `schemas/run.schema.json`
- `schemas/result.schema.json`
- `src/mtnsim/...` package layout

Purpose:
- establish a stable input language before deeper refactoring
- keep CLI, future GUI, API, and AI-agent layers aligned to the same config model

### 2.2 SUMO Execution Kernel

Implemented:
- `traffic/sumo_adapter.py`
- `traffic/vehicle_controls.py`
- `services/run_service.py`
- `app/main.py`
- `app/runner.py`

What it does now:
- loads a project manifest and scenario
- starts a SUMO run from `data/sumo/4lane.sumocfg`
- deploys vehicles according to scenario controls
- applies lane-change and post-distance speed logic
- computes receiver and grid noise outputs
- stores run manifest and run result summary

### 2.3 Acoustic Engine Refactor

Implemented:
- `acoustics/emission/road_vehicle.py`
- `acoustics/field/noise_grid.py`
- `acoustics/propagation/distance.py`
- `acoustics/propagation/shielding.py`
- `acoustics/propagation/reflection.py`
- `acoustics/propagation/diffraction.py`
- `acoustics/propagation/correction.py`

Current state:
- distance attenuation is active
- shielding is active in a first-pass CPU implementation
- reflection and diffraction now use geometry-informed specular and knife-edge-inspired path-excess models in the active propagation path

### 2.4 Scene Generalization Work

Current scene objects:
- `noise_barriers`
- `buildings`

Runtime hierarchy:
- `SceneModel`
- `SceneObject`
- `LinearSceneObject`
- `PolygonSceneObject`
- `NoiseBarrierObject`
- `BuildingObject`
- `PropagationMaterial`

Common propagation properties now tracked on scene objects:
- `shielding_attenuation_db`
- `reflection_loss_db`
- `diffraction_loss_db`
- `absorption_coefficient`
- `allows_reflection`
- `allows_diffraction`

Behavior:
- a `noise_barrier` is represented as a single line segment with height, attenuation, and material tag
- a `building` is represented as a footprint polygon, height, attenuation, and material tag
- building footprints are decomposed into edge segments for first-pass shielding checks
- object materials now resolve through per-object-type defaults plus optional per-object propagation overrides
- `RunService` consumes the runtime `SceneModel` instead of manually expanding schema objects inline

Compatibility note:
- legacy `scene.barriers` input is still accepted and internally converted into `noise_barriers`

### 2.5 Calibration Workflow

Implemented:
- `services/calibration_service.py`
- `schemas/calibration.py`
- `schemas/calibration.schema.json`
- `io/measurements.py`
- CLI calibration entry in `app/main.py`

What it does now:
- loads measurement CSV data in `sensor_id/receiver_id,time_index|time_seconds,value_db` format
- applies optional sensor metadata for receiver mapping, manual time offset, enabled flag, and valid time window
- can automatically estimate per-sensor time offsets within a bounded search window
- can reject calibration outliers using an absolute error threshold
- aligns measurements with simulated receiver histories
- computes receiver-level and global bias, MAE, and RMSE while tracking skipped, unmatched, and rejected samples
- writes `calibration_summary.json` per calibrated run

### 2.6 Benchmark Workflow

Implemented:
- `benchmarks/propagation_reference_cases.json`
- `services/benchmark_service.py`
- CLI benchmark entry in `app/main.py`

What it does now:
- runs synthetic propagation reference cases for reflection and diffraction
- checks each case against expected numeric ranges
- verifies comparison relations such as absorptive < concrete reflection and taller barrier < moderate barrier diffraction

### 2.7 Tuned Defaults and Scenario Overrides
- Reflection and diffraction now use tuned defaults from the benchmark search.
- Scenario authors can override any model parameter with `propagation_model.reflection` and `propagation_model.diffraction`.
- Run summaries now persist the exact effective propagation settings used for reproducibility.

### 2.7 Tuning Workflow

Implemented:
- `benchmarks/propagation_tuning_space.json`
- `services/tuning_service.py`
- CLI tuning entry in `app/main.py`

What it does now:
- evaluates candidate reflection/diffraction parameter sets against benchmark cases
- scores candidates by range violations and comparison failures
- returns the best-performing parameter combination under the current benchmark suite

### 2.8 Comparison Workflow

Implemented:
- configuration comparison between two scenarios
- result comparison between two executed runs

Current comparison outputs include:
- changed scenario fields
- receiver-level min/max/mean delta values
- aggregate mean-of-mean dB delta summary
- object-level propagation-property differences in scene definitions

## 3. Validated Scenarios

Validated scenario files:
- `baseline.toml`
- `speed_drop_80.toml`
- `lane_change_enforce.toml`
- `barrier_shielding.toml`
- `building_shielding_default.toml`
- `building_shielding.toml`

Observed comparison examples:
- `baseline` vs `speed_drop_80`: average receiver mean level decreased by about `-1.60 dB`
- `baseline` vs `lane_change_enforce`: small average decrease around `-0.10 dB`
- `baseline` vs `barrier_shielding`: average receiver mean level decreased by about `-4.74 dB`
- `baseline` vs `building_shielding`: average receiver mean level decreased by about `-5.56 dB`
- `building_shielding_default` vs `building_shielding`: average receiver mean level changed by about `+0.45 dB`, with a strong near-field decrease and more visible far-field increases under the current reflection model
- `baseline` calibration against example measurement CSV + sensor metadata: overall mean bias about `-0.67 dB`, overall RMSE about `0.95 dB`
- propagation tuning benchmark: current search space found a zero-penalty candidate over 6,561 parameter combinations
- building material override comparison after geometry-coupled material correction update: average receiver mean level changed by about `-0.28 dB`, with near-field reductions up to about `-1.47 dB` and small far-field increases from reflection redistribution
- synthetic shifted-measurement calibration validation: auto time sync recovered `+2` steps for both sensors and rejected one injected outlier sample

These values are prototype-level engineering checks, not yet validated against measured field data.

## 4. Current Limitations

### 4.1 Acoustic Model Limitations

- shielding is simplified to line-of-sight crossing plus fixed attenuation
- building shielding is approximated using footprint edges only
- reflection now uses a geometry-informed specular model tied to scene-object materials
- diffraction now uses a knife-edge-inspired path-excess model on blocked paths
- common propagation properties now affect shielding, reflection, and diffraction through geometry-coupled material corrections, but they are still simplified and not yet fully validated physics-based implementations

### 4.2 Performance Limitations

- shielding-enabled runs currently fall back to CPU
- GPU is currently practical only for free-field distance-based computation

### 4.3 Product Limitations

- no GUI yet
- an initial calibration pipeline is now available for measurement CSV alignment and bias estimation
- no report generator yet
- no production-grade scene import workflow yet
- AI-agent structures exist only as an architectural baseline, not as a working user-facing capability

## 5. Why The Current Order Was Correct

The development sequence followed so far was:
1. product direction and PRD
2. manifest and scenario schema
3. package skeleton
4. execution kernel
5. run/result schema
6. scenario comparison
7. propagation split
8. first shielding implementation
9. scene-object generalization
10. runtime scene-object hierarchy cleanup
11. common propagation-property layer
12. first-pass material-aware correction wiring

This order was correct because:
- stable config had to come before larger refactoring
- execution and result reproducibility had to come before GUI or AI control
- propagation needed to be modular before scene complexity increased
- scene hierarchy needed to be clarified before material-based propagation logic is added

## 6. Recommended Next Order

1. validate and tune reflection/diffraction against measured or reference cases
2. strengthen material-aware corrections beyond the current heuristic use
3. deepen calibration workflow against measurements
4. only then deepen higher-level product layers such as reporting, GUI, and richer agent control

## 7. Practical Repository State

Repository now contains:
- source packages under `src/mtnsim`
- example manifest and scenarios under `examples`
- schema files under `schemas`
- example SUMO network under `data/sumo`
- planning and status docs under `docs` and the repository root
- a persistent progress checklist under `docs/development_checklist.md`
- propagation benchmark cases under `benchmarks`

Repository excludes from version control through `.gitignore`:
- `outputs/`
- Python cache files
- local scratch and build artifacts

## 8. Bottom Line

MTNsim is no longer just a prototype script. It is now a structured simulation kernel with a clear product direction, reproducible scenario handling, comparison capability, an initial runtime scene hierarchy, path-specific material-aware propagation behavior, and a baseline calibration loop against measurement CSV data.