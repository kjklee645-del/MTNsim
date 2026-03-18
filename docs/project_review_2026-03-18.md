# MTNsim Project Review (2026-03-18)

## Purpose

This document summarizes three things:
- the major implementation tracks MTNsim was originally expected to cover
- what is already implemented in the repository today
- what should be implemented next, based on the current product stage

## 1. Original Project Scope

MTNsim was always larger than a single noise-calculation script. The intended scope can be grouped into six tracks.

1. Simulation core
- SUMO-backed microscopic execution
- scenario-driven vehicle control
- receiver/grid output generation

2. Acoustic and propagation engine
- source emission modeling
- distance attenuation
- shielding, reflection, diffraction
- material-aware propagation behavior
- GPU acceleration where useful

3. Scene and geometry model
- roads and receivers
- barriers, buildings, terrain, ground, vegetation
- richer scene-aware runtime objects

4. Calibration and validation
- measured-data import
- calibration and campaign workflows
- acceptance and diagnostic reporting

5. GUI and operator workflow
- project creation/import
- scenario editing
- run/compare/result/playback workflows
- campaign validation workflow

6. Long-term expansion
- 3D visualization
- volumetric or directional source-field models
- precomputed patent-style correction fields
- AI-agent control

## 2. What Is Implemented Today

### 2.1 Core and Engine
- manifest/scenario/run/result schema
- package-based `src/mtnsim` structure
- SUMO-backed deterministic run service
- receiver timeseries and final grid snapshot output
- scenario/result comparison services
- first-pass propagation split for distance, shielding, reflection, diffraction, and correction
- scene-aware hybrid GPU path

### 2.2 Scene and Validation
- scene runtime hierarchy for barriers, buildings, terrain edges, ground surfaces, and vegetation zones
- calibration workflow with metadata mapping, auto time sync, and outlier rejection
- campaign inspection, campaign validation, and campaign comparison workflows
- benchmark/tuning/validation suite infrastructure

### 2.3 GUI Prototype
- Project Home
- New Project / Import SUMO Project / Attach SUMO
- Scenario Editor with Save As and live preview
- Scene View
- Run Monitor
- Result Viewer
- Vehicle Playback
- Scenario Comparison
- Campaign Validation
- playback export as PNG / GIF / MP4

## 3. Current Stage Interpretation

MTNsim is no longer just a research script. It is now a usable GUI-based desktop prototype around a structured simulation kernel.

This means the project has already crossed the following threshold:
- users can create or import their own projects
- users can run and inspect scenarios without editing TOML manually
- users can compare scenarios and inspect campaign validation outputs inside the GUI

At the same time, MTNsim is not yet a finished professional product. The biggest remaining gaps are now in visualization quality, product polish, and long-term 3D / directional acoustic expansion.

## 4. Main Gaps Right Now

### 4.1 Visual trust gap
- the 2D scene/playback view can distort geometry if aspect ratio is not preserved
- this also makes noise overlays look less trustworthy

### 4.2 Product polish gap
- the GUI is broad and functional but still has a prototype-grade visual style
- more operator-facing clarity and polish are still needed

### 4.3 Next-generation visualization gap
- current map/noise rendering is still 2D
- 3D scene and 3D noise presentation are still missing

### 4.4 Source-field realism gap
- current source radiation is still effectively shown as a flat-height approximation in the GUI
- future source-region visualization should support volumetric and directional options such as spherical or wedge-like patterns

## 5. Recommended Next Order

1. Fix the GUI scene/playback aspect-ratio problem.
2. Improve GUI visual polish.
3. Continue project/run/result UX polish.
4. Design and implement a 3D scene/noise visualization layer.
5. Design and implement volumetric/directional source-field modeling and user-facing selection of source-shape modes.
6. Keep deeper validation, calibration, GPU, and physics hardening on the deferred backlog unless a milestone pulls them forward.

## 6. Bottom Line

MTNsim already has enough engine and GUI breadth to be treated as a real desktop prototype. The next most valuable work is not another large backend refactor. It is making the current product visually trustworthy, easier to use, and ready for the later jump into 3D and directional source-field visualization.
