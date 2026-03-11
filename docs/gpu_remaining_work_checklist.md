# MTNsim GPU Remaining Work Checklist

Last updated: 2026-03-11
Purpose: track what remains to move from the current hybrid GPU path to a fuller scene-aware GPU execution path.

Status legend:
- `[x]` done
- `[~]` in progress or partially done
- `[ ]` not started

## 1. Current GPU Baseline

| Area | Item | Status | Notes |
| --- | --- | --- | --- |
| Free-field GPU | Distance attenuation + power accumulation on GPU | [x] | active in `acoustics/field/noise_grid.py` |
| Scene-aware GPU | Hybrid scene-aware GPU path | [x] | provider computes corrections, GPU handles attenuation and accumulation |
| Accuracy check | Reduced-size CPU vs GPU consistency check | [x] | matched within about `2.6e-6 dB` |
| Full-run check | Full-size scene-aware GPU run | [x] | `terrain_ground_vegetation` now records `used_gpu = true` |

## 2. Remaining GPU Work

| Priority | Work item | Status | Why it still matters |
| --- | --- | --- | --- |
| 1 | Tensorize shielding context generation | [ ] | current shielding context is still assembled in the provider, not inside a tensor kernel |
| 2 | Tensorize reflection context generation | [ ] | current reflection context still depends on provider-side geometry logic |
| 3 | Tensorize diffraction context generation | [ ] | current diffraction context still depends on provider-side geometry logic |
| 4 | Tensorize ground-surface correction | [ ] | ground effect is still provider-side path logic |
| 5 | Tensorize vegetation attenuation | [ ] | vegetation effect is still provider-side path logic |
| 6 | Reduce provider dependency in hybrid GPU path | [~] | broad-phase tensor-ready candidate scan exists, but correction assembly still uses Python/provider logic |
| 7 | Add scene-aware GPU performance benchmark suite | [ ] | correctness exists, but performance regression tracking is not formalized |
| 8 | Add CPU vs GPU regression suite for multiple scene scenarios | [~] | one reduced-size terrain case validated; broader scenario coverage still needed |

## 3. What Is Not Urgent Right Now

The following is intentionally not the current top product priority:

- full tensorized scene-aware GPU execution
- end-to-end provider removal
- large-scale GPU micro-optimization before more field validation exists

Reason:
- the current hybrid GPU path is already usable
- scene-aware full runs complete successfully
- reduced-size CPU/GPU agreement is already strong
- validation, calibration, and physics expansion now provide higher product value per unit work

## 4. Recommended GPU Follow-up Order

1. expand CPU/GPU regression coverage to more scene scenarios
2. add performance benchmark reporting for scene-aware runs
3. tensorize shielding context generation
4. tensorize reflection/diffraction context generation
5. tensorize ground/vegetation correction paths
6. only then consider deeper kernel fusion or provider removal

## 5. Decision Rule

Prioritize more GPU work only if one of the following becomes true:

- scenario size grows enough that hybrid GPU becomes the new bottleneck
- batch experiment throughput becomes a major requirement
- GUI or AI-agent workflows require much faster repeated reruns
- field-validation campaigns need repeated large-scale scenario sweeps
