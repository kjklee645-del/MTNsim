# Directional Emission Expansion Plan

Date: 2026-03-19
Purpose: define the first implementation path that connects the new 3D source-field visualization concepts to actual MTNsim acoustic calculation.

## 1. Current State

Current MTNsim acoustic calculation is still effectively close to an isotropic point-source model:
- vehicle emission level is computed from speed and vehicle type
- distance attenuation is applied
- shielding, reflection, diffraction, and material-aware correction are applied
- the radiated source itself is not yet strongly directional in the engine

The 3D GUI already supports source-field visualization overlays for the selected playback vehicle:
- `off`
- `sphere`
- `wedge`
- `dual_wedge`

At the moment those overlays are primarily visualization aids.

## 2. Goal

The next acoustic step is to make source-field directionality affect the actual dB calculation.
That means the vehicle should not radiate equally in all directions.

Prototype goal for Phase A:
- keep the existing engine architecture intact
- add a simple directional gain/loss term before propagation correction
- use vehicle heading plus target angle to modulate source emission
- support the same basic mode names already visible in the 3D GUI

## 3. Phase A Scope

Phase A includes:
- scenario-level directional emission settings
- actual engine-side `isotropic / wedge / dual_wedge` handling
- heading estimation from frame-to-frame vehicle motion
- directivity-aware receiver and grid updates
- directivity-aware dynamic playback heatmap recomputation
- first-pass Scenario Editor support for the new settings

Phase A does not include:
- full 3D acoustic physics rewrite
- source-type decomposition such as tire / engine / exhaust components
- per-vehicle-class calibrated field datasets
- regulatory-grade directional source standards

The tire / engine / exhaust split is intentionally deferred until dedicated measurement experiments define a more trustworthy subsource model.

## 4. Proposed Calculation Rule

For Phase A, directivity is implemented as an emission-side directional adjustment:

`effective_source_level = base_source_level + directional_gain_db`

Where:
- `base_source_level` comes from the current vehicle speed coefficients
- `directional_gain_db` depends on
  - vehicle heading
  - angle between heading and target direction
  - selected directivity mode
  - directivity strength
  - wedge angle

Conservative rule for Phase A:
- preferred directions stay at `0 dB`
- non-preferred directions are attenuated by up to `-strength_db`
- this avoids artificially increasing total emitted energy in the first pass

## 5. First Supported Modes

### Isotropic
- same as current behavior
- no directional attenuation

### Wedge
- strongest in the forward lobe
- gradually reduced outside the wedge
- good first approximation for a forward-biased visualization/analysis mode

### Dual Wedge
- strongest in forward and rear lobes
- side radiation reduced
- useful as a first proxy for more complex traffic-noise source patterns

## 6. Required Code Touch Points

Engine-side:
- `src/mtnsim/acoustics/emission/road_vehicle.py`
- `src/mtnsim/acoustics/field/noise_grid.py`
- `src/mtnsim/services/run_service.py`
- `src/mtnsim/gui/controllers/result_controller.py`

Schema/config:
- `src/mtnsim/schemas/scenario.py`
- `schemas/scenario.schema.json`

GUI exposure:
- `src/mtnsim/gui/views/scenario_editor.py`
- `src/mtnsim/gui/controllers/project_controller.py`
- `src/mtnsim/gui/main_window.py`

Documentation:
- `docs/current_status.md`
- `docs/development_checklist.md`
- `docs/user_guide.md`
- `docs/scenario_editor_field_reference.md`

## 7. Validation Rule For Phase A

Phase A should be considered implemented when all of the following are true:
- a scenario can select `isotropic`, `wedge`, or `dual_wedge`
- a forward receiver and a rear receiver at equal distance no longer necessarily receive the same dB
- `wedge` produces stronger forward than rear/side values
- `dual_wedge` produces stronger front/rear than side values
- dynamic playback heatmap recomputation uses the same directivity rule
- result metadata records the chosen directivity settings

## 8. Phase 2 Extension

Phase 2 now adds a first-pass vertical directivity term:
- `vertical_strength_db`
- `vertical_angle_deg`
- actual calculation-side attenuation for targets outside the preferred vertical spread
- calc-linked 3D source-field overlays that reuse the same vertical spread settings for overlay height and receiver highlighting, differentiate receiver-interaction style by directivity preset, and now gate receiver highlighting through the actual directional-gain calculation

## 9. After Phase 2

Natural next steps after this implementation are:
- add more shapes such as ellipsoid or cone-like variants
- split emission into tire / engine / exhaust subcomponents
- calibrate source directivity parameters against measured data
- align 3D source-field overlays even more closely with the actual calculation model


## Presets

Phase 2 now includes user-facing presets to make directional emission easier to adopt in project setup and scenario editing. Current presets cover both legacy broad classes and finer vehicle groups: `custom`, `passenger`, `sedan`, `suv`, `bus`, `city_bus`, `coach_bus`, `truck`, `delivery_truck`, and `heavy_truck`.


Phase 2 metadata polish: run outputs now expose the directivity preset and target vehicle types so calc-linked 3D source fields can show the same context explicitly.


- Directional emission now supports `response_profile = physical | enhanced`; `enhanced` increases directional contrast so 2D heatmaps show clearer anisotropy.
