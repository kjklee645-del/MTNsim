# MTNsim

MTNsim is a microscopic traffic noise simulation prototype that combines SUMO-based vehicle motion, receiver/grid noise calculation, scenario comparison, calibration, and early scene-aware propagation logic.

The long-term product direction is a traffic-noise digital twin platform with richer 3D scene correction, calibration against measurements, reporting, and bounded AI-agent control through structured commands.

## Current Status

Implemented in the repository today:
- project manifest and scenario schema
- package-based application structure under `src/mtnsim`
- deterministic SUMO-backed execution with seeded scenario runs
- receiver time-series and final grid snapshot outputs
- run/result schema and scenario/result comparison services
- first-pass propagation split for distance, shielding, reflection, diffraction, and material-aware correction
- calibration with metadata mapping, auto time sync, and outlier rejection
- propagation benchmark, tuning, and multi-case validation suite workflows
- field-campaign inspection, quality checks, and markdown/JSON campaign reports
- campaign-aware validation that runs simulation, calibration, and threshold checks from a campaign manifest
- standardized campaign import contracts for traffic metadata and scene manifests

Supported example scenarios:
- `baseline`
- `speed_drop_80`
- `lane_change_enforce`
- `barrier_shielding`
- `building_shielding_default`
- `building_shielding`
- `terrain_ground_vegetation`
- `propagation_override_example`

## Repository Layout

- `src/mtnsim`: application packages
- `examples`: project manifest and scenario examples
- `schemas`: JSON schema definitions
- `data/sumo`: example SUMO network inputs
- `data/measurements`: measurement and seeded reference datasets
- `data/field`: field-campaign templates and demo packages
- `benchmarks`: propagation and validation benchmark suites
- `docs`: design, status, and usage notes
- `paper`: manuscript planning and draft text
- `scripts`: utility scripts such as reference-measurement generation

## User Guide

- Detailed usage: `docs/user_guide.md`

## Quick Start

Environment assumptions used during validation:
- Python: `C:\Users\user\miniconda3\envs\Trac\python.exe`
- workspace: `D:\Codex\MTNsim`

Set the source path:

```powershell
cd D:\Codex\MTNsim
$env:PYTHONPATH='D:\Codex\MTNsim\src'
```

Print the default project summary:

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

Inspect a field campaign package:

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --inspect-field-campaign --campaign-file 'D:\Codex\MTNsim\data\field\demo_seeded_campaign\campaign.json'
```

Run campaign-aware validation:

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --validate-field-campaign --campaign-file 'D:\Codex\MTNsim\data\field\demo_seeded_campaign\campaign.json' --cpu
```

## Current Implementation Notes

- When no shielding object is present, the engine can use the existing GPU path for free-field distance attenuation.
- When shielding objects are present, the current implementation falls back to CPU so shielding, reflection, diffraction, and material-aware corrections can be applied together.
- The current scene model supports `noise_barriers`, `terrain_edges`, `buildings`, `ground_surfaces`, and `vegetation_zones`. Building footprints are converted to edge segments for first-pass shielding evaluation, while ground and vegetation zones add path-based corrections.
- Validation now covers baseline reference measurements, shifted/outlier calibration recovery, speed control, barrier shielding, and building shielding default cases.
- A field-campaign inspection flow now checks campaign package completeness before real data is used for validation.
- The next major gap is not basic reproducibility anymore, but broader validation against richer field datasets and richer scene classes such as terrain and vegetation.

## Key Documents

- `MTNsim_product_direction.md`
- `MTNsim_PRD_draft.md`
- `MTNsim_package_architecture.md`
- `docs/current_status.md`
- `docs/development_checklist.md`
- `docs/user_guide.md`
- `docs/campaign_import_standard.md`
- `paper/manuscript_draft.md`

## Recommended Next Steps

1. Expand validation from seeded reference cases toward true field datasets and stronger acceptance rules.
2. Deepen calibration for field-facing alignment and correction workflows.
3. Continue scene/physics expansion for terrain, vegetation, and richer object classes.
4. Add reporting, GUI, and richer bounded agent control after the core engine is better validated.
