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
    "sedan": {
        "mode": "wedge",
        "strength_db": 5.5,
        "wedge_angle_deg": 92.0,
        "vertical_strength_db": 1.5,
        "vertical_angle_deg": 68.0,
    },
    "suv": {
        "mode": "wedge",
        "strength_db": 6.5,
        "wedge_angle_deg": 88.0,
        "vertical_strength_db": 2.5,
        "vertical_angle_deg": 64.0,
    },
    "bus": {
        "mode": "dual_wedge",
        "strength_db": 7.5,
        "wedge_angle_deg": 105.0,
        "vertical_strength_db": 3.0,
        "vertical_angle_deg": 55.0,
    },
    "city_bus": {
        "mode": "dual_wedge",
        "strength_db": 7.8,
        "wedge_angle_deg": 112.0,
        "vertical_strength_db": 3.6,
        "vertical_angle_deg": 58.0,
    },
    "coach_bus": {
        "mode": "dual_wedge",
        "strength_db": 7.1,
        "wedge_angle_deg": 100.0,
        "vertical_strength_db": 2.8,
        "vertical_angle_deg": 52.0,
    },
    "truck": {
        "mode": "dual_wedge",
        "strength_db": 9.0,
        "wedge_angle_deg": 95.0,
        "vertical_strength_db": 4.0,
        "vertical_angle_deg": 50.0,
    },
    "delivery_truck": {
        "mode": "dual_wedge",
        "strength_db": 8.2,
        "wedge_angle_deg": 100.0,
        "vertical_strength_db": 3.5,
        "vertical_angle_deg": 52.0,
    },
    "heavy_truck": {
        "mode": "dual_wedge",
        "strength_db": 9.6,
        "wedge_angle_deg": 92.0,
        "vertical_strength_db": 4.6,
        "vertical_angle_deg": 48.0,
    },
}

DIRECTIVITY_PRESET_OPTIONS: Final[list[tuple[str, str]]] = [
    ("Custom", "custom"),
    ("Passenger (Legacy)", "passenger"),
    ("Sedan", "sedan"),
    ("SUV / Van", "suv"),
    ("Bus (Legacy)", "bus"),
    ("City Bus", "city_bus"),
    ("Coach Bus", "coach_bus"),
    ("Truck (Legacy)", "truck"),
    ("Delivery Truck", "delivery_truck"),
    ("Heavy Truck", "heavy_truck"),
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
