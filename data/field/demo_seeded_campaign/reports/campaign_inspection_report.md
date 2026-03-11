# Field Campaign Inspection Report: Demo Seeded Campaign

- Campaign ID: `demo_seeded_campaign`
- Overall status: `True`
- Measurement file: `D:\Codex\MTNsim\data\field\demo_seeded_campaign\..\..\measurements\baseline_reference_measurements.csv`
- Sensor metadata file: `D:\Codex\MTNsim\data\field\demo_seeded_campaign\sensor_metadata.csv`
- Traffic file: `D:\Codex\MTNsim\data\field\demo_seeded_campaign\traffic.csv`
- Scene path: `D:\Codex\MTNsim\data\field\demo_seeded_campaign\scene`
- Notes file: `D:\Codex\MTNsim\data\field\demo_seeded_campaign\notes.md`

## Summary

- Measurement row count: `4800`
- Measurement sensor count: `8`
- Metadata sensor count: `8`
- Traffic row count: `3`

## Checks

- [x] `measurement_required_columns` (error): Measurements need sensor, time, and value columns.
  details: `{"columns": ["receiver_id", "sensor_id", "time_index", "value_db"]}`
- [x] `measurement_rows_present` (error): Measurement file should contain at least one row.
  details: `{"row_count": 4800}`
- [x] `measurement_duplicate_sensor_time_keys` (error): Measurement file should not contain duplicate sensor/time pairs.
  details: `{"duplicate_key_count": 0}`
- [x] `measurement_missing_sensor_ids` (error): Measurement rows should include sensor identifiers.
  details: `{"missing_sensor_count": 0}`
- [x] `measurement_missing_time_values` (error): Measurement rows should include time values.
  details: `{"missing_time_count": 0}`
- [x] `measurement_missing_value_db` (error): Measurement rows should include dB values.
  details: `{"missing_value_count": 0}`
- [x] `measurement_plausible_db_range` (warning): Measurement dB values should stay in a plausible range.
  details: `{"impossible_db_count": 0}`
- [x] `metadata_required_columns` (error): Metadata should include sensor_id and either simulation_receiver_id or x/y/z coordinates.
  details: `{"columns": ["enabled", "sensor_id", "simulation_receiver_id"]}`
- [x] `metadata_rows_present` (error): Sensor metadata should contain at least one row.
  details: `{"row_count": 8}`
- [x] `metadata_duplicate_sensor_ids` (error): Sensor metadata should not contain duplicate sensor IDs.
  details: `{"duplicate_sensor_id_count": 0}`
- [x] `metadata_mapping_available` (error): Each metadata row should map to a receiver or coordinates.
  details: `{"missing_mapping_count": 0}`
- [x] `traffic_rows_present` (warning): Traffic file should contain at least one row.
  details: `{"row_count": 3}`
- [x] `traffic_minimum_columns` (warning): Traffic file should include time, flow, and speed information.
  details: `{"columns": ["average_speed_kmh", "heavy_vehicle_share", "time_index", "traffic_volume"]}`
- [x] `scene_path_exists` (warning): scene_path_exists should point to an existing dir.
  details: `{"path": "D:\\Codex\\MTNsim\\data\\field\\demo_seeded_campaign\\scene"}`
- [x] `notes_file_exists` (warning): notes_file_exists should point to an existing file.
  details: `{"path": "D:\\Codex\\MTNsim\\data\\field\\demo_seeded_campaign\\notes.md"}`
- [x] `measurement_sensors_mapped_in_metadata` (error): All measurement sensor IDs should exist in sensor metadata.
  details: `{"missing_sensor_ids": []}`

## Next Action

- Campaign package passes the current structural checks and is ready for simulation-side validation work.
