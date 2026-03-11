# MTNsim Development Checklist

Last updated: 2026-03-11
Owner: Codex + User
Purpose: keep a single progress checklist that reflects product direction, implementation order, and current technical status.

Status legend:
- `[x]` done
- `[~]` in progress or partially done
- `[ ]` not started
- `blocked` waiting on data, decision, or external dependency

## 1. Product and Planning

| Area | Item | Status | Notes |
| --- | --- | --- | --- |
| Product direction | Product direction document | [x] | `MTNsim_product_direction.md` |
| Product planning | PRD draft | [x] | `MTNsim_PRD_draft.md` |
| Architecture | Package architecture draft | [x] | `MTNsim_package_architecture.md` |
| Progress tracking | Progress review against docs | [x] | `docs/progress_review_against_plan.md` |
| Ongoing tracking | Persistent development checklist | [x] | This document |

## 2. Configuration and Project Structure

| Area | Item | Status | Notes |
| --- | --- | --- | --- |
| Manifest | Project manifest format | [x] | `examples/project.toml` |
| Schema | Scenario schema | [x] | `schemas/scenario.schema.json` |
| Schema | Run schema | [x] | `schemas/run.schema.json` |
| Schema | Result schema | [x] | `schemas/result.schema.json` |
| Packaging | Python package skeleton | [x] | `src/mtnsim` |
| Metadata | README and package metadata | [x] | `README.md`, `pyproject.toml` |

## 3. Core Execution Kernel

| Area | Item | Status | Notes |
| --- | --- | --- | --- |
| SUMO | SUMO adapter separation | [x] | `traffic/sumo_adapter.py` |
| Scenario control | Vehicle deployment and lane control | [x] | `traffic/vehicle_controls.py` |
| Runner | Manifest/scenario-driven run service | [x] | `services/run_service.py` |
| App entry | CLI summary and run commands | [x] | `app/main.py` |
| Data output | Run manifest output | [x] | JSON output created per run |
| Data output | Receiver timeseries output | [x] | CSV per receiver |
| Data output | Grid final snapshot output | [x] | JSON snapshot |

## 4. Comparison and Reproducibility

| Area | Item | Status | Notes |
| --- | --- | --- | --- |
| Scenario diff | Scenario comparison service | [x] | `services/compare_service.py` |
| Result diff | Run-result comparison service | [x] | receiver deltas and summary |
| Repeatability | Fixed manifest/scenario inputs | [x] | reproducible run entry points |
| Reproducibility | Deterministic seeded execution | [x] | Python vehicle deployment and SUMO runs both use the project seed |
| Storage | Structured run records | [~] | JSON/CSV only, not Parquet/DB yet |

## 5. Acoustic Engine

| Area | Item | Status | Notes |
| --- | --- | --- | --- |
| Emission | Vehicle emission module split | [x] | `acoustics/emission` |
| Propagation | Distance module | [x] | active |
| Propagation | Shielding module | [x] | first-pass active implementation |
| Propagation | Reflection module | [~] | geometry-informed specular reflection model active |
| Propagation | Diffraction module | [~] | knife-edge-inspired path-excess diffraction model active |
| Noise field | CPU grid/receiver updates | [x] | active |
| Noise field | GPU free-field path | [x] | active |
| Noise field | Scene-aware hybrid GPU path | [x] | provider computes corrections, GPU handles attenuation and accumulation |
| Noise field | Full tensorized scene-aware GPU path | [ ] | not implemented yet |

## 6. Scene and Geometry

| Area | Item | Status | Notes |
| --- | --- | --- | --- |
| Scene model | Receiver model | [x] | in schema |
| Scene model | Noise barrier model | [x] | in schema and runtime |
| Scene model | Building footprint model | [x] | in schema and runtime |
| Scene runtime | Dedicated runtime scene object hierarchy | [x] | `scene/objects.py` |
| Compatibility | Legacy `scene.barriers` support | [x] | converted into `noise_barriers` |
| Geometry | Building edge decomposition | [x] | first-pass shielding conversion |
| Geometry | Terrain surface / edge objects | [~] | `terrain_edges` added as first-pass scene/runtime objects; richer terrain surfaces still limited |
| Geometry | Vegetation objects | [~] | `vegetation_zones` added as first-pass scene/runtime objects |
| Propagation model | Common propagation properties per object type | [x] | defaults + per-object overrides added |
| Propagation model | Material-aware corrections | [~] | geometry-coupled shielding/reflection/diffraction corrections plus path-length-aware and line-height-aware ground/vegetation corrections |

## 7. Calibration and Validation

| Area | Item | Status | Notes |
| --- | --- | --- | --- |
| Calibration | Measurement import workflow | [x] | CSV measurement loader and calibration service added |
| Calibration | Sensor alignment | [~] | sensor metadata mapping, manual offset, auto time sync, and valid window support added |
| Calibration | Correction factor estimation | [~] | receiver/global bias recommendation, structured calibration recommendations, and skipped/unmatched tracking added |
| Validation | Benchmark scenarios | [x] | expanded propagation benchmark suite, total-correction cases, runner, tuning-space, and tuned defaults added |
| Validation | Integration tests | [~] | smoke-level validation only |
| Validation | Field-data comparison | [~] | validation suite covers multiple seeded references; true field datasets still needed |
| Validation prep | Field-data checklist and methodology docs | [x] | `docs/field_validation_data_checklist.md`, `docs/field_validation_methodology.md` |
| Validation prep | Field-campaign import convention and quality report flow | [x] | demo/template campaigns plus `--inspect-field-campaign` added |
| Validation prep | Campaign-aware validation/report flow | [x] | `--validate-field-campaign` now runs simulation, calibration, thresholds, receiver/group coverage checks, acceptance classification, diagnostics, and reports |
| Validation prep | Multi-campaign comparison flow | [x] | `--compare-field-campaigns` validates and compares two campaign packages with JSON/Markdown output |

## 8. Product Layers

| Area | Item | Status | Notes |
| --- | --- | --- | --- |
| Reporting | Report generation | [ ] | not started |
| Visualization | GUI MVP planning | [x] | `docs/gui_mvp_plan.md` |
| Visualization | GUI Phase 1 skeleton | [x] | project loading, scenario browsing, scenario-detail preview, and status/log shell implemented in `src/mtnsim/gui` |
| Visualization | GUI Phase 2 run flow | [x] | background run worker, progress monitor, and output-path display implemented |
| Visualization | GUI Phase 3 result viewer | [x] | recent results list, receiver stats table, and built-in receiver-series chart implemented |
| Visualization | GUI Scene View | [x] | SUMO road polylines, receivers, and scenario geometry layers rendered in a 2D scene view |
| Visualization | GUI implementation | [~] | active track; next is scenario comparison wiring |
| API | Local API layer | [~] | thin local layer exists |
| Agent | Bounded command architecture baseline | [~] | early structure only |
| Agent | Real natural-language scenario control | [ ] | not started |
| Agent | Audit/replay flow | [ ] | not started |

## 9. Current Recommended Order

| Priority | Next item | Status | Why next |
| --- | --- | --- | --- |
| 1 | Extend GUI Phase 3 into scenario comparison flow | [~] | run execution and result inspection are wired; comparison is the next operator-facing workflow gap |
| 2 | Keep deeper validation, calibration, physics, and GPU work on the deferred backlog while GUI MVP is under construction | [~] | tracked in `docs/deferred_enhancement_backlog.md` so the mainline focus stays clear |
| 3 | Resume field-data validation hardening after the GUI prototype is usable | [~] | real user feedback and real datasets should shape the next round of engine refinement |
| 4 | Add scene-aware performance benchmarking and selective GPU follow-up only where hybrid GPU becomes the bottleneck | [~] | hybrid GPU path is already usable, so more GPU work is not the immediate product priority |
| 5 | Deepen reporting / richer agent control after GUI flows stabilize | [ ] | depends on a usable GUI shell and clearer operator workflows |

## 10. Maintenance Rule

Update this document when one of the following changes:
- a checklist item moves from `[ ]` to `[~]` or `[x]`
- the recommended next order changes
- a new major subsystem is added
- a previously completed item is discovered to be only partial
