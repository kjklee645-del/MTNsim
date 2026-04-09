from __future__ import annotations

from collections.abc import Iterable, Sequence

from mtnsim.security.exceptions import ConfigValidationError


def ensure_non_empty_string(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ConfigValidationError(f"{label} must be a non-empty string.")


def ensure_member(value: str, allowed: Iterable[str], label: str) -> None:
    allowed_values = tuple(allowed)
    if value not in allowed_values:
        raise ConfigValidationError(f"{label} must be one of {allowed_values}.")


def ensure_positive_number(value: int | float, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ConfigValidationError(f"{label} must be greater than 0.")


def ensure_non_negative_number(value: int | float, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ConfigValidationError(f"{label} must be greater than or equal to 0.")


def ensure_ratio(value: int | float, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 or value > 1:
        raise ConfigValidationError(f"{label} must be between 0 and 1.")


def ensure_non_empty_sequence(values: Sequence[object], label: str) -> None:
    if not values:
        raise ConfigValidationError(f"{label} must not be empty.")


def ensure_same_length(first: Sequence[object], second: Sequence[object], label: str) -> None:
    if len(first) != len(second):
        raise ConfigValidationError(f"{label} must have matching lengths.")


def ensure_unique_strings(values: Iterable[str], label: str) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        raise ConfigValidationError(f"{label} contains duplicate values: {sorted(duplicates)}")
