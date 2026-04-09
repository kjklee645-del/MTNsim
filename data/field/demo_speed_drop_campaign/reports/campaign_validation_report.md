# Field Campaign Validation Report: Demo Speed Drop Campaign

- Campaign ID: `demo_speed_drop_campaign`
- Project: `mtnsim-demo`
- Scenario: `speed_drop_80`
- Inspection passed: `True`
- Validation passed: `True`
- Simulation executed: `True`
- Inspection summary: `D:\Codex\MTNsim\data\field\demo_speed_drop_campaign\reports\campaign_inspection_summary.json`
- Inspection report: `D:\Codex\MTNsim\data\field\demo_speed_drop_campaign\reports\campaign_inspection_report.md`
- Result summary: `D:\Codex\MTNsim\outputs\b53d76d3b8604bd098f638151c3cd276\run_result_summary.json`
- Calibration summary: `D:\Codex\MTNsim\outputs\b53d76d3b8604bd098f638151c3cd276\calibration_summary.json`

## Acceptance Decision

- Acceptance status: `accepted`
- Acceptance reasons: `['All declared campaign validation checks passed.']`

## Campaign Description

Synthetic campaign package that reuses seeded speed-drop reference data for comparison workflow testing.

## Inspection Snapshot

- Measurement rows: `4800`
- Measurement sensors: `8`
- Metadata sensors: `8`
- Traffic rows: `3`

## Calibration Summary

- Aligned sample count: `4800`
- Coverage ratio: `1.0`
- Overall mean bias (dB): `0.0`
- Overall RMSE (dB): `0.0`
- Unmatched sensor count: `0`
- Outlier rejected sample count: `0`
- Outlier rejection ratio: `0.0`
- Max abs effective time offset (steps): `0`
- Recommended global offset (dB): `-0.0`
- Worst receiver: `poi_500_65`
- Worst receiver group: `near_field`
- High-error receivers: `[]`
- High-error receiver groups: `[]`
- Low-coverage receivers: `[]`
- Low-coverage receiver groups: `[]`
- Calibration high-priority receivers: `[]`
- Suggested sensor time-offset updates: `{}`

## Threshold Checks

- [x] `min_aligned_sample_count`: `{'passed': True, 'actual': 4800, 'expected_min': 4800}`
- [x] `max_overall_rmse_db`: `{'passed': True, 'actual': 0.0, 'expected_max': 1e-06}`
- [x] `max_abs_overall_mean_bias_db`: `{'passed': True, 'actual': 0.0, 'expected_max': 1e-06}`
- [x] `max_unmatched_sensor_count`: `{'passed': True, 'actual': 0, 'expected_max': 0}`
- [x] `min_coverage_ratio`: `{'passed': True, 'actual': 1.0, 'expected_min': 1.0}`
- [x] `min_receiver_coverage_ratio`: `{'passed': True, 'actual_failed_receivers': [], 'expected_min': 1.0}`
- [x] `max_receiver_rmse_db`: `{'passed': True, 'actual_failed_receivers': [], 'expected_max': 1e-06}`
- [x] `max_receiver_abs_mean_bias_db`: `{'passed': True, 'actual_failed_receivers': [], 'expected_max': 1e-06}`
- [x] `max_worst_receiver_rmse_db`: `{'passed': True, 'actual': 0.0, 'expected_max': 1e-06}`
- [x] `max_outlier_rejected_sample_count`: `{'passed': True, 'actual': 0, 'expected_max': 0}`
- [x] `max_outlier_rejection_ratio`: `{'passed': True, 'actual': 0.0, 'expected_max': 0.0}`
- [x] `max_abs_effective_time_offset_steps`: `{'passed': True, 'actual': 0, 'expected_max': 0}`
- [x] `min_receiver_group_coverage_ratio`: `{'passed': True, 'actual_failed_groups': [], 'expected_min': 1.0}`

## Receiver Diagnostics

| Receiver | Samples | Expected | Coverage | Mean Bias | MAE | RMSE | Rejected Outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `poi_500_115` | 600 | 600 | 1.000 | 0.000 | 0.000 | 0.000 | 0 |
| `poi_500_165` | 600 | 600 | 1.000 | 0.000 | 0.000 | 0.000 | 0 |
| `poi_500_215` | 600 | 600 | 1.000 | 0.000 | 0.000 | 0.000 | 0 |
| `poi_500_25` | 600 | 600 | 1.000 | 0.000 | 0.000 | 0.000 | 0 |
| `poi_500_35` | 600 | 600 | 1.000 | 0.000 | 0.000 | 0.000 | 0 |
| `poi_500_45` | 600 | 600 | 1.000 | 0.000 | 0.000 | 0.000 | 0 |
| `poi_500_55` | 600 | 600 | 1.000 | 0.000 | 0.000 | 0.000 | 0 |
| `poi_500_65` | 600 | 600 | 1.000 | 0.000 | 0.000 | 0.000 | 0 |

## Receiver Group Diagnostics

| Group | Receiver Count | Samples | Expected | Coverage | Mean Bias | MAE | RMSE | Rejected Outliers | Members |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `far_field` | 2 | 1200 | 1200 | 1.000 | 0.000 | 0.000 | 0.000 | 0 | `poi_500_165`, `poi_500_215` |
| `mid_field` | 2 | 1200 | 1200 | 1.000 | 0.000 | 0.000 | 0.000 | 0 | `poi_500_65`, `poi_500_115` |
| `near_field` | 4 | 2400 | 2400 | 1.000 | 0.000 | 0.000 | 0.000 | 0 | `poi_500_25`, `poi_500_35`, `poi_500_45`, `poi_500_55` |

## Comparison Insights

- Worst receiver is poi_500_65 with RMSE 0.000 dB and mean bias 0.000 dB.
- Worst receiver group is near_field with RMSE 0.000 dB and mean bias 0.000 dB.
- Near/far RMSE split: near_field 0.000 dB vs far_field 0.000 dB.
- Near/far mean-bias split: near_field 0.000 dB vs far_field 0.000 dB.

## Calibration Recommendations

- No calibration recommendations were generated.

## Next Action

- Freeze this campaign package as a reusable validation baseline.
