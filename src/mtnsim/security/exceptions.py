from __future__ import annotations


class ConfigValidationError(ValueError):
    """Raised when a user-provided configuration payload is malformed."""


class PathSecurityError(ConfigValidationError):
    """Raised when a configured path escapes its allowed sandbox."""
