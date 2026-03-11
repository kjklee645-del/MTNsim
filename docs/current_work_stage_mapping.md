# Current Work Stage Mapping

## Purpose

This document maps the recently implemented propagation tuning and override workflow to the original 13-stage MTNsim development process.
It is intended to be updated continuously whenever a new major implementation milestone is completed.

## Mapping Summary

| Original Stage | Relation to Current Work | Current Status |
|---|---|---|
| 1. Product direction / PRD / architecture | Serves as the governing reference for the current work | Completed |
| 2. Manifest / schema definition | Expanded to include `propagation_model.reflection` and `propagation_model.diffraction` override structures | Completed, extended |
| 3. Package decomposition | Propagation settings now flow through `schema -> service -> runtime` | Completed |
| 4. SUMO integration + scenario execution kernel | Effective propagation settings are now applied during actual simulation execution | Completed |
| 5. Run/result schema + comparison service | Effective propagation settings are recorded in run results and detected in scenario comparisons | Completed, extended |
| 6. Propagation module separation | Reflection and diffraction now have their own model settings and runtime interfaces | Completed |
| 7. Shielding v1 | Shielding remains the geometric input used by reflection/diffraction logic | Completed |
| 8. Scene hierarchy clarification | Barrier/building objects now serve as explicit propagation context providers | Partially completed |
| 9. Material-based computation | Material-aware behavior is now managed alongside tunable model parameters | Partially completed, in progress |
| 10. Reflection / diffraction | Main target of this work: tuned defaults applied and scenario-level override path added | Partially completed, advanced |
| 11. Calibration | Override path prepares the system for future measured-value-based parameter updates | Partially completed, preparation strengthened |
| 12. GUI | Not started, but the typed override structure is ready for future UI controls | Not started |
| 13. AI agent control layer | Not started, but the typed parameter model is now suitable for natural-language agent control later | Not started, groundwork improved |

## Interpretation

The current work belongs primarily to Stage 10.
It also directly supports Stage 9 and Stage 11.
From a product-engineering perspective, it strengthens Stage 2, Stage 5, and Stage 13 because propagation parameters are now:

- represented as structured scenario data,
- reproducible in run outputs,
- overrideable without editing engine source code,
- compatible with future GUI and AI-agent control layers.

## Operational Rule For Ongoing Maintenance

This document should be updated whenever one of the following happens:

- a stage moves from `not started` to `partial`,
- a stage moves from `partial` to `completed`,
- a new implementation affects more than one original stage,
- a new runtime/configuration mechanism changes how progress should be interpreted.

## Current Milestone Covered By This Document

The current mapping reflects the following recent additions:

- benchmark-based propagation tuning workflow,
- tuned defaults applied to reflection/diffraction models,
- scenario-level override path for propagation parameters,
- run-result persistence of effective propagation settings,
- scenario comparison support for propagation-model differences.
