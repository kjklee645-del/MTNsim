# MTNsim Campaign Import Standard

Date: 2026-03-11
Purpose: define the standard file contract for field campaign packages so real-world datasets can be imported and checked consistently.

## 1. Standard Campaign Folder

Recommended structure:
- `campaign.json`
- `measurements.csv`
- `sensor_metadata.csv`
- `traffic.csv`
- `traffic_metadata.json`
- `scene/scene_manifest.json`
- `scene/...` geometry files
- `notes.md`
- `reports/` generated outputs

## 2. Campaign Manifest Fields

Required:
- `campaign_id`
- `name`
- `measurement_file`
- `sensor_metadata_file`

Recommended:
- `traffic_file`
- `traffic_metadata_file`
- `scene_path`
- `scene_manifest_file`
- `scenario_file`
- `expected_time_zone`
- `coordinate_system`
- `validation_thresholds`

## 3. Measurement CSV Standard

Minimum required columns:
- `sensor_id` or `receiver_id`
- one time column: `time_index`, `timestamp`, or `time_seconds`
- `value_db`

Recommended columns:
- `quality_flag`
- `aggregation_type`

## 4. Sensor Metadata CSV Standard

Minimum required columns:
- `sensor_id`
- `simulation_receiver_id` or `x`, `y`, `z`

Recommended columns:
- `enabled`
- `time_offset_steps`
- `start_time_index`
- `end_time_index`
- `installation_type`
- `orientation`

## 5. Traffic CSV Standard

Minimum required semantic fields:
- time column: `time_index`, `timestamp`, `time_seconds`, or `interval_start`
- flow column: `traffic_volume`, `vehicle_count`, or `flow_veh_per_hour`
- speed column: `average_speed_kmh`, `speed_kmh`, or `mean_speed_kmh`

Recommended fields:
- `heavy_vehicle_share`
- `lane_id`
- `segment_id`
- `queue_state`

## 6. Traffic Metadata JSON Standard

Recommended fields:
- `time_zone`
- `time_column`
- `speed_unit`
- `flow_unit`
- `sampling_interval_seconds`
- `data_type`

## 7. Scene Manifest Standard

Required top-level fields:
- `coordinate_system`
- `layers`

Recommended layer keys:
- `buildings`
- `barriers`
- `terrain`
- `ground_surfaces`
- `vegetation`

Each layer should point to a file inside or relative to the scene bundle.

## 8. Validation Threshold Hints

Useful campaign-level validation thresholds now supported in `campaign.json`:
- `min_aligned_sample_count`
- `min_coverage_ratio`
- `min_receiver_coverage_ratio`
- `max_overall_rmse_db`
- `max_abs_overall_mean_bias_db`
- `max_receiver_rmse_db`
- `max_receiver_abs_mean_bias_db`
- `max_worst_receiver_rmse_db`
- `max_outlier_rejected_sample_count`
- `max_outlier_rejection_ratio`
- `max_abs_effective_time_offset_steps`

These are meant to express acceptance gates before a campaign is treated as validation-grade input.

## 9. Current Inspector Behavior

The current `--inspect-field-campaign` flow checks:
- required measurement columns
- duplicate sensor/time keys
- metadata mapping coverage
- traffic minimum columns
- traffic metadata core fields
- scene manifest structure
- referenced scene files existence
- time-zone and coordinate-system consistency with the campaign manifest

## 10. Intentional Scope

This standard does not yet force one GIS format or one coordinate system.
It standardizes the metadata contract first, so real datasets can vary in format while still being machine-checkable.
