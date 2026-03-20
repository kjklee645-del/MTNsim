from __future__ import annotations

from typing import Final

DIRECTIVITY_PRESETS: Final[dict[str, dict[str, float | str]]] = {
    "custom": {
        "mode": "isotropic",
        "strength_db": 6.0,
        "wedge_angle_deg": 70.0,
        "vertical_strength_db": 0.0,
        "vertical_angle_deg": 55.0,
    },
    "passenger": {
        "mode": "wedge",
        "strength_db": 6.0,
        "wedge_angle_deg": 85.0,
        "vertical_strength_db": 2.0,
        "vertical_angle_deg": 65.0,
    },
    "bus": {
        "mode": "dual_wedge",
        "strength_db": 7.5,
        "wedge_angle_deg": 105.0,
        "vertical_strength_db": 3.0,
        "vertical_angle_deg": 55.0,
    },
    "truck": {
        "mode": "dual_wedge",
        "strength_db": 9.0,
        "wedge_angle_deg": 95.0,
        "vertical_strength_db": 4.0,
        "vertical_angle_deg": 50.0,
    },
}

DIRECTIVITY_PRESET_OPTIONS: Final[list[tuple[str, str]]] = [
    ("Custom", "custom"),
    ("Passenger", "passenger"),
    ("Bus", "bus"),
    ("Truck", "truck"),
]


def get_directivity_preset_values(preset: str) -> dict[str, float | str]:
    key = preset if preset in DIRECTIVITY_PRESETS else "custom"
    return dict(DIRECTIVITY_PRESETS[key])


def infer_directivity_preset(
    mode: str,
    strength_db: float,
    wedge_angle_deg: float,
    vertical_strength_db: float,
    vertical_angle_deg: float,
) -> str:
    for preset, values in DIRECTIVITY_PRESETS.items():
        if preset == "custom":
            continue
        if str(values["mode"]) != str(mode):
            continue
        if abs(float(values["strength_db"]) - float(strength_db)) > 0.05:
            continue
        if abs(float(values["wedge_angle_deg"]) - float(wedge_angle_deg)) > 0.05:
            continue
        if abs(float(values["vertical_strength_db"]) - float(vertical_strength_db)) > 0.05:
            continue
        if abs(float(values["vertical_angle_deg"]) - float(vertical_angle_deg)) > 0.05:
            continue
        return preset
    return "custom"
