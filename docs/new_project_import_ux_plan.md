# MTNsim New Project and Import UX Plan

Date: 2026-03-13
Purpose: define the first user-facing workflow for creating a new MTNsim project or importing an existing SUMO project without hand-editing `project.toml`.

## 1. Problem Statement

The current GUI can open an existing project manifest and work well once a project already exists. In practice, this means most users start from the bundled `4lane` example project and modify scenarios inside that project.

This is not enough for general users. The GUI now needs a first-class project entry workflow that supports:
- starting a brand-new MTNsim project shell
- importing an existing SUMO project into MTNsim structure
- generating a valid `project.toml`
- generating at least one starter scenario automatically
- validating required files before the user enters the main workspace

## 2. Primary User Flows

### 2.1 Flow A: New Empty Project

Purpose:
- create a clean MTNsim project folder and manifest before any SUMO network is connected

Recommended use:
- users planning a new study package
- teams standardizing folder structure before data is ready
- users who want to attach SUMO files later

Steps:
1. Click `New Project` from Project Home or startup dialog.
2. Enter project name, description, and project root folder.
3. Choose initial mode:
   - `Create empty MTNsim project`
   - `Create project and attach SUMO files now`
4. If empty mode is chosen, generate project skeleton only.
5. Generate a starter scenario file such as `baseline.toml`.
6. Open the new project immediately in the GUI.

### 2.2 Flow B: Import Existing SUMO Project

Purpose:
- take an existing `.sumocfg`-based SUMO case and wrap it in a valid MTNsim project

Recommended use:
- existing SUMO users
- users migrating prototype files into MTNsim
- users who already have `.net.xml`, `.rou.xml`, `.sumocfg`, and optional `.add.xml`

Steps:
1. Click `Import SUMO Project`.
2. Choose either:
   - existing project folder to import into
   - new MTNsim project folder to create
3. Select a `.sumocfg` file.
4. Auto-detect referenced SUMO assets from the config.
5. Show validation summary:
   - found network
   - found route files
   - found additional files
   - missing files
6. Let the user confirm output locations inside the MTNsim project.
7. Generate `project.toml` and one starter scenario.
8. Open the imported project immediately in the GUI.

## 3. UX Surface

### 3.1 Entry Points

The GUI should expose project entry through:
- Project Home toolbar buttons:
  - `Open Project`
  - `New Project`
  - `Import SUMO Project`
- optional startup dialog when no project is loaded

### 3.2 Recommended Wizard Structure

Use a small multi-step wizard or stacked dialog.

#### Step 1: Project Mode
- `Open Existing MTNsim Project`
- `Create New MTNsim Project`
- `Import Existing SUMO Project`

#### Step 2: Project Identity
Fields:
- `Project name`
- `Description`
- `Project folder`
- `Default scenario name`

#### Step 3: SUMO Source
Shown only for import or attach-now mode.

Fields:
- `SUMO config (.sumocfg)`
- optional `Network (.net.xml)` override
- optional `Route (.rou.xml)` override
- optional `Additional files (.add.xml)` override
- `Copy files into project` vs `Reference files in place`

#### Step 4: Validation Summary
Show:
- resolved file list
- missing files
- path conflicts
- relative path plan for manifest generation
- warnings such as `route file not found`, `scene file not provided`, or `measurements not configured`

#### Step 5: Finish
Show generated outputs:
- `project.toml`
- `scenarios/baseline.toml`
- copied or linked SUMO files
- output directory
- optional empty `data/scene` and `data/measurements` folders

## 4. Generated Project Structure

Recommended generated structure:

```text
<ProjectRoot>/
  project.toml
  scenarios/
    baseline.toml
  data/
    sumo/
      *.sumocfg
      *.net.xml
      *.rou.xml
      *.add.xml (optional)
    scene/
    measurements/
  outputs/
```

Notes:
- use `project.toml` at the project root for user-created projects
- continue supporting `examples/project.toml` for the bundled demo project
- keep scenario files under `scenarios/` for user-created projects

## 5. Generated Manifest Rules

### 5.1 New Empty Project

Generate a manifest with:
- project metadata
- output folder
- default scenario path assumptions
- no required measurement files yet
- no SUMO paths if the user chose fully empty mode

Required behavior:
- project should still open in the GUI
- Run actions should be disabled until SUMO config is attached
- GUI should clearly say `SUMO source not configured yet`

### 5.2 Imported SUMO Project

Generate a manifest with:
- `paths.sumo_config`
- `paths.network`
- `paths.route` when determinable
- `paths.outputs`
- optional placeholders for scene and measurements

Manifest path policy:
- prefer relative paths inside the project root
- if the user chooses `Reference files in place`, still store relative paths when possible; otherwise store absolute paths and mark the project as externally linked in metadata later if needed

## 6. Starter Scenario Generation

Every new/imported project should get one starter scenario.

Recommended starter values:
- scenario name: `baseline`
- traffic defaults based on current example profile
- noise/grid defaults based on current engine-safe values
- no advanced propagation overrides by default
- if the imported SUMO case already implies bounds, keep the default receiver list minimal and safe

Minimum receiver strategy for import:
- if no receiver geometry is known, generate 2-4 placeholder receivers near the network centerline and label them clearly as starter receivers
- include a GUI warning that receiver positions should be reviewed before real analysis

## 7. Validation Rules

The wizard should validate before project creation/import completes.

### 7.1 Hard Errors
- project folder is missing or not writable
- `.sumocfg` file is missing when import mode is selected
- referenced network file cannot be resolved
- chosen output manifest path already exists and overwrite is not approved
- default scenario file would overwrite an existing file without approval

### 7.2 Soft Warnings
- route file cannot be detected from `.sumocfg`
- no `.add.xml` file found
- scene file not configured
- measurements not configured
- imported SUMO assets are outside the project root
- starter receivers are auto-generated placeholders only

## 8. Recommended Implementation Order

### Phase A: Controller and File Generation
- add `create_project(...)` to `ProjectController`
- add `import_sumo_project(...)` to `ProjectController`
- add helper for generating `project.toml`
- add helper for generating starter `baseline.toml`
- add helper for copying or referencing SUMO files

### Phase B: GUI Entry UX
- add `New Project` and `Import SUMO Project` buttons to Project Home
- add a simple project creation/import dialog
- show validation summary before final confirmation

### Phase C: Post-Creation UX
- automatically load the created/imported project
- if SUMO is missing, disable run actions and show attach-SUMO guidance
- if receivers were auto-generated, show a first-run note recommending receiver review in Scenario Editor

## 9. First Implementation Scope

Do first:
- `Import Existing SUMO Project`
- `Create New Project (with SUMO attached now)`
- generated `project.toml`
- generated `scenarios/baseline.toml`
- copied SUMO files into `data/sumo/`
- auto-open project in GUI

Defer:
- drag-and-drop SUMO import
- deeper scene/measurement import with schema-aware validation during the same wizard
- project templates beyond one baseline
- scene/measurement import wizard
- automatic receiver placement from scene rules more advanced than a safe placeholder layout

## 10. Why This Matters Now

This workflow removes the biggest current GUI limitation:
- today the GUI is effectively centered on the bundled `4lane` project
- after this work, a user can bring their own SUMO case into MTNsim without editing TOML files manually

This is the correct next step for turning the current GUI from a strong demo shell into a real project-based operator tool.
