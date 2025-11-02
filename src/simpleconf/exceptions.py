class FeatherConfError(RuntimeError):
    """Base exception for FeatherConf errors."""


class ConfigNotFoundError(FeatherConfError):
    """Raised when no configuration files could be located."""

