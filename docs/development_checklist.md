# MTNsim Development Checklist

Last updated: 2026-03-10
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
| Storage | Structured run records | [~] | JSON/CSV only, not Parquet/DB yet |

## 5. Acoustic Engine

| Area | Item | Status | Notes |
| --- | --- | --- | --- |
| Emission | Vehicle emission module split | [x] | `acoustics/emission` |
| Propagation | Distance module | [x] | active |
| Propagation | Shielding module | [x] | first-pass CPU implementation |
| Propagation | Reflection module | [~] | geometry-informed specular reflection model active |
| Propagation | Diffraction module | [~] | knife-edge-inspired path-excess diffraction model active |
| Noise field | CPU grid/receiver updates | [x] | active |
| Noise field | GPU free-field path | [x] | active without shielding |
| Noise field | GPU shielding-aware path | [ ] | not implemented |

## 6. Scene and Geometry

| Area | Item | Status | Notes |
| --- | --- | --- | --- |
| Scene model | Receiver model | [x] | in schema |
| Scene model | Noise barrier model | [x] | in schema and runtime |
| Scene model | Building footprint model | [x] | in schema and runtime |
| Scene runtime | Dedicated runtime scene object hierarchy | [x] | `scene/objects.py` |
| Compatibility | Legacy `scene.barriers` support | [x] | converted into `noise_barriers` |
| Geometry | Building edge decomposition | [x] | first-pass shielding conversion |
| Geometry | Terrain surface / edge objects | [ ] | not started |
| Geometry | Vegetation objects | [ ] | not started |
| Propagation model | Common propagation properties per object type | [x] | defaults + per-object overrides added |
| Propagation model | Material-aware corrections | [~] | path-specific shielding/reflection/diffraction material corrections active |

## 7. Calibration and Validation

| Area | Item | Status | Notes |
| --- | --- | --- | --- |
| Calibration | Measurement import workflow | [x] | CSV measurement loader and calibration service added |
| Calibration | Sensor alignment | [~] | sensor metadata mapping, time offset, and valid window support added |
| Calibration | Correction factor estimation | [~] | receiver/global bias recommendation with skipped/unmatched tracking added |
| Validation | Benchmark scenarios | [~] | propagation reference benchmark cases, runner, and tuning-space added |
| Validation | Integration tests | [~] | smoke-level validation only |
| Validation | Field-data comparison | [ ] | not started |

## 8. Product Layers

| Area | Item | Status | Notes |
| --- | --- | --- | --- |
| Reporting | Report generation | [ ] | not started |
| Visualization | GUI | [ ] | intentionally deferred |
| API | Local API layer | [~] | thin local layer exists |
| Agent | Bounded command architecture baseline | [~] | early structure only |
| Agent | Real natural-language scenario control | [ ] | not started |
| Agent | Audit/replay flow | [ ] | not started |

## 9. Current Recommended Order

| Priority | Next item | Status | Why next |
| --- | --- | --- | --- |
| 1 | Validate and tune reflection/diffraction against measured or reference cases | [ ] | geometry-informed models are active, but still need validation |
| 2 | Strengthen material-aware corrections beyond heuristic shielding use | [ ] | current version is still first-pass only |
| 3 | Deepen calibration workflow with richer sensor metadata and alignment | [ ] | baseline calibration loop now exists |
| 4 | Deepen reporting / GUI / richer agent control | [ ] | should come after core physics and validation |

## 10. Maintenance Rule

Update this document when one of the following changes:
- a checklist item moves from `[ ]` to `[~]` or `[x]`
- the recommended next order changes
- a new major subsystem is added
- a previously completed item is discovered to be only partial