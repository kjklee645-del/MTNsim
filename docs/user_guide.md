# MTNsim User Guide

This guide summarizes the current operator-facing workflows of MTNsim.
It is written for the current desktop prototype and the current CLI entry points.

## 1. Launch and Environment

Validated environment:
- workspace: `D:\Codex\MTNsim`
- Python: `C:\Users\user\miniconda3\envs\Trac\python.exe`

Setup:

```powershell
cd D:\Codex\MTNsim
$env:PYTHONPATH='D:\Codex\MTNsim\src'
```

Launch GUI:

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --gui
```

## 2. Main GUI Structure

Top toolbar:
- `Project`
- `Run`
- `Results`
- `Validation`
- `Help`
- quick `Run Selected`

Left dock:
- `Workspace`
- view switching only

Main workspaces:
- `Home`
- `Scene`
- `Scene Objects`
- `Editor`
- `Compare`
- `Validation`
- `Run Monitor`
- `Results`
- `Playback`
- `3D View`

Right dock:
- `Analysis & Data`

Bottom dock:
- `Status / Logs`

## 3. Project Workflows

Supported project-entry flows:
- create empty project
- import SUMO project from `.sumocfg`
- attach SUMO later to an empty project

Supported optional imports during project entry:
- scene file
- measurements file
- measurement metadata file

Starter scenario options now include default directional emission:
- `isotropic`
- `wedge`
- `dual_wedge`

## 4. Scenario Editing

The current `Editor` supports:
- traffic controls
- lane-change controls
- background noise
- directivity settings, including vertical spread
- receiver table editing
- rectangular grid override
- live unsaved preview in scene/details view
- Save As derived scenario workflow

See:
- [scenario_editor_field_reference.md](D:/Codex/MTNsim/docs/scenario_editor_field_reference.md)

## 5. Scene Object Editing

The current `Scene Objects` workspace supports:
- barriers
- buildings
- terrain edges
- ground surfaces
- vegetation zones

Current editing modes:
- list/form editing
- click-to-draw in `Scene View`
- direct manipulation in `Scene View`
- duplicate
- undo / redo
- Save As to derived scenario

## 6. Grid Region Workflow

MTNsim now supports a custom rectangular simulation region.

Two ways to define it:
- numeric editing in `Editor`
- drag authoring in `Scene View`

Current capabilities:
- persistent visible rectangle in `Scene View`
- later drag edit of the rectangle in `Scene View`
- scenario persistence through grid override fields

## 7. Run and Result Workflow

### Run Monitor
The current `Run Monitor` shows:
- run state
- progress
- execution mode
- output paths
- receiver file summary

### Result Viewer
The current `Results` workspace shows:
- receiver summary table
- receiver time-series chart
- output links
- markdown export

### Scenario Comparison
The current `Compare` workspace supports:
- configuration diff
- run-and-compare flow
- receiver delta table
- overlay chart
- JSON / Markdown export

### Campaign Validation
The current `Validation` workspace supports:
- campaign inspect
- campaign validate
- acceptance summary
- threshold table
- recommendation panel
- artifact links

## 8. Playback Workflow

The current `Playback` workspace supports:
- timeline slider
- play / pause
- speed control
- 2D heatmap
- speed-colored vehicles
- trails
- minimap
- selected vehicle inspection
- selected vehicle contribution heatmap
- receiver contribution summary
- timeline event markers
- camera follow
- PNG / GIF / MP4 export

## 9. 3D Workflow

The current `3D View` supports:
- static 3D scene geometry
- 3D noise surface
- orbit / pan / zoom / reset camera
- playback-aware 3D vehicles
- 3D trails
- selected vehicle highlight
- camera follow
- source-field overlays
  - `off`
  - `sphere`
  - `wedge`
  - `dual_wedge`
- calc-linked directivity display
- dB legend and range controls
- open the active result summary directly from 3D View
- export a 3D PNG snapshot
- export a hi-res 2x 3D PNG snapshot
- inspect 3D receivers, vehicles, barriers, terrain edges, and buildings with hover halos and tooltips
- export a 3D Markdown report

## 10. Directional Emission

Directional emission now includes Phase A horizontal directivity plus a first-pass vertical spread term in actual calculation.

Supported modes:
- `isotropic`
- `wedge`
- `dual_wedge`

Current controls:
- mode
- strength
- wedge angle

Where it is used now:
- scenario editing
- starter project creation/import
- actual run calculation
- playback heatmap recomputation
- 3D calc-linked source-field visualization

Detailed design:
- [directional_emission_plan.md](D:/Codex/MTNsim/docs/directional_emission_plan.md)

## 11. Useful CLI Commands

Default summary:

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main
```

Run selected/default scenario:

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --run --cpu
```

Propagation benchmark:

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --benchmark-propagation
```

Validation suite:

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --validate-suite --cpu
```

Inspect campaign:

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --inspect-field-campaign --campaign-file 'D:\Codex\MTNsim\data\field\demo_seeded_campaign\campaign.json'
```

Validate campaign:

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --validate-field-campaign --campaign-file 'D:\Codex\MTNsim\data\field\demo_seeded_campaign\campaign.json' --cpu
```

## 12. Current Limits

Still deferred:
- tire / engine / exhaust decomposition
- deeper field-data hardening
- full scene-aware GPU path
- patent-style precomputed correction-field acceleration
- AI-agent control layer

## 13. Related Documents

- [README.md](D:/Codex/MTNsim/README.md)
- [new_project_quickstart.md](D:/Codex/MTNsim/docs/new_project_quickstart.md)
- [current_status.md](D:/Codex/MTNsim/docs/current_status.md)
- [development_checklist.md](D:/Codex/MTNsim/docs/development_checklist.md)
- [visualization_3d_plan.md](D:/Codex/MTNsim/docs/visualization_3d_plan.md)
- [directional_emission_plan.md](D:/Codex/MTNsim/docs/directional_emission_plan.md)
- [deferred_enhancement_backlog.md](D:/Codex/MTNsim/docs/deferred_enhancement_backlog.md)


## Directivity Presets

Project setup and Scenario Editor now support directivity presets: `custom`, `passenger`, `bus`, and `truck`. Non-custom presets auto-fill horizontal and vertical directivity values and keep the fields linked until switched back to `custom`.


The Result Viewer and 3D View now show the active directivity preset and the scenario vehicle types that the calculation used.


In 3D View, calc-linked source fields now adopt preset-specific visual profiles. Passenger, bus, and truck presets use different default colors and relative size/height tendencies so the active source-field is easier to interpret.
