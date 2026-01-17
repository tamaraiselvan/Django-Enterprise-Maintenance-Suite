class MaintenanceError(Exception):
    """Base exception for maintenance operations."""


class InvalidTransitionError(MaintenanceError):
    pass


class PermissionDeniedError(MaintenanceError):
    pass
