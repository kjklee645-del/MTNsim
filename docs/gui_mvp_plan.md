# MTNsim GUI MVP Plan

Date: 2026-03-11
Purpose: define the first user-facing MTNsim desktop prototype so non-developer users can run simulations, compare scenarios, and inspect outputs without editing TOML files or using CLI commands.

## 1. Product Goal

Build a desktop GUI prototype that lets a general user:
- open a project
- choose a scenario
- edit a small set of high-value scenario parameters
- run a simulation
- compare scenarios
- inspect receiver-level results
- open campaign validation outputs

The GUI MVP is not a full professional acoustic workstation. It is a usable operator shell around the existing MTNsim engine.

## 2. Recommended GUI Stack

### 2.1 Primary Choice: PySide6 Desktop App

Recommended stack:
- `PySide6` for desktop UI
- `Qt Model/View` for tables and structured lists
- `QThread` or `QRunnable/QThreadPool` for long-running runs
- `pyqtgraph` for fast receiver time-series plots
- `QGraphicsView` or `Qt Charts` for simple 2D scene/result views
- existing Python services reused directly from `src/mtnsim`

Why this is the right stack now:
- the simulation engine is already Python
- no extra backend service is required for a first prototype
- Windows desktop use is the near-term target
- packaging is simpler than Electron + Python bridge for the current team state
- it keeps the GUI close to the run/calibration/validation services already built

### 2.2 Why Not Electron or Web First

Possible later, but not recommended for the MVP.

Reasons:
- would introduce frontend/backend split too early
- would add IPC and packaging overhead
- current priority is a working tool, not cross-platform polish
- the engine is already local-file and local-process oriented

### 2.3 Technical Direction for Later AI Support

Even in the GUI MVP, actions should be framed as typed operations rather than ad hoc button logic.

Examples:
- `load_project(project_path)`
- `select_scenario(scenario_path)`
- `update_scenario_controls(...)`
- `run_simulation(...)`
- `compare_scenarios(...)`
- `open_campaign_validation(...)`

This keeps the GUI compatible with a later AI command layer.

## 3. MVP Screen Composition

### 3.1 Main Window

Layout recommendation:
- left sidebar: project, scenario, campaign, and recent runs navigation
- center workspace: editor or results view depending on selected mode
- right panel: run status, selected object details, quick actions
- bottom panel: logs, warnings, run progress, errors

### 3.2 Screen A: Project Home

Purpose:
- open a project manifest
- list available scenarios
- show recent runs and recent comparison outputs

Must-have controls:
- `Open Project`
- scenario list
- `Run Selected Scenario`
- `Compare Scenarios`
- `Open Outputs Folder`

### 3.3 Screen B: Scenario Editor (MVP Scope)

Purpose:
- edit only the parameters that matter most for demonstration and early usage

Editable in MVP:
- traffic max vehicles
- start speed
- post-distance target speed
- lane-change mode
- background noise
- receiver list view
- scene object summary counts

Not in MVP editor yet:
- full free-form scene geometry editing
- detailed material parameter editing
- raw propagation model parameter tuning

Design note:
- the editor should show a simplified form view backed by the existing scenario schema
- advanced settings can remain read-only or hidden in the first cut

### 3.4 Screen C: Run Monitor

Purpose:
- show execution progress and output links during a run

Must-have elements:
- current scenario name
- run status: pending / running / completed / failed
- progress indicator by step
- live log panel
- output paths for summary and receiver files
- cancel button if practical

### 3.5 Screen D: Result Viewer

Purpose:
- inspect the main outputs without leaving the GUI

Must-have elements:
- receiver summary table
- receiver time-series plot selector
- run metadata panel
- propagation feature summary
- open raw JSON/CSV actions

Nice-to-have after MVP:
- grid heatmap preview
- scene overlay view
- multiple run overlays

### 3.6 Screen E: Scenario Comparison View

Purpose:
- compare two scenarios through settings and output summaries

Must-have elements:
- scenario A / scenario B picker
- configuration diff summary
- receiver delta table
- key metric cards such as mean delta and largest change
- links to full comparison artifacts

### 3.7 Screen F: Campaign Validation View

Purpose:
- inspect campaign quality and validation outcomes

Must-have elements:
- open campaign manifest
- run inspect / run validate actions
- acceptance status badge
- calibration recommendation list
- receiver/group diagnostics table
- open generated Markdown/JSON reports

## 4. MVP Functional Scope

### 4.1 Must Have

- open project manifest
- browse bundled scenarios
- edit a limited set of scenario controls
- run scenario from GUI
- view receiver summary outputs
- compare two scenarios
- inspect one campaign package
- run one campaign validation and view the report

### 4.2 Should Have

- recent runs list
- output folder shortcuts
- validation status badges
- parameter reset to scenario defaults
- simple scene summary panel

### 4.3 Not in First MVP

- full scene drawing/editing canvas
- CAD/GIS import UI
- full report designer
- multi-window 3D visualization
- AI natural-language panel
- full precomputed correction-field controls

## 5. Proposed Package Structure for GUI

Recommended additions under `src/mtnsim`:
- `gui/app.py`
- `gui/main_window.py`
- `gui/state.py`
- `gui/controllers/`
- `gui/views/project_home.py`
- `gui/views/scenario_editor.py`
- `gui/views/run_monitor.py`
- `gui/views/result_viewer.py`
- `gui/views/scenario_compare.py`
- `gui/views/campaign_validation.py`
- `gui/widgets/`
- `gui/models/`

Responsibilities:
- `views`: Qt widgets and layout
- `controllers`: call existing services and translate results into view state
- `state`: selected project, selected scenario, current run, recent outputs
- `models`: table models and display adapters for schemas/results

## 6. MVP Implementation Order

### Phase 1: GUI Skeleton

Build first:
- application bootstrap [done]
- main window shell [done]
- sidebar navigation [done]
- status/log panel [done]
- project loading and scenario list [done]

Goal:
- a user can open the app and see project/scenario structure

### Phase 2: Run Flow

Build next:
- run button [done]
- background worker for simulation execution [done]
- progress display [done]
- run completion status [done]
- output file links [done]

Goal:
- a user can run an existing scenario from the GUI

### Phase 3: Result Viewer

Build next:
- receiver summary table [done]
- time-series chart for one receiver at a time [done]
- propagation feature card [done as metadata panel]
- recent runs panel [done as recent result list]

Goal:
- a user can inspect what the run produced without opening files manually

### Phase 3.6: Vehicle Playback

Build next:
- record vehicle traces during GUI-triggered runs [done]
- load a playback view on top of the 2D scene canvas [done]
- add a time slider and play/pause controls [done]
- add playback layer toggles and heatmap range/opacity controls [done]

Goal:
- a user can inspect vehicle movement without leaving the GUI

### Phase 4: Scenario Comparison

Build next:
- select two scenarios
- show config diff
- run compare flow
- display receiver delta summary

Goal:
- a user can compare changes without touching CLI

### Phase 5: Campaign Validation Panel

Build next:
- open campaign manifest
- run inspect / validate
- show acceptance result, diagnostics, and recommendations

Goal:
- a user can use the existing validation pipeline from the GUI

### Phase 6: Limited Scenario Editing

Build after the above:
- form-based edits for selected scenario controls
- save-as behavior for derived scenarios
- validation of edited values against schema

Goal:
- a user can create and test simple scenario variations safely

## 7. UX Rules for the MVP

- keep terminology consistent with existing docs: project, scenario, run, campaign, validation
- never force users to edit raw TOML for common tasks
- show output file locations clearly
- prefer explicit buttons over hidden workflows
- surface warnings early when required files are missing
- separate editable controls from advanced read-only settings
- keep the app usable on one laptop screen

## 8. Immediate Engineering Tasks

1. add GUI package skeleton under `src/mtnsim/gui`
2. add a minimal desktop entry point
3. implement project/scenario browser view
4. implement run worker and run monitor
5. implement result summary table + receiver chart
6. add vehicle playback panel [done]
7. add comparison panel
8. add campaign validation panel
9. add limited scenario editor only after read-only flows are stable

## 9. Success Criteria for the GUI MVP

The GUI MVP is successful if a non-developer can do all of the following without terminal use:
- open the MTNsim project
- choose and run `baseline`
- choose and run `terrain_ground_vegetation`
- compare two scenarios and understand the receiver-level difference
- open a demo campaign and validate it
- find the output files for a completed run

## 10. After the MVP

Once the GUI MVP is stable, the likely next layers are:
- richer scene summaries, playback overlays, and map-like views
- more scenario editing coverage
- result-report export
- AI-assisted command entry on top of the same typed GUI actions

### Phase 3.5: 2D Scene View

Build next:
- 2D road network rendering from SUMO net.xml [done]
- receiver markers [done]
- scenario geometry overlays for barriers, buildings, terrain, ground, and vegetation [done]

Goal:
- a user can understand the spatial layout of the scenario before moving to richer playback or comparison tools
