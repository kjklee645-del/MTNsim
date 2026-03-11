# MTNsim Current Status

Date: 2026-03-11

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
- uses a fixed project random seed for repeatable Python-side vehicle deployment and SUMO execution
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
- `terrain_edges`
- `buildings`
- `ground_surfaces`
- `vegetation_zones`

Runtime hierarchy:
- `SceneModel`
- `SceneObject`
- `LinearSceneObject`
- `PolygonSceneObject`
- `NoiseBarrierObject`
- `TerrainEdgeObject`
- `BuildingObject`
- `GroundSurfaceObject`
- `VegetationZoneObject`
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
- a `terrain_edge` is represented as a terrain berm or cut edge using the same line-segment shielding path
- a `building` is represented as a footprint polygon, height, attenuation, and material tag
- a `ground_surface` is represented as a polygon that contributes path-based ground-effect correction
- a `vegetation_zone` is represented as a polygon that contributes path-based vegetation attenuation
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
- runs synthetic propagation reference cases for reflection, diffraction, and total propagation correction
- checks supported cases against expected numeric ranges or expected no-context behavior
- verifies comparison relations such as absorptive < concrete reflection, glass > concrete reflection, oblique < mid-angle reflection, taller barrier < moderate barrier diffraction, and absorptive total barrier correction < moderate total barrier correction

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

### 2.9 Validation Suite Workflow

### 2.10 Field Campaign Inspection Workflow

Implemented:
- `schemas/field_campaign.py`
- `services/field_campaign_service.py`
- `data/field/demo_seeded_campaign/campaign.json`
- `data/field/template_campaign/campaign.json`
- CLI field-campaign inspection entry in `app/main.py`

What it does now:
- loads a field-campaign manifest
- checks measurement CSV, sensor metadata CSV, traffic CSV, traffic metadata JSON, scene path, scene manifest, and notes file
- verifies required columns, row counts, duplicate sensor/time keys, plausible dB ranges, metadata mapping coverage, time-zone consistency, coordinate-system consistency, and referenced scene-layer files
- writes JSON and Markdown inspection reports into the campaign `reports/` folder


Implemented:
- `benchmarks/validation_suite.json`
- `schemas/validation.py`
- `services/validation_service.py`
- `scripts/generate_reference_measurements.py`
- CLI validation entry in `app/main.py`

What it does now:
- runs repeatable scenario + measurement validation cases from one suite file
- executes simulation, calibration, and threshold checks together
- records pass/fail for aligned samples, RMSE, bias, unmatched sensors, outlier rejection, and expected auto time offsets
- now covers baseline reference data, shifted/outlier calibration recovery, speed-drop reference data, barrier reference data, and building-default reference data
- uses seeded execution so reference cases are stable across reruns
- writes `outputs/validation_suite_summary.json`


Implemented:
- configuration comparison between two scenarios
- result comparison between two executed runs

Current comparison outputs include:
- changed scenario fields
- receiver-level min/max/mean delta values
- aggregate mean-of-mean dB delta summary
- object-level propagation-property differences in scene definitions

### 2.11 Campaign-Aware Validation Workflow

Implemented:
- `services/campaign_validation_service.py`
- campaign validation summary writing in `io/result_store.py`
- CLI campaign validation entry in `app/main.py`

What it does now:
- loads a field-campaign manifest and inspects campaign quality first
- runs the linked scenario against the current project
- calibrates against the campaign measurement and metadata files
- evaluates campaign-level acceptance thresholds
- tracks receiver-level coverage failures, outlier rejection, and effective time-offset diagnostics
- writes JSON and Markdown campaign validation reports into the campaign `reports/` folder

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
- expanded propagation benchmark suite: reflection, diffraction, disabled-context, and total-correction material cases all pass under the current tuned defaults
- building material override comparison after geometry-coupled material correction update: average receiver mean level changed by about `-0.28 dB`, with near-field reductions up to about `-1.47 dB` and small far-field increases from reflection redistribution
- synthetic shifted-measurement calibration validation: auto time sync recovered `+2` steps for both sensors and rejected one injected outlier sample
- validation suite run: baseline reference measurement, shifted/outlier calibration recovery, speed-drop reference, barrier reference, and building-default reference cases all passed from one repeatable suite run
- field-validation preparation docs now define required datasets and methodology before real campaign data arrives
- demo field-campaign inspection run passed and produced both JSON and Markdown campaign-quality reports
- campaign import standard document now defines the contract for `traffic_metadata.json` and `scene/scene_manifest.json`
- standardized demo/template campaigns now pass traffic-metadata and scene-manifest inspection checks
- demo campaign-aware validation run passed with zero bias and zero RMSE against the seeded baseline reference package
- campaign validation now supports stronger gates for receiver coverage, worst-receiver RMSE, outlier rejection, and effective time-offset magnitude
- reduced-size terrain/ground/vegetation validation run showed an average receiver mean-level change of about `-1.60 dB`, with the strongest reduction near `poi_500_115` under the current first-pass scene-effect model
- full-size terrain/ground/vegetation run now completes after grid-update optimization and shows an average receiver mean-level change of about `-1.94 dB` versus baseline

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
- default project runs now compute the grid only on the final step unless full grid timeseries storage is explicitly requested

### 4.3 Product Limitations

- no GUI yet
- an initial calibration pipeline is now available for measurement CSV alignment and bias estimation
- no report generator yet
- campaign import standardization now exists for traffic metadata and scene manifests, but full production-grade GIS/CAD ingestion is still not implemented
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

1. expand validation from seeded reference cases toward true field datasets and stronger acceptance rules
2. deepen calibration workflow against measurements and field-facing correction tasks
3. continue scene expansion for terrain, vegetation, and richer object classes
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