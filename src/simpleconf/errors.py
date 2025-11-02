"""Exception types for the modern featherconf API."""
from __future__ import annotations

from .exceptions import FeatherConfError


class UnsupportedFormatError(FeatherConfError):
    """Raised when a configuration file format is not supported."""


class InterpolationError(FeatherConfError):
    """Raised when environment interpolation cannot resolve a placeholder."""


class ValidationError(FeatherConfError):
    """Raised when a user-supplied validator fails."""


__all__ = [
    "FeatherConfError",
    "UnsupportedFormatError",
    "InterpolationError",
    "ValidationError",
]
