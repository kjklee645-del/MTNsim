# MTNsim Field Validation Methodology

Date: 2026-03-11
Purpose: define the recommended methodology for validating MTNsim against real-world field measurements once a usable dataset is available.

## 1. Goal

The goal of field validation is not only to see whether MTNsim produces plausible noise levels, but to quantify:
- overall bias
- temporal alignment quality
- receiver-by-receiver fit
- whether propagation components such as shielding, reflection, and diffraction behave credibly in real conditions

## 2. Validation Philosophy

Validation should proceed in stages.

Stage A: structural validation
- verify file formats
- verify receiver mapping
- verify time alignment
- verify repeatable reruns

Stage B: baseline acoustic validation
- compare simulated and measured receiver time series
- quantify bias, MAE, RMSE, and sample coverage
- identify systematic underprediction or overprediction

Stage C: scene-sensitive validation
- test whether barriers, buildings, and distance trends are represented correctly
- compare near-field and far-field receivers separately
- inspect cases with clear shielding or reflection signatures

Stage D: calibration-informed validation
- apply controlled calibration adjustments
- rerun validation
- check whether improvement is stable across receivers rather than overfit to one point

## 3. Recommended Workflow

### Step 1. Freeze Inputs

Before calibration or tuning:
- freeze the scenario definition
- freeze geometry inputs
- freeze the traffic input source
- freeze the raw measurement files

This avoids tuning against moving targets.

### Step 2. Build Validation Scenario

Create or map:
- road geometry
- scene objects such as barriers and buildings
- receivers corresponding to sensor positions
- traffic inputs for the same time window

### Step 3. Run Uncalibrated Baseline

Run MTNsim without ad hoc manual tuning and collect:
- `run_result_summary.json`
- receiver time-series CSV files
- `calibration_summary.json`

This becomes the baseline comparison point.

### Step 4. Check Time Alignment

Use metadata or auto time sync to estimate offsets.
Confirm:
- overlap count is sufficient
- estimated offsets are physically plausible
- alignment does not depend on a tiny number of samples

### Step 5. Evaluate Error Metrics

Evaluate at minimum:
- overall mean bias in dB
- overall MAE in dB
- overall RMSE in dB
- receiver-level mean bias
- receiver-level RMSE
- aligned sample count
- unmatched sensor count
- outlier rejected sample count

### Step 6. Inspect Spatial Pattern

Do not rely only on one global RMSE.
Check whether:
- near receivers behave differently from far receivers
- shielded receivers are consistently biased
- one receiver dominates the total error
- geometry-sensitive receivers show physically reasonable trends

### Step 7. Apply Controlled Calibration

If calibration is needed, change only one category at a time:
- global offset
- time alignment parameters
- material parameters
- reflection/diffraction parameters
- scene-object properties

Avoid changing several physical assumptions simultaneously unless the baseline evidence is already clear.

### Step 8. Hold-Out Check

If multiple time windows or sites are available:
- tune on one subset
- validate on another subset

This is important to avoid overfitting calibration to one campaign.

## 4. Recommended Metrics

Core metrics:
- `mean_bias_db`
- `mae_db`
- `rmse_db`
- `aligned_sample_count`
- `coverage_ratio`

Recommended additional diagnostics:
- receiver rank-order consistency by mean level
- peak-event timing mismatch
- near/far receiver error split
- shielded/unshielded receiver error split
- declared receiver-group diagnostics (for example `near_field`, `far_field`, `shielded`, `unshielded`)

## 5. Acceptance Logic For Early Campaigns

Early field-validation acceptance does not need to be too strict, but it must be explicit.

Suggested first-pass acceptance rules:
- no unmatched sensors
- sufficient aligned samples at every validation receiver
- stable estimated time offsets
- no large systematic sign error across all receivers
- error reduction after calibration should be consistent, not isolated to one receiver only
- an explicit acceptance status should be recorded as `accepted`, `conditional`, or `rejected`

Exact numeric thresholds should be decided after the first real dataset is inspected.

## 6. Error Analysis Template

For each campaign, summarize:
- dataset description
- time window used
- number of receivers
- traffic input source quality
- geometry completeness
- baseline bias and RMSE
- calibrated bias and RMSE
- dominant failure modes
- next parameter or model changes to test

## 7. Failure Modes To Watch For

Common failure modes likely to appear:
- sensor clock mismatch
- receiver coordinate mismatch
- missing barrier or building geometry
- wrong height assumptions
- traffic data aggregated too coarsely
- reflection model helping one receiver while hurting another
- overfitted calibration that does not generalize to another time window

## 8. Experimental Design For The First Field Campaign

A practical first experiment should be small and interpretable.

Recommended design:
- one site
- one stable traffic condition window
- three or more receivers
- one clearly identifiable barrier or building effect
- enough duration to include both quiet and vehicle-event periods

Recommended comparisons:
- uncalibrated baseline vs measured
- time-synced baseline vs measured
- calibrated baseline vs measured
- receiver-by-receiver error table

## 9. Deliverables For Each Validation Campaign

Each campaign should produce:
- one frozen dataset folder
- one scenario file or scenario package
- one run result summary
- one calibration summary
- one validation report or markdown summary
- one list of accepted and rejected assumptions

## 10. How This Connects To MTNsim Development

The output of field validation should drive the next implementation priorities.

If baseline distance trend is wrong:
- revisit emission and distance-decay assumptions

If shielded receivers are wrong:
- improve scene geometry and shielding logic

If far receivers become worse when reflection is enabled:
- revisit reflection model and material assumptions

If alignment is unstable:
- deepen calibration and synchronization tooling

## 11. Recommended Next Actions Before Data Arrives

Before real field data is available, MTNsim should be prepared by:
- keeping the validation suite stable
- documenting field-data requirements clearly
- standardizing field-data folder structure
- preparing one campaign-ready import convention
- deciding which metrics will be reported by default

That way, once field data arrives, the project can move directly into validation rather than spending time inventing the process.
