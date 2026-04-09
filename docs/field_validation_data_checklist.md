# MTNsim Field Validation Data Checklist

Date: 2026-03-11
Purpose: define the minimum and recommended field-data package required to move MTNsim from seeded reference validation toward real-world validation.

## 1. Minimum Validation Package

The minimum usable package for one field-validation session is:
- `2-5` receiver or sensor locations
- synchronized sound-level time series for each sensor
- sensor coordinates and installation height
- road geometry and surrounding obstacle geometry
- traffic-state data for the same time window
- measurement metadata describing time base and data quality

Without this minimum package, calibration can still be tested structurally, but model-vs-reality validation will remain weak.

## 2. Sensor Data Checklist

Required:
- sensor ID
- timestamp or discrete time index
- measured sound level in dB
- sampling interval or averaging interval
- unit convention if not standard `dB(A)`

Recommended:
- raw short-interval data such as `100 ms`, `1 s`, or another fixed interval
- equivalent aggregated metrics such as `LAeq`, `Lmax`, `L10`, `L90`
- sensor health or quality flags
- notes for missing periods or maintenance windows

Preferred file fields:
- `sensor_id`
- `timestamp` or `time_index`
- `value_db`
- `quality_flag`
- `aggregation_type`

## 3. Sensor Metadata Checklist

Required:
- sensor ID
- simulation receiver mapping or field coordinate
- `x, y, z` or equivalent GIS coordinate reference
- installation height above ground
- enabled/disabled status

Recommended:
- microphone orientation
- calibration date
- device model
- shielding or mounting notes such as facade mount, pole mount, rooftop, roadside
- valid measurement start and end times
- known clock offset if measured independently

## 4. Traffic Data Checklist

Preferred, highest quality:
- vehicle trajectories with time, position, speed, and class

Acceptable fallback:
- lane-level counts by time interval
- average speed by time interval
- vehicle class composition
- queue or congestion state annotations

Required minimum fields if trajectories are not available:
- timestamp or time interval
- traffic volume
- average speed
- heavy-vehicle share or vehicle type share

Recommended additions:
- lane occupancy
- acceleration or stop-start indicators
- incident or control-state annotations
- weather and pavement condition during measurement

## 5. Geometry and Scene Checklist

Required:
- road centerline or lane geometry
- receiver/sensor positions
- building footprints near the road
- barrier or wall geometry near the road

Recommended:
- building heights
- barrier heights and materials
- terrain elevation or contour data
- ground-surface type such as asphalt, concrete, soil, grass
- vegetation belts if acoustically relevant
- facade material or dominant surface description

Preferred import sources:
- GIS layers
- CAD exports
- surveyed coordinates
- drone or site-photo-assisted interpretation

## 6. Time Synchronization Checklist

Required:
- common time base across sensor and traffic data
- explicit time zone information
- clear start and end time of the usable interval

Recommended:
- clock drift estimate per device
- synchronization event or anchor point
- notes for daylight-saving or manual time corrections if applicable

## 7. Weather and Environmental Checklist

Recommended for serious validation:
- wind speed and direction
- temperature
- humidity
- precipitation state
- pavement wet/dry condition

These are not mandatory for the first field-validation round, but they become important once propagation accuracy is being tuned against reality.

## 8. Data Quality Checklist

Before using a field dataset, confirm:
- no duplicated timestamps
- no impossible dB values
- missing intervals are marked
- units are consistent
- sensor IDs are unique and stable
- receiver mapping is unambiguous
- coordinate system is documented

## 9. Recommended Pilot Campaign

For the first MTNsim field-validation campaign, target:
- one road segment
- one measurement day or one controlled time block
- `3` sensors at different setback distances
- `10-30` minutes of synchronized data
- one clear barrier/building condition
- one traffic control condition such as normal flow or speed-limited flow

This is enough to test:
- time alignment
- receiver mapping
- baseline bias
- distance decay consistency
- first-pass shielding behavior

## 10. Suggested Repository Staging

When real field data becomes available, stage it like this:
- `data/field/<campaign_name>/measurements.csv`
- `data/field/<campaign_name>/sensor_metadata.csv`
- `data/field/<campaign_name>/traffic.csv`
- `data/field/<campaign_name>/scene/`
- `data/field/<campaign_name>/notes.md`

## 11. Readiness Gate

A field dataset is ready for MTNsim validation when all of the following are true:
- sensor time series is present and readable
- sensor positions are mapped to simulation receivers or coordinates
- traffic data exists for the same time window
- geometry exists for the same road segment
- time base is documented
- basic quality checks have passed

If any of these fail, do not treat the dataset as a validation-grade dataset yet.
