# Progress Review Against Planning Docs

Date: 2026-03-09

Reviewed documents:
- `D:/Codex/MTNsim/MTNsim_PRD_draft.md`
- `D:/Codex/MTNsim/MTNsim_product_direction.md`
- `D:/Codex/MTNsim/MTNsim_package_architecture.md`

## 1. Overall Assessment

The current implementation order is broadly correct.

We started with:
1. product direction and architecture
2. project manifest and scenario schema
3. package skeleton
4. SUMO integration and scenario-driven execution
5. scenario variants for baseline, lane-change, and speed-drop experiments

This is aligned with the intended early-phase sequence in the planning documents.

## 2. Alignment With `MTNsim_product_direction.md`

Planned early priorities:
- refactor code into product architecture
- separate SUMO integration from acoustic logic
- move experiment parameters out of the script into config
- build a reusable research kernel first

Status:
- done: package refactor baseline created
- done: SUMO adapter separated from scenario controls
- done: experiment parameters moved into TOML scenario files
- done: receiver history and run manifest outputs created
- partial: results are still CSV/JSON only, not yet Parquet/SQLite
- not started: 3D correction and calibration workflow

Conclusion:
Current work matches the intended phase 1 kernel-refactor direction.

## 3. Alignment With `MTNsim_PRD_draft.md`

Relevant Phase A / Phase B items:
- modular refactor
- config manifest
- result storage standard
- initial command schema for agent control
- vehicle-level simulation loop
- receiver and grid outputs
- scenario runner
- batch-style execution API

Status:
- done: modular refactor baseline
- done: project manifest and scenario schema
- partial: result storage standard exists but is still minimal
- partial: command bus exists, but no real domain command set yet
- done: vehicle-level simulation loop integrated through `RunService`
- done: receiver output and grid snapshot output
- done: scenario runner through CLI and `AppRunner`
- partial: API exists but is still thin and local-only

Conclusion:
We are in late Phase A to early Phase B territory.

## 4. Alignment With `MTNsim_package_architecture.md`

Recommended implementation order:
1. schemas
2. core
3. traffic
4. scene
5. acoustics
6. io
7. services
8. api
9. visualization
10. agent

Actual order taken:
1. schemas
2. io/project loading
3. core
4. scene
5. acoustics
6. traffic
7. services
8. api
9. app runner
10. scenario variants and execution validation

Assessment:
- the order is close enough to the plan
- `io` came slightly earlier than originally suggested, which is acceptable because manifest loading was required immediately
- `app` was added early for testing convenience, which is also acceptable
- `visualization`, `calibration`, and `agent` are intentionally deferred, which is correct at this stage

Conclusion:
The package implementation sequence is acceptable and does not create architectural debt at this stage.

## 5. What Has Been Completed

### Architecture and Config
- `pyproject.toml`
- `examples/project.toml`
- `examples/scenarios/baseline.toml`
- `examples/scenarios/lane_change_enforce.toml`
- `examples/scenarios/speed_drop_80.toml`
- `schemas/project.schema.json`
- `schemas/scenario.schema.json`

### Runtime and Domain Structure
- `src/mtnsim/schemas/project.py`
- `src/mtnsim/schemas/scenario.py`
- `src/mtnsim/traffic/sumo_adapter.py`
- `src/mtnsim/traffic/vehicle_controls.py`
- `src/mtnsim/scene/grid.py`
- `src/mtnsim/acoustics/emission/road_vehicle.py`
- `src/mtnsim/acoustics/field/noise_grid.py`
- `src/mtnsim/io/project_store.py`
- `src/mtnsim/io/result_store.py`
- `src/mtnsim/services/run_service.py`
- `src/mtnsim/api/project_api.py`
- `src/mtnsim/api/simulation_api.py`
- `src/mtnsim/app/main.py`
- `src/mtnsim/app/runner.py`

### Execution Validation
- baseline CPU run succeeded
- speed-drop CPU run succeeded
- lane-change CPU run succeeded after robust lane-index clamping was added

## 6. What Is Still Missing For The Planned Sequence

### Immediate next items
- formal run/result schemas under `mtnsim.schemas`
- better result storage structure beyond CSV and a single grid snapshot JSON
- stronger integration tests and benchmark tests
- scenario comparison service

### Next major milestone items
- 3D scene objects beyond network bounds and flat receiver/grid placement
- propagation corrections for shielding, reflection, diffraction
- calibration pipeline against measured data
- agent command schema and bounded command execution layer

## 7. Recommended Next Order From Here

1. add run schema and result schema
2. add scenario comparison service and result summary service
3. add integration tests for baseline vs speed-drop vs lane-change runs
4. improve result storage to structured run records
5. start propagation/correction module split
6. begin calibration data pipeline
7. only after that, deepen command bus and agent interfaces

## 8. Final Verdict

Yes, the work is proceeding in the right order.

The current branch of work is consistent with the planning documents because it prioritizes:
- stable configuration
- modular runtime structure
- executable simulation kernel
- reproducible scenario runs

The main thing to avoid from here is jumping early into GUI or free-form AI control before the result schema, comparison workflow, and correction/calibration layers are stabilized.
