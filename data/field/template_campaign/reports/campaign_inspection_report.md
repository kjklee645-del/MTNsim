# Field Campaign Inspection Report: Template Campaign

- Campaign ID: `template_campaign`
- Overall status: `False`
- Measurement file: `D:\Codex\MTNsim\data\field\template_campaign\measurements.csv`
- Sensor metadata file: `D:\Codex\MTNsim\data\field\template_campaign\sensor_metadata.csv`
- Traffic file: `D:\Codex\MTNsim\data\field\template_campaign\traffic.csv`
- Traffic metadata file: `D:\Codex\MTNsim\data\field\template_campaign\traffic_metadata.json`
- Scene path: `D:\Codex\MTNsim\data\field\template_campaign\scene`
- Scene manifest file: `D:\Codex\MTNsim\data\field\template_campaign\scene\scene_manifest.json`
- Notes file: `D:\Codex\MTNsim\data\field\template_campaign\notes.md`

## Summary

- Measurement row count: `0`
- Measurement sensor count: `0`
- Metadata sensor count: `0`
- Traffic row count: `0`
- Expected time zone: `Asia/Seoul`
- Coordinate system: `EPSG:5186`

## Checks

- [ ] `measurement_required_columns` (error): Measurements need sensor, time, and value columns.
  details: `{"columns": []}`
- [ ] `measurement_preferred_time_column_present` (warning): Measurement file should include the preferred time column declared in the campaign manifest.
  details: `{"preferred_time_column": "timestamp", "columns": []}`
- [ ] `measurement_rows_present` (error): Measurement file should contain at least one row.
  details: `{"row_count": 0}`
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
- [ ] `metadata_required_columns` (error): Metadata should include sensor_id and either simulation_receiver_id or x/y/z coordinates.
  details: `{"columns": []}`
- [ ] `metadata_rows_present` (error): Sensor metadata should contain at least one row.
  details: `{"row_count": 0}`
- [x] `metadata_duplicate_sensor_ids` (error): Sensor metadata should not contain duplicate sensor IDs.
  details: `{"duplicate_sensor_id_count": 0}`
- [x] `metadata_mapping_available` (error): Each metadata row should map to a receiver or coordinates.
  details: `{"missing_mapping_count": 0}`
- [ ] `traffic_rows_present` (warning): Traffic file should contain at least one row.
  details: `{"row_count": 0}`
- [ ] `traffic_minimum_columns` (warning): Traffic file should include time, flow, and speed information.
  details: `{"columns": []}`
- [ ] `traffic_heavy_vehicle_share_column` (warning): Traffic file should include heavy-vehicle share if available.
  details: `{"columns": []}`
- [x] `traffic_metadata_required_fields` (warning): Traffic metadata should include time_zone, time_column, and speed_unit.
  details: `{"keys": ["data_type", "flow_unit", "sampling_interval_seconds", "speed_unit", "time_column", "time_zone"]}`
- [x] `traffic_metadata_expected_time_zone` (warning): Traffic metadata time zone should match the campaign manifest.
  details: `{"expected_time_zone": "Asia/Seoul", "actual_time_zone": "Asia/Seoul"}`
- [x] `scene_path_exists` (warning): scene_path_exists should point to an existing dir.
  details: `{"path": "D:\\Codex\\MTNsim\\data\\field\\template_campaign\\scene"}`
- [x] `scene_manifest_required_fields` (warning): Scene manifest should include coordinate_system and layers.
  details: `{"keys": ["coordinate_system", "layers", "notes"]}`
- [x] `scene_manifest_coordinate_system_match` (warning): Scene manifest coordinate system should match the campaign manifest.
  details: `{"expected_coordinate_system": "EPSG:5186", "actual_coordinate_system": "EPSG:5186"}`
- [x] `scene_manifest_has_relevant_layer` (warning): Scene manifest should reference at least one relevant scene layer.
  details: `{"layer_keys": ["barriers", "buildings", "ground_surfaces", "terrain", "vegetation"]}`
- [x] `scene_manifest_layer_files_exist` (warning): Scene manifest referenced files should exist inside or relative to the scene bundle.
  details: `{"missing_files": []}`
- [x] `notes_file_exists` (warning): notes_file_exists should point to an existing file.
  details: `{"path": "D:\\Codex\\MTNsim\\data\\field\\template_campaign\\notes.md"}`
- [x] `measurement_sensors_mapped_in_metadata` (error): All measurement sensor IDs should exist in sensor metadata.
  details: `{"missing_sensor_ids": []}`

## Next Action

- Fix failed `error` checks before treating this campaign as validation-grade data.
