# MTNsim

MTNsim is a microscopic traffic-noise simulation workbench built around SUMO, a package-based acoustic engine, and a desktop GUI for project authoring, simulation, result analysis, comparison, validation, and 2D/3D visualization.

## What MTNsim Can Do Today

- Create a new MTNsim project, import an existing SUMO project, or attach SUMO later.
- Edit scenarios from the GUI, including traffic controls, receivers, grid settings, and directional-emission defaults.
- Author scene objects from the GUI:
  - noise barriers
  - buildings
  - terrain edges
  - ground surfaces
  - vegetation zones
- Draw and edit a custom rectangular grid region directly in the Scene View.
- Run SUMO-backed microscopic traffic-noise simulations.
- Inspect receiver time-series, result summaries, and comparison results.
- Replay vehicle motion with 2D and 3D playback-aware noise visualization.
- Inspect campaign validation outputs from field-style package structures.
- View 3D scene geometry, 3D noise surfaces, and first-pass source-field overlays.

## Current Technical Scope

Implemented today:
- deterministic project/scenario execution
- receiver CSV outputs and final grid snapshots
- distance, shielding, reflection, diffraction, and first-pass material-aware correction
- terrain/ground/vegetation first-pass propagation effects
- campaign inspection, validation, and comparison workflows
- directional emission Phase A in actual calculation
  - `isotropic`
  - `wedge`
  - `dual_wedge`
- GUI project workflow
  - project home
  - new/import project
  - attach SUMO
  - scenario editor
  - scene object editor
  - scene view
  - run monitor
  - result viewer
  - vehicle playback
  - scenario comparison
  - campaign validation
  - 3D view

## Repository Layout

- `src/mtnsim`: main application packages
- `examples`: example project manifest and scenarios
- `schemas`: JSON schema files
- `data/sumo`: example SUMO assets
- `data/measurements`: example and seeded measurement data
- `data/field`: field-campaign templates and demo packages
- `benchmarks`: propagation and validation benchmark definitions
- `docs`: user, design, and status documents
- `scripts`: utility scripts

## Quick Start

Environment used during validation:
- workspace: `D:\Codex\MTNsim`
- Python: `C:\Users\user\miniconda3\envs\Trac\python.exe`

Set the source path:

```powershell
cd D:\Codex\MTNsim
$env:PYTHONPATH='D:\Codex\MTNsim\src'
```

Launch the GUI:

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --gui
```

Run the default CLI summary:

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main
```

Run the default scenario:

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --run --cpu
```

Run the propagation benchmark:

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --benchmark-propagation
```

Run the validation suite:

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --validate-suite --cpu
```

Inspect a demo campaign package:

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --inspect-field-campaign --campaign-file 'D:\Codex\MTNsim\data\field\demo_seeded_campaign\campaign.json'
```

Validate a demo campaign package:

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --validate-field-campaign --campaign-file 'D:\Codex\MTNsim\data\field\demo_seeded_campaign\campaign.json' --cpu
```

## Recommended Reading Order

1. `docs/new_project_quickstart.md`
2. `docs/user_guide.md`
3. `docs/scenario_editor_field_reference.md`
4. `docs/current_status.md`
5. `docs/development_checklist.md`

## Key Documents

- `docs/new_project_quickstart.md`
- `docs/user_guide.md`
- `docs/current_status.md`
- `docs/development_checklist.md`
- `docs/directional_emission_plan.md`
- `docs/visualization_3d_plan.md`
- `docs/deferred_enhancement_backlog.md`
- `docs/scenario_editor_field_reference.md`
- `docs/campaign_import_standard.md`

## Current Mainline Focus

- deepen 3D visualization quality and workflow integration
- deepen directional source-field meaning beyond Phase A
- continue GUI/operator polish

Deferred for later milestones:
- tire / engine / exhaust decomposition
- deeper field-data calibration and validation hardening
- full scene-aware GPU path
- patent-style precomputed correction-field module
- AI-agent control layer
