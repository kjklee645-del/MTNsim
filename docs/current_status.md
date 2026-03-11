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
- a runtime scene-object hierarchy for clearer geometry handling
- path-specific material-aware propagation effects
- scene-aware hybrid GPU execution for attenuation and accumulation
- a GUI prototype with project loading, 2D scene viewing, background run execution, progress monitoring, result viewing, and receiver-series plotting

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
- `acoustics/propagation/provider.py`

Current state:
- distance attenuation is active
- shielding is active in a first-pass scene-aware implementation
- reflection and diffraction use geometry-informed specular and knife-edge-inspired path-excess models
- scene-aware propagation now has a hybrid GPU path where the provider computes corrections and the GPU handles attenuation and power accumulation

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
- a `ground_surface` is represented as a polygon that contributes path-length-aware and line-height-aware ground-effect correction
- a `vegetation_zone` is represented as a polygon that contributes path-length-aware and line-height-aware vegetation attenuation
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
- emits structured calibration recommendations such as global offset candidates, sensor time-offset updates, and high-priority receiver review points
- writes `calibration_summary.json` per calibrated run

### 2.6 Validation and Campaign Workflow

Implemented:
- `benchmarks/propagation_reference_cases.json`
- `benchmarks/propagation_tuning_space.json`
- `benchmarks/validation_suite.json`
- `schemas/field_campaign.py`
- `services/benchmark_service.py`
- `services/tuning_service.py`
- `services/validation_service.py`
- `services/field_campaign_service.py`
- `services/campaign_validation_service.py`
- `scripts/generate_reference_measurements.py`

What it does now:
- runs synthetic propagation benchmark cases for reflection, diffraction, and total correction
- tunes reflection/diffraction defaults against the benchmark suite
- runs repeatable scenario + measurement validation cases from one suite file
- inspects field-campaign packages for measurement, metadata, traffic, and scene-manifest quality
- runs campaign-aware validation with calibration, thresholds, coverage checks, receiver-group diagnostics, structured calibration recommendations, acceptance-status classification, comparison insights, outlier diagnostics, and report generation
- compares two campaign packages and writes field-campaign comparison JSON/Markdown reports

### 2.7 GUI Phase 3 + Scene View

Implemented:
- `gui/app.py`
- `gui/main_window.py`
- `gui/state.py`
- `gui/controllers/project_controller.py`
- `gui/controllers/run_controller.py`
- `gui/controllers/result_controller.py`
- `gui/views/project_home.py`
- `gui/views/run_monitor.py`
- `gui/views/result_viewer.py`
- `gui/controllers/scene_controller.py`
- `gui/views/scene_view.py`

What it does now:
- launches a PySide6 desktop shell
- opens a project manifest
- discovers bundled scenarios
- selects the default scenario automatically
- shows basic scenario details in a read-only panel
- runs the selected scenario through a background worker
- surfaces progress updates from the simulation engine
- switches to a run-monitor view during execution
- shows output directory, manifest, result-summary path, and receiver output files after completion
- renders a 2D scene view using SUMO road polylines plus scenario geometry and receivers
- loads recent result summaries inside the GUI
- renders receiver summary statistics in a table
- renders receiver time-series in a built-in line chart

## 3. Validated Scenarios and Checks

Validated scenario files:
- `baseline.toml`
- `speed_drop_80.toml`
- `lane_change_enforce.toml`
- `barrier_shielding.toml`
- `building_shielding_default.toml`
- `building_shielding.toml`
- `terrain_ground_vegetation.toml`

Observed checks include:
- `baseline` vs `speed_drop_80`: average receiver mean level decreased by about `-1.60 dB`
- `baseline` vs `lane_change_enforce`: small average decrease around `-0.10 dB`
- `baseline` vs `barrier_shielding`: average receiver mean level decreased by about `-4.74 dB`
- `baseline` vs `building_shielding`: average receiver mean level decreased by about `-5.56 dB`
- `building_shielding_default` vs `building_shielding`: average receiver mean level changed by about `+0.45 dB` under the current reflection model
- baseline calibration against example measurement CSV + sensor metadata: overall mean bias about `-0.67 dB`, overall RMSE about `0.95 dB`
- propagation tuning benchmark: current search space found a zero-penalty candidate over 6,561 parameter combinations
- expanded propagation benchmark suite: reflection, diffraction, disabled-context, and total-correction material cases all pass under the current tuned defaults
- synthetic shifted-measurement calibration validation: auto time sync recovered `+2` steps for both sensors and rejected one injected outlier sample
- validation suite run: baseline reference, shifted/outlier recovery, speed-drop reference, barrier reference, and building-default reference cases all passed from one repeatable suite run
- demo campaign inspection run passed and produced JSON and Markdown campaign-quality reports
- demo campaign-aware validation run passed with zero bias and zero RMSE against the seeded baseline reference package
- campaign validation now supports declared receiver-group diagnostics and group-level acceptance checks
- full-size terrain/ground/vegetation run now completes and records `used_gpu = true`
- reduced-size scene-aware CPU vs GPU comparison matched within about `2.6e-6 dB` on receiver mean levels
- updated terrain/ground/vegetation physics changed average receiver mean level by about `-3.07 dB` versus baseline, with the largest reduction around `-8.59 dB` at `poi_500_115`

These values are prototype-level engineering checks, not yet validated against measured field data.

## 4. Current Limitations

### 4.1 Acoustic Model Limitations

- shielding is still simplified relative to a full production acoustic model
- building shielding is approximated using footprint edges only
- reflection and diffraction are informed models, but not yet fully validated physics-grade implementations
- terrain-edge shielding is active, and ground/vegetation effects now include path-length and line-height sensitivity, but they are still not fully validated field-grade models
- precomputed correction-field acceleration from the related patent direction is intentionally deferred as a later add-on module

### 4.2 Performance Limitations

- scene-aware runs now support a hybrid GPU path for attenuation and accumulation
- full tensorized scene-aware correction kernels are still not implemented
- default project runs now compute the grid only on the final step unless full grid timeseries storage is explicitly requested
- scene-aware propagation uses a batched `vehicle -> many POIs` provider path
- scene candidate filtering now has a tensor-ready scan path with a heuristic fallback for small POI sets

### 4.3 Product Limitations

- GUI can browse scenarios, inspect a 2D scene view, run scenarios, and inspect results, but scenario comparison and campaign validation are not yet wired into the desktop UI
- no final report generator yet
- campaign import standardization exists, but full production-grade GIS/CAD ingestion is still not implemented
- AI-agent structures exist only as an architectural baseline, not as a working user-facing capability

## 5. Recommended Next Order

1. extend the GUI into scenario comparison flow and, after that, vehicle playback
2. keep deeper validation, calibration, scene-physics, and GPU work tracked as deferred backlog while GUI MVP is under construction
3. resume field-validation and scene-physics hardening after the GUI prototype is usable enough for feedback
4. keep GPU follow-up selective and demand-driven unless hybrid GPU becomes a proven bottleneck
5. deepen reporting and richer agent control after the GUI layer stabilizes

## 6. Bottom Line

MTNsim is now a structured simulation kernel with reproducible scenario handling, comparison capability, a runtime scene hierarchy, material-aware propagation behavior, campaign-aware validation tooling, a usable hybrid scene-aware GPU path, and a working GUI Phase 3 prototype that can launch runs and inspect receiver-level results.
