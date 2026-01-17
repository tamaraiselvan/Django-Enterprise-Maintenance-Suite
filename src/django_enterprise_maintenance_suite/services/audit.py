from django_enterprise_maintenance_suite.models import MaintenanceAuditLog

def log_action(
    *,
    actor,
    action,
    window,
    payload=None,
    ip_address=None,):
    """
    Centralized audit logging for maintenance operations.
    """
    MaintenanceAuditLog.objects.create(
        actor=actor,
        action=action,
        maintenance_window=window,
        payload=payload or {},
        ip_address=ip_address,
    )
