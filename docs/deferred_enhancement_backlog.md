# MTNsim Deferred Enhancement Backlog

Date: 2026-03-18
Purpose: capture the high-value engine, validation, and performance work that remains important, but is intentionally not the immediate focus while GUI MVP work proceeds.

## 1. Why This Backlog Exists

MTNsim has reached the point where a user-facing prototype is strategically more valuable than continuing to deepen the engine in isolation.

The items below are not cancelled. They are deferred so the team can:
- put a usable GUI in front of real users
- validate interaction flow and product shape earlier
- return to high-end engine work with clearer user feedback

## 2. Deferred Work Areas

### 2.1 Field Validation and Acceptance Hardening

Keep for a later phase:
- true field dataset ingestion beyond seeded reference packages
- tighter acceptance rules by receiver group, time window, and campaign type
- sensor quality diagnostics such as drift, missing spans, and unstable offsets
- calibration-before/after comparison summaries for real campaign packages
- stronger campaign comparison across locations and operating conditions

Why deferred:
- the current validation pipeline is structurally usable
- the main missing ingredient is real measured data, not more workflow scaffolding

### 2.2 Calibration Deepening

Keep for a later phase:
- receiver-specific correction recommendations by cause class
- sensor position uncertainty handling
- better automatic time alignment heuristics
- campaign-level correction suggestion packaging for review and approval
- clearer distinction between model bias, sensor issues, and scene-mapping issues

Why deferred:
- current calibration already supports alignment, outlier rejection, and structured recommendations
- further progress depends heavily on real field data and review cycles

### 2.3 Terrain / Ground / Vegetation Physics Deepening

Keep for a later phase:
- richer terrain surfaces beyond line-edge shielding
- slope-aware terrain screening and elevation-aware path geometry
- stronger ground-effect formulations and surface-type tuning
- more realistic vegetation attenuation by depth, density, and canopy type
- calibration of terrain/ground/vegetation effects against measurements or reference models

Why deferred:
- first-pass runtime objects and path-aware corrections are already present
- immediate product value now comes more from usability than further heuristic refinement

### 2.4 Reflection / Diffraction Validation and Tuning

Keep for a later phase:
- more benchmark cases tied to reference solutions
- measured-data-based tuning of reflection and diffraction parameters
- scenario-specific parameter envelopes
- stronger material-parameter calibration loops

Why deferred:
- current benchmark/tuning path exists and passes seeded reference checks
- the main gap is external validation, not missing internal structure

### 2.5 Full Scene-Aware GPU Acceleration

Keep for a later phase:
- tensorized shielding kernels
- tensorized reflection/diffraction context generation
- tensorized ground/vegetation correction paths
- fully GPU-based scene-aware correction generation
- dedicated performance benchmark suite for large scenes and denser receiver grids

Why deferred:
- free-field GPU path exists
- scene-aware hybrid GPU path exists and is already usable
- full tensorization is a substantial engineering block and not the present bottleneck for a GUI prototype

### 2.6 Precomputed Correction-Field Module (Patent Add-On)

Keep for a later phase:
- static correction precompute engine
- correction-map / correction-volume generation
- runtime lookup path for precomputed static propagation adjustments
- separation of static and dynamic propagation components

Why deferred:
- the underlying scene/runtime/propagation structure now makes this possible later
- it is intentionally not part of the current mainline build

### 2.7 Reporting, Publishing, and AI-Agent Layers

Keep for a later phase:
- production-grade report generator
- regulatory export formats
- bounded command bus for AI-agent execution
- audit/replay flows for agent-driven changes
- natural-language scenario control

Why deferred:
- the GUI MVP should stabilize user flow first
- agent control is easier to build once GUI commands and user tasks are clearer

### 2.8 GUI Preview and Editing Polish

Keep for a later phase:
- highlight receivers or geometry changed by unsaved scenario-editor preview values
- preview reset / revert controls in the Scenario Editor
- warnings for receivers moved outside practical scene bounds
- stronger live preview hints for invalid versus valid unsaved edits
- richer preview overlays that show what changed before saving
- Project Home expansion with recent comparison history and recent campaign-validation history
- clearer run-monitor <-> Project Home handoff for in-progress versus completed work

Why deferred:
- live unsaved preview now works for scene/details updates
- these are polish improvements rather than immediate workflow blockers


### 2.9 Advanced Visualization and Source-Field Modeling

Keep for a later phase:
- full 3D scene rendering instead of only 2D map/noise overlays
- 3D noise visualization tied to terrain, barriers, buildings, and receiver height
- volumetric source-field models for individual vehicles
- selectable directivity/source-field display modes such as spherical and wedge-like patterns
- tighter linkage between future 3D visualization and more realistic directional propagation models

Why deferred:
- the current 2D GUI prototype is already broad enough that immediate value comes first from fixing aspect ratio and improving visual polish
- true 3D rendering and directional source-field modeling are major expansions that should follow a stabilized operator workflow

## 3. Re-Entry Conditions

Resume one of the deferred tracks when at least one of these becomes true:
- GUI MVP is usable enough that user feedback points to a clear bottleneck
- real field datasets are available for validation work
- hybrid GPU becomes measurably too slow for target scene sizes
- a funding, paper, or demonstration milestone explicitly requires the deeper work
- a patent-driven extension module is selected for active development

## 4. Current Mainline Focus

The current mainline focus is:
1. GUI product usability, project-entry flow, and operator workflow clarity
2. Visual correctness and polish of the current 2D desktop shell
3. Wiring the existing run/compare/validation engine into a usable desktop prototype

## 5. Maintenance Rule

Update this backlog when:
- an item moves back into active development
- a deferred area is split into smaller milestones
- external constraints change the order again
