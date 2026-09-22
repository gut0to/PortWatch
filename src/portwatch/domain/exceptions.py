class InvalidPortError(ValueError):
    """Raised when a port or port range is invalid."""


class PortNotFoundError(LookupError):
    """Raised when a requested port is not listening."""


class PermissionDeniedError(PermissionError):
    """Raised when process information cannot be accessed."""


class ProcessTerminationError(RuntimeError):
    """Raised when a process could not be terminated."""
