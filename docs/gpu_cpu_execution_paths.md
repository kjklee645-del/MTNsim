# GPU CPU Execution Paths

Date: 2026-03-11
Purpose: clarify which parts of MTNsim currently use GPU, which paths still fall back to CPU, and what should be migrated next.

## 1. Current Execution Split

| Area | Current path | GPU used now | Notes |
| --- | --- | --- | --- |
| Free-field distance attenuation | `update_noise_grid_gpu` | Yes | Used when no shielding/scene-aware propagation objects are active. |
| Basic receiver/grid accumulation | `update_noise_grid_gpu` | Yes | GPU path currently handles distance-based attenuation only. |
| Shielding with barriers/buildings | `update_noise_grid_cpu` | No | CPU fallback because shielding context is built per vehicle-POI pair in Python. |
| Reflection correction | `update_noise_grid_cpu` | No | Active only through the scene-aware propagation provider. |
| Diffraction correction | `update_noise_grid_cpu` | No | Active only through the scene-aware propagation provider. |
| Material-aware correction | `update_noise_grid_cpu` | No | Depends on shielding/reflection/diffraction contexts. |
| Terrain-edge correction | `update_noise_grid_cpu` | No | Implemented through shielding-style terrain edge segments. |
| Ground-surface correction | `update_noise_grid_cpu` | No | Path-based polygon coverage check is CPU only. |
| Vegetation-zone correction | `update_noise_grid_cpu` | No | Path-based polygon coverage check is CPU only. |

## 2. Current Switch Logic

Effective behavior in `RunService` today:

| Condition | Result |
| --- | --- |
| No shielding segments and `use_gpu=True` | GPU path can be used |
| Any shielding segment exists (`noise_barrier`, `building`, `terrain_edge`) | CPU fallback |
| Ground/vegetation scene effects active | CPU-only propagation provider still required |

In practice this means:
- `baseline`-style free-field runs can use GPU.
- `barrier_shielding`, `building_shielding`, and `terrain_ground_vegetation` currently run on CPU.

## 3. Why CPU Fallback Happens

Current blockers for scene-aware GPU execution:
- shielding context is generated per vehicle and per POI using Python geometry checks
- reflection and diffraction depend on that per-pair context
- ground and vegetation corrections currently use polygon path-coverage sampling on CPU
- material-aware corrections depend on the CPU-built propagation context

## 4. What Should Move To GPU Next

Recommended migration order:

| Priority | Computation | Why |
| --- | --- | --- |
| 1 | Shielding segment intersection and line-of-sight blocking | This is the main gate that disables GPU for barriers/buildings/terrain edges. |
| 2 | Reflection and diffraction context evaluation | These are downstream of shielding and must move with it to avoid mixed-path overhead. |
| 3 | Material-aware correction application | Once contexts are vectorized, material correction becomes a lightweight tensor step. |
| 4 | Ground-surface path checks | Needed to make terrain-aware scene effects feasible at larger scales. |
| 5 | Vegetation-zone path checks | Similar to ground surfaces, but can follow the same scene-mask strategy. |

## 5. Suggested GPU Strategy

A practical next strategy is:
1. precompute scene masks or compact scene arrays from `SceneModel`
2. vectorize `vehicle x POI x segment` blocking tests
3. compute reflection/diffraction gains from the same vectorized context
4. add tensor-based ground/vegetation correction masks
5. keep CPU as a correctness reference path during migration

## 6. Current Bottom Line

Current state:
- GPU is already used for simple free-field runs.
- GPU is not yet used for scene-aware propagation.
- scene-aware accuracy work is now ahead of scene-aware performance work.

So the next optimization goal is not ?introduce GPU from scratch,? but ?extend GPU coverage from free-field propagation to scene-aware propagation.?
