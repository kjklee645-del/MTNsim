# Field Campaign Validation Report: Demo Seeded Campaign

- Campaign ID: `demo_seeded_campaign`
- Project: `mtnsim-demo`
- Scenario: `baseline`
- Inspection passed: `True`
- Validation passed: `False`
- Simulation executed: `True`
- Inspection summary: `D:\Codex\MTNsim\data\field\demo_seeded_campaign\reports\campaign_inspection_summary.json`
- Inspection report: `D:\Codex\MTNsim\data\field\demo_seeded_campaign\reports\campaign_inspection_report.md`
- Result summary: `D:\Codex\MTNsim\outputs\2cc19feadf78471c9d2d75aba83146d6\run_result_summary.json`
- Calibration summary: `D:\Codex\MTNsim\outputs\2cc19feadf78471c9d2d75aba83146d6\calibration_summary.json`

## Acceptance Decision

- Acceptance status: `conditional`
- Acceptance reasons: `['Failed validation check: max_overall_rmse_db', 'Failed validation check: max_abs_overall_mean_bias_db', 'Failed validation check: max_receiver_rmse_db', 'Failed validation check: max_receiver_abs_mean_bias_db', 'Failed validation check: max_worst_receiver_rmse_db']`

## Campaign Description

Synthetic campaign package that reuses seeded MTNsim reference data for workflow testing.

## Inspection Snapshot

- Measurement rows: `4800`
- Measurement sensors: `8`
- Metadata sensors: `8`
- Traffic rows: `3`

## Calibration Summary

- Aligned sample count: `4800`
- Coverage ratio: `1.0`
- Overall mean bias (dB): `0.030021278000172694`
- Overall RMSE (dB): `0.045506492461568133`
- Unmatched sensor count: `0`
- Outlier rejected sample count: `0`
- Outlier rejection ratio: `0.0`
- Max abs effective time offset (steps): `0`
- Recommended global offset (dB): `-0.030021278000172694`
- Worst receiver: `poi_500_215`
- Worst receiver group: `far_field`
- High-error receivers: `['poi_500_215', 'poi_500_165', 'poi_500_115', 'poi_500_65', 'poi_500_55', 'poi_500_45', 'poi_500_35', 'poi_500_25']`
- High-error receiver groups: `[]`
- Low-coverage receivers: `[]`
- Low-coverage receiver groups: `[]`
- Calibration high-priority receivers: `[]`
- Suggested sensor time-offset updates: `{}`

## Threshold Checks

- [x] `min_aligned_sample_count`: `{'passed': True, 'actual': 4800, 'expected_min': 4800}`
- [ ] `max_overall_rmse_db`: `{'passed': False, 'actual': 0.045506492461568133, 'expected_max': 1e-06}`
- [ ] `max_abs_overall_mean_bias_db`: `{'passed': False, 'actual': 0.030021278000172694, 'expected_max': 1e-06}`
- [x] `max_unmatched_sensor_count`: `{'passed': True, 'actual': 0, 'expected_max': 0}`
- [x] `min_coverage_ratio`: `{'passed': True, 'actual': 1.0, 'expected_min': 1.0}`
- [x] `min_receiver_coverage_ratio`: `{'passed': True, 'actual_failed_receivers': [], 'expected_min': 1.0}`
- [ ] `max_receiver_rmse_db`: `{'passed': False, 'actual_failed_receivers': ['poi_500_215', 'poi_500_165', 'poi_500_115', 'poi_500_65', 'poi_500_55', 'poi_500_45', 'poi_500_35', 'poi_500_25'], 'expected_max': 1e-06}`
- [ ] `max_receiver_abs_mean_bias_db`: `{'passed': False, 'actual_failed_receivers': ['poi_500_215', 'poi_500_165', 'poi_500_115', 'poi_500_65', 'poi_500_55', 'poi_500_45', 'poi_500_35', 'poi_500_25'], 'expected_max': 1e-06}`
- [ ] `max_worst_receiver_rmse_db`: `{'passed': False, 'actual': 0.08191882501541355, 'expected_max': 1e-06}`
- [x] `max_outlier_rejected_sample_count`: `{'passed': True, 'actual': 0, 'expected_max': 0}`
- [x] `max_outlier_rejection_ratio`: `{'passed': True, 'actual': 0.0, 'expected_max': 0.0}`
- [x] `max_abs_effective_time_offset_steps`: `{'passed': True, 'actual': 0, 'expected_max': 0}`
- [x] `min_receiver_group_coverage_ratio`: `{'passed': True, 'actual_failed_groups': [], 'expected_min': 1.0}`

## Receiver Diagnostics

| Receiver | Samples | Expected | Coverage | Mean Bias | MAE | RMSE | Rejected Outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `poi_500_215` | 600 | 600 | 1.000 | 0.075 | 0.075 | 0.082 | 0 |
| `poi_500_165` | 600 | 600 | 1.000 | 0.052 | 0.052 | 0.060 | 0 |
| `poi_500_115` | 600 | 600 | 1.000 | 0.035 | 0.035 | 0.044 | 0 |
| `poi_500_65` | 600 | 600 | 1.000 | 0.020 | 0.020 | 0.032 | 0 |
| `poi_500_55` | 600 | 600 | 1.000 | 0.018 | 0.018 | 0.030 | 0 |
| `poi_500_45` | 600 | 600 | 1.000 | 0.015 | 0.015 | 0.029 | 0 |
| `poi_500_35` | 600 | 600 | 1.000 | 0.013 | 0.013 | 0.028 | 0 |
| `poi_500_25` | 600 | 600 | 1.000 | 0.012 | 0.012 | 0.027 | 0 |

## Receiver Group Diagnostics

| Group | Receiver Count | Samples | Expected | Coverage | Mean Bias | MAE | RMSE | Rejected Outliers | Members |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `far_field` | 2 | 1200 | 1200 | 1.000 | 0.064 | 0.064 | 0.072 | 0 | `poi_500_165`, `poi_500_215` |
| `mid_field` | 2 | 1200 | 1200 | 1.000 | 0.027 | 0.027 | 0.039 | 0 | `poi_500_65`, `poi_500_115` |
| `near_field` | 4 | 2400 | 2400 | 1.000 | 0.015 | 0.015 | 0.029 | 0 | `poi_500_25`, `poi_500_35`, `poi_500_45`, `poi_500_55` |

## Comparison Insights

- Worst receiver is poi_500_215 with RMSE 0.082 dB and mean bias 0.075 dB.
- Worst receiver group is far_field with RMSE 0.072 dB and mean bias 0.064 dB.
- Near/far RMSE split: near_field 0.029 dB vs far_field 0.072 dB.
- Near/far mean-bias split: near_field 0.015 dB vs far_field 0.064 dB.

## Calibration Recommendations

- No calibration recommendations were generated.

## Next Action

- Inspect geometry, traffic inputs, and local scene assumptions for the highest-error receivers or groups.
