# MTNsim

MTNsim is a microscopic traffic noise simulation prototype that combines SUMO-based vehicle motion, receiver/grid noise calculation, scenario comparison, and early-stage shielding logic.

The long-term product direction is a traffic-noise digital twin platform with 3D scene correction, calibration against measurements, and bounded AI-agent control through structured commands.

## Current Status

Implemented today in the repository:
- project manifest and scenario schema
- package-based application structure under `src/mtnsim`
- SUMO adapter and scenario-driven execution pipeline
- receiver time-series and grid snapshot outputs
- run/result schema and scenario/result comparison services
- first-pass propagation split for distance, shielding, reflection, and diffraction modules
- first-pass shielding model for roadside barriers and building footprints

Supported example scenarios:
- `baseline`
- `speed_drop_80`
- `lane_change_enforce`
- `barrier_shielding`
- `building_shielding`

## Repository Layout

- `src/mtnsim`: application packages
- `examples`: project manifest and scenario examples
- `schemas`: JSON schema definitions
- `data/sumo`: example SUMO network inputs
- `docs`: internal design and progress notes

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

Compare scenario configuration only:

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --scenario 'D:\Codex\MTNsim\examples\scenarios\baseline.toml' --compare-scenario 'D:\Codex\MTNsim\examples\scenarios\speed_drop_80.toml'
```

Compare actual run results:

```powershell
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --scenario 'D:\Codex\MTNsim\examples\scenarios\baseline.toml' --compare-scenario 'D:\Codex\MTNsim\examples\scenarios\building_shielding.toml' --run --cpu
```

## Current Implementation Notes

- When no shielding object is present, the engine can use the existing GPU path for free-field distance attenuation.
- When shielding objects are present, the current implementation falls back to CPU so the shielding correction can be applied.
- The current scene model supports `noise_barriers` and `buildings`. Building footprints are converted to edge segments for first-pass shielding evaluation.
- Reflection, diffraction, calibration, GUI, and full AI-agent control are not implemented yet.

## Key Documents

- `MTNsim_product_direction.md`
- `MTNsim_PRD_draft.md`
- `MTNsim_package_architecture.md`
- `docs/current_status.md`
- `docs/progress_review_against_plan.md`

## Recommended Next Steps

1. Clarify the scene-object hierarchy further.
2. Add material-aware propagation properties on top of the scene hierarchy.
3. Expand propagation beyond shielding into usable reflection and diffraction logic.
4. Add calibration workflow and benchmark validation.
5. Deepen bounded command interfaces for future AI-agent control.