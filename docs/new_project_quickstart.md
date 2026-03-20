# New Project Quickstart

This document is the shortest end-to-end path for a new user.
It covers:
- launching the GUI
- creating or importing a project
- authoring scene objects
- defining the grid region
- running a simulation
- viewing 2D/3D results

## 1. Launch the GUI

```powershell
cd D:\Codex\MTNsim
$env:PYTHONPATH='D:\Codex\MTNsim\src'
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --gui
```

## 2. Create a Project

### Option A: Import an Existing SUMO Project

1. Open `Project > Import SUMO Project`.
2. Fill in:
   - `Project name`
   - `Description`
   - `Default scenario`
   - `Project folder`
   - `SUMO config (.sumocfg)`
3. Choose optional import settings:
   - copy SUMO files into project
   - allow overwrite
   - optional scene file
   - optional measurements file
   - optional measurement metadata file
4. Choose starter directivity if needed:
   - `isotropic`
   - `wedge`
   - `dual_wedge`
5. Click `Inspect SUMO Files`.
6. If inspection passes, click `Import Project`.

### Option B: Create an Empty MTNsim Project

1. Open `Project > New Project`.
2. If you want a project shell first, disable `Attach SUMO config now`.
3. Later, use `Project > Attach SUMO` to connect a `.sumocfg` file.

## 3. Check the Project Home Screen

After creation or import, use `Home` in the left workspace list.
Check:
- project name
- status badge
- available scenarios
- recent runs

## 4. Edit the Scenario

Open `Editor` from the left workspace list.

You can edit:
- max vehicles
- start speed
- vehicle interval
- post target speed
- background noise
- directivity mode / strength / wedge angle
- receiver table
- rectangular grid override

Use `Save As New Scenario` to create a derived scenario.

Reference:
- [scenario_editor_field_reference.md](D:/Codex/MTNsim/docs/scenario_editor_field_reference.md)

## 5. Create Scene Objects

Open `Scene Objects` from the left workspace list.

Supported objects:
- `noise_barriers`
- `buildings`
- `terrain_edges`
- `ground_surfaces`
- `vegetation_zones`

Available authoring methods:
- list/form editing
- `Add New`
- `Delete Selected`
- `Duplicate Selected`
- `Undo / Redo`
- `Draw In Scene View`
- direct manipulation in `Scene View`

## 6. Define the Grid Region

You can keep the default corridor-based region or define a custom rectangle.

### Numeric method
In `Editor`:
- enable `Grid Override`
- set `Grid Min X`, `Grid Max X`, `Grid Min Y`, `Grid Max Y`

### Scene method
In `Editor`:
1. enable `Grid Override`
2. click `Draw Grid Region`
3. drag a rectangle in `Scene View`
4. return to `Editor`

The grid region remains visible in `Scene View` and can be edited again later.

## 7. Inspect the Scene

Open `Scene` from the left workspace list.

You can inspect:
- roads
- receivers
- barriers
- buildings
- terrain
- ground
- vegetation
- grid region

## 8. Run the Simulation

Use the top toolbar or the quick run button:
- `Run > Run Selected`
- or the quick `Run Selected` button

Then use `Run Monitor` to watch:
- run progress
- current status
- output paths
- execution mode

## 9. Inspect Results

### Result Viewer
Use `Results` to inspect:
- receiver summary table
- receiver time-series
- output files
- exported markdown summary

### Vehicle Playback
Use `Playback` to inspect:
- time slider
- vehicle paths
- 2D heatmap
- selected vehicle contribution
- PNG / GIF / MP4 export

### 3D View
Use `3D View` to inspect:
- 3D roads, receivers, barriers, buildings, terrain, ground, vegetation
- 3D noise surface
- playback-aware 3D vehicles and trails
- 3D source-field overlays
- calculation-linked directivity overlays

## 10. Compare Scenarios

Open `Compare`.

You can:
- compare configuration differences
- run and compare two scenarios
- inspect receiver delta tables
- inspect overlay charts
- export comparison summaries

## 11. Validate Campaign Packages

Open `Validation`.

You can:
- inspect a campaign manifest
- validate a campaign package
- read acceptance status
- inspect diagnostics and recommendations
- open generated artifacts

## 12. Common Notes

- If a SUMO config uses top-level `net-file` and `route-files`, the GUI import flow supports it.
- If `Run Selected` is disabled, the project is usually missing a usable SUMO attachment or a selected scenario.
- The current engine supports directional emission Phase A in actual calculation.
- The 3D source-field display can follow the run's calculation-side directivity.

## Related Documents

- [README.md](D:/Codex/MTNsim/README.md)
- [user_guide.md](D:/Codex/MTNsim/docs/user_guide.md)
- [new_project_import_ux_plan.md](D:/Codex/MTNsim/docs/new_project_import_ux_plan.md)
- [scenario_editor_field_reference.md](D:/Codex/MTNsim/docs/scenario_editor_field_reference.md)
- [visualization_3d_plan.md](D:/Codex/MTNsim/docs/visualization_3d_plan.md)
