# Current Work Stage Mapping

## Purpose

This document maps the currently implemented scene-aware propagation, validation, hybrid GPU, and GUI workflow work to the original 13-stage MTNsim development process.
It should be updated whenever a major implementation milestone changes the effective development priority.

## Mapping Summary

| Original Stage | Relation to Current Work | Current Status |
| --- | --- | --- |
| 1. Product direction / PRD / architecture | Still the governing reference for current implementation choices | Completed |
| 2. Manifest / schema definition | Expanded over time to cover propagation overrides, richer scene objects, calibration, and field-campaign manifests | Completed, extended |
| 3. Package decomposition | Execution, propagation, scene, calibration, validation, and campaign workflows now live in separated packages | Completed |
| 4. SUMO integration + scenario execution kernel | Stable manifest/scenario-driven execution path remains the base for all new work | Completed |
| 5. Run/result schema + comparison service | Run summaries, scenario diffs, result diffs, and campaign validation summaries now support reproducible evaluation | Completed, extended |
| 6. Propagation module separation | Distance, shielding, reflection, diffraction, correction, and provider layers are now separated | Completed |
| 7. Shielding v1 | Active and still used as a first-pass scene-aware geometric core | Completed |
| 8. Scene hierarchy clarification | Runtime scene hierarchy now includes barriers, buildings, terrain edges, ground surfaces, and vegetation zones | Partially completed, advanced |
| 9. Material-based computation | Material-aware corrections are active across multiple path types, but still first-pass and not fully field-validated | Partially completed, advanced |
| 10. Reflection / diffraction | Active models plus benchmark/tuning workflow exist, but more physics and validation depth are still needed | Partially completed, advanced |
| 11. Calibration | Calibration, validation suite, field-campaign inspection, campaign-aware validation, and campaign validation UI workflows all exist, but real field data is still limited | Partially completed, advanced |
| 12. GUI | GUI MVP planning is complete and the desktop prototype now supports project browsing, run/result inspection, scenario comparison, campaign validation workflows, and limited scenario editing | Partially completed, advanced |
| 13. AI agent control layer | Typed configuration and bounded architecture groundwork exist, but real user-facing agent control is not implemented | Not started, groundwork improved |

## Current Interpretation

The current codebase is no longer centered on Stage 10 alone.
It now spans three active implementation fronts:

- Stage 10: propagation and scene-aware execution
- Stage 11: calibration, validation, and field-campaign workflows
- Stage 8/9: richer scene objects and material-aware scene behavior
- Stage 11/12: campaign validation and calibration workflows surfaced through the GUI

From a product-engineering perspective, the current state also strengthens Stage 2 and Stage 5 because the system now has:

- broader typed input contracts,
- reproducible run outputs,
- standardized campaign import rules,
- campaign-level validation summaries,
- a usable hybrid scene-aware GPU execution path.

## Priority Interpretation

The current recommended order is:

1. fix the GUI scene/playback aspect-ratio problem so visual trust is not undermined by stretched geometry
2. raise GUI visual polish and product-facing design quality
3. continue project/run/result UX polish now that project creation/import/attach is usable
4. treat 3D scene/noise visualization as the next visualization expansion after the 2D shell is corrected and polished
5. treat volumetric and directional source-field modeling as the next major acoustic-visualization expansion after the 3D scene layer is defined
6. keep deeper validation, calibration, scene physics, and GPU work on the deferred backlog unless external data or product needs pull them forward

This means the mainline focus has shifted from deeper engine refinement to product usability and trustworthy visualization.
The hybrid scene-aware GPU path is considered sufficient for the current stage unless scale or workflow requirements prove otherwise.

## Maintenance Rule

Update this document whenever one of the following happens:

- a stage moves from `not started` to `partial`
- a stage moves from `partial` to `completed`
- the recommended execution priority changes
- a new subsystem shifts the center of gravity across multiple original stages

Current GUI plan update:
- a dedicated `Scene Object Editor` is now part of the mainline product plan because scene-aware propagation features already exist in the engine but still depend on manual scenario-file editing
- in the original 13-step model, this sits primarily under `12. GUI`, while enabling fuller use of `8. scene hierarchy`, `9. material-aware calculation`, and `10. reflection/diffraction` from a user-facing workflow
