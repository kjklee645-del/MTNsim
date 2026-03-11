# Field Campaign Validation Report: Demo Seeded Campaign

- Campaign ID: `demo_seeded_campaign`
- Project: `mtnsim-demo`
- Scenario: `baseline`
- Inspection passed: `True`
- Validation passed: `True`
- Simulation executed: `True`
- Inspection summary: `D:\Codex\MTNsim\data\field\demo_seeded_campaign\reports\campaign_inspection_summary.json`
- Inspection report: `D:\Codex\MTNsim\data\field\demo_seeded_campaign\reports\campaign_inspection_report.md`
- Result summary: `D:\Codex\MTNsim\outputs\cd2062d4e14d4cd69089f4be2b6002f4\run_result_summary.json`
- Calibration summary: `D:\Codex\MTNsim\outputs\cd2062d4e14d4cd69089f4be2b6002f4\calibration_summary.json`

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
- Overall mean bias (dB): `0.0`
- Overall RMSE (dB): `0.0`
- Unmatched sensor count: `0`
- Worst receiver: `poi_500_65`
- High-error receivers: `[]`

## Threshold Checks

- [x] `min_aligned_sample_count`: `{'passed': True, 'actual': 4800, 'expected_min': 4800}`
- [x] `max_overall_rmse_db`: `{'passed': True, 'actual': 0.0, 'expected_max': 1e-06}`
- [x] `max_abs_overall_mean_bias_db`: `{'passed': True, 'actual': 0.0, 'expected_max': 1e-06}`
- [x] `max_unmatched_sensor_count`: `{'passed': True, 'actual': 0, 'expected_max': 0}`
- [x] `min_coverage_ratio`: `{'passed': True, 'actual': 1.0, 'expected_min': 1.0}`
- [x] `max_receiver_rmse_db`: `{'passed': True, 'actual_failed_receivers': [], 'expected_max': 1e-06}`
- [x] `max_receiver_abs_mean_bias_db`: `{'passed': True, 'actual_failed_receivers': [], 'expected_max': 1e-06}`

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

## Next Action

- Campaign passed the current validation gate and can be used as a baseline comparison package.
