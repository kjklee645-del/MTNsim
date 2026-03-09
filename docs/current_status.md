# MTNsim Current Status

Date: 2026-03-09

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
- reflection and diffraction modules exist as placeholders for later expansion

### 2.4 Scene Generalization Work

Current scene objects:
- `noise_barriers`
- `buildings`

Behavior:
- a `noise_barrier` is represented as a single line segment with height, attenuation, and material tag
- a `building` is represented as a footprint polygon, height, attenuation, and material tag
- building footprints are decomposed into edge segments for first-pass shielding checks

Compatibility note:
- legacy `scene.barriers` input is still accepted and internally converted into `noise_barriers`

### 2.5 Comparison Workflow

Implemented:
- configuration comparison between two scenarios
- result comparison between two executed runs

Current comparison outputs include:
- changed scenario fields
- receiver-level min/max/mean delta values
- aggregate mean-of-mean dB delta summary

## 3. Validated Scenarios

Validated scenario files:
- `baseline.toml`
- `speed_drop_80.toml`
- `lane_change_enforce.toml`
- `barrier_shielding.toml`
- `building_shielding.toml`

Observed comparison examples:
- `baseline` vs `speed_drop_80`: average receiver mean level decreased by about `-1.60 dB`
- `baseline` vs `lane_change_enforce`: small average decrease around `-0.10 dB`
- `baseline` vs `barrier_shielding`: average receiver mean level decreased by about `-4.74 dB`
- `baseline` vs `building_shielding`: average receiver mean level decreased by about `-5.56 dB`

These values are prototype-level engineering checks, not yet validated against measured field data.

## 4. Current Limitations

### 4.1 Acoustic Model Limitations

- shielding is simplified to line-of-sight crossing plus fixed attenuation
- building shielding is approximated using footprint edges only
- reflection is not implemented yet
- diffraction is not implemented yet
- material tags are stored but not yet used in propagation formulas

### 4.2 Performance Limitations

- shielding-enabled runs currently fall back to CPU
- GPU is currently practical only for free-field distance-based computation

### 4.3 Product Limitations

- no GUI yet
- no calibration pipeline yet
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

This order was correct because:
- stable config had to come before larger refactoring
- execution and result reproducibility had to come before GUI or AI control
- propagation needed to be modular before scene complexity increased
- scene hierarchy needed to be clarified before material-based propagation logic is added

## 6. Recommended Next Order

1. refine the scene-object hierarchy further
2. add common propagation properties for each scene object type
3. implement material-aware corrections on top of that hierarchy
4. extend reflection and diffraction beyond placeholders
5. add calibration workflow against measurements
6. only then deepen higher-level product layers such as reporting, GUI, and richer agent control

## 7. Practical Repository State

Repository now contains:
- source packages under `src/mtnsim`
- example manifest and scenarios under `examples`
- schema files under `schemas`
- example SUMO network under `data/sumo`
- planning and status docs under `docs` and the repository root

Repository excludes from version control through `.gitignore`:
- `outputs/`
- Python cache files
- local scratch and build artifacts

## 8. Bottom Line

MTNsim is no longer just a prototype script. It is now a structured simulation kernel with a clear product direction, reproducible scenario handling, comparison capability, and the first usable step toward scene-aware traffic-noise propagation.