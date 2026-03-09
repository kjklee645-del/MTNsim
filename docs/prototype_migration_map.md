# Prototype Migration Map

Source prototype:
- `D:/test/MTN/00_MTN_V1_5_속도변화실험.py`

## Function mapping

- `add_T_grid_cell` -> `mtnsim.scene.grid.GridDomain.add_cell`
- `set_grid_area_from_network` -> `mtnsim.scene.grid.read_network_bounds`
- `update_poi_values` -> `mtnsim.acoustics.field.noise_grid.update_noise_grid_cpu`
- `update_poi_values_GPU` -> `mtnsim.acoustics.field.noise_grid.update_noise_grid_gpu`
- `calculate_3d_distance` -> `mtnsim.acoustics.emission.road_vehicle.calculate_3d_distance`
- `poi_history` -> `mtnsim.io.result_store.write_receiver_history`
- `enforce_lane_change` -> `mtnsim.traffic.vehicle_controls.enforce_lane_change`
- `restore_vehicle_speeds` -> `mtnsim.traffic.vehicle_controls.restore_vehicle_speeds`
- `apply_speed_after_distance` -> `mtnsim.traffic.vehicle_controls.apply_speed_after_distance`
- `disable_lane_change` -> `mtnsim.traffic.vehicle_controls.disable_lane_change`
- `add_vehicle` -> `mtnsim.traffic.vehicle_controls.add_vehicle`

## Current extraction order

1. schema and manifest layer
2. scene/grid utilities
3. traffic control utilities
4. acoustic update engine
5. result storage
6. orchestration service

## Important note

The current prototype is a single-run experimental script. The new structure separates:
- configuration
- domain logic
- engine orchestration
- outputs
- future AI control surface
