from __future__ import annotations

import math

try:
    import torch
except ImportError:  # pragma: no cover
    torch = None


def free_field_attenuation_db(distance: float) -> float:
    distance = max(distance, 1e-6)
    return 11 + (20 * math.log10(distance))


def receiver_level_with_background(power_level_db: float, attenuation_db: float, correction_db: float, background_noise_db: float) -> float:
    source_power = 10 ** ((power_level_db - attenuation_db + correction_db) / 10)
    background_power = 10 ** (background_noise_db / 10)
    return 10 * math.log10(source_power + background_power)


def free_field_attenuation_torch_db(distances):
    if torch is None:
        raise RuntimeError('torch is required for torch-based attenuation')
    return 11 + (20 * torch.log10(distances + 1e-6))
