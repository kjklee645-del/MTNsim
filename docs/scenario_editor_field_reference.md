# Scenario Editor Field Reference

## Purpose

This document explains the fields currently exposed in the MTNsim `Scenario Editor` GUI.
The editor does not expose every schema field. It focuses on high-value scenario controls that a general user is likely to adjust first.

## Live Preview

When current values pass editor validation, the editor automatically updates the main `Scenario Details` panel and `Scene View` without saving. This preview is unsaved and temporary. Heatmap overlays are cleared during preview so saved run outputs are not confused with edited geometry.

## Scenario

### Scenario Name
- Meaning: the internal scenario identifier shown in the GUI and used in run summaries.
- Effect: helps distinguish derived scenarios after `Save As`.

### Description
- Meaning: short human-readable description of the scenario.
- Effect: documentation only; does not change simulation physics.

## Traffic

### Max Vehicles
- Schema field: `traffic.max_vehicles`
- Meaning: maximum number of vehicles inserted during the simulation.
- Typical use: increase or decrease demand intensity.
- Higher value usually means: denser traffic and potentially higher noise levels.

### Start Speed
- Schema field: `traffic.start_speed_kmh`
- Meaning: initial vehicle speed when vehicles are introduced.
- Typical use: compare free-flow versus slower-entry scenarios.

### Vehicle Interval
- Schema field: `traffic.vehicle_interval_seconds`
- Meaning: time interval between vehicle insertions in interval-based traffic generation.
- Lower value means: more vehicles enter more frequently.

## Controls

### Post Distance
- Schema field: `controls.post_distance_meters`
- Meaning: downstream distance where post-distance speed logic is applied.
- Typical use: model speed management after a threshold location.

### Post Target Speed
- Schema field: `controls.post_target_speed_kmh`
- Meaning: target speed after the post-distance condition becomes active.
- Typical use: speed-drop or speed-control scenarios.

### Lane Change Mode
- Schema field: `controls.lane_change_mode`
- Meaning: whether lane-change intervention is disabled or enforced.
- Current GUI values:
  - `disable`: no explicit lane-change enforcement
  - `enforce`: force the configured lane-change behavior

### Lane Change Strategy
- Schema field: `controls.lane_change_strategy`
- Meaning: strategy label used by the traffic control logic.
- Current GUI value:
  - `custom`

### Post Control
- Schema field: `controls.post_distance_speed_control`
- Meaning: enable or disable the post-distance speed-control logic entirely.
- If unchecked: post-distance target speed is ignored.

### Lane Change Force
- Schema field: `controls.lane_change_force_change`
- Meaning: whether the lane-change action should be forced once the condition is reached.

## Noise

### Background Noise
- Schema field: `noise.background_noise_db`
- Meaning: ambient baseline noise level added to the simulation context.
- Typical use: represent non-traffic background conditions.

### Max Area
- Schema field: `noise.max_area_meters`
- Meaning: maximum spatial extent used around the source/receiver domain for noise-grid evaluation.
- Larger values can increase spatial coverage and runtime cost.

### Grid Size
- Schema field: `noise.grid_size_meters`
- Meaning: grid cell size used for noise-map discretization.
- Smaller values mean: finer heatmap resolution, more cells, and heavier computation.

### Receiver Height
- Schema field: `noise.receiver_height_meters`
- Meaning: default height used for receiver evaluation.
- Typical use: represent ear height or a measurement instrument height.

## Grid

### Grid Margin Start
- Schema field: `grid.margin_x_start`
- Meaning: upstream margin added before the main road region when building the analysis grid.

### Grid Margin End
- Schema field: `grid.margin_x_end`
- Meaning: downstream margin added after the main road region when building the analysis grid.

### Grid Extra Y
- Schema field: `grid.extra_y_extent`
- Meaning: extra lateral extent added to the analysis grid.
- Typical use: widen the receiver/noise-map domain away from the road.

## Receivers Table

The `Receivers` table edits multiple receiver points directly.
Each row corresponds to one `[[receivers]]` entry in the scenario TOML.

### ID
- Schema field: `receivers[].id`
- Meaning: unique receiver identifier.
- Used in result files, charts, comparisons, and validation reports.

### X
- Schema field: `receivers[].x`
- Meaning: receiver X coordinate in scenario space.

### Y
- Schema field: `receivers[].y`
- Meaning: receiver Y coordinate in scenario space.

### Z
- Schema field: `receivers[].z`
- Meaning: receiver elevation / height.

### Add Receiver
- Meaning: append a new receiver row with default values.
- Recommended follow-up: rename the `ID` and set realistic coordinates before saving.

### Remove Selected
- Meaning: remove one or more selected receiver rows from the derived scenario.
- Caution: removed receivers will not appear in later outputs, comparisons, or validation mappings for that scenario.

## Save As Behavior

### Save As New Scenario
- Meaning: write a new TOML scenario file instead of overwriting the source scenario.
- Current behavior:
  - updates the GUI scenario list
  - selects the new scenario
  - opens the comparison view against the source scenario

## Recommended Usage Pattern

1. Start from a stable baseline scenario.
2. Change only a few fields at a time.
3. Use `Save As New Scenario`.
4. Review the automatic comparison view.
5. Run the new scenario only after confirming the intended changes.

## Validation Rules

The current editor blocks `Save As New Scenario` when any of the following checks fail.

- Scenario name must not be empty.
- Grid size must be greater than `0`.
- Max area must be greater than or equal to grid size.
- If `Post Control` is enabled, `Post Distance` must be greater than `0`.
- Receiver height must not be negative.
- At least one receiver row must exist.
- Every receiver row must have a non-empty `ID`.
- Receiver IDs must be unique.
- Receiver `X/Y/Z` values must be numeric.
- Receiver `Z` must not be negative.

When validation fails:
- the scenario is not saved
- the editor stays open
- a warning dialog is shown
- the status line displays the first validation error
