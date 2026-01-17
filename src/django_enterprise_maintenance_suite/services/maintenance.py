from django.db import transaction
from django.utils import timezone
from django_enterprise_maintenance_suite.models import MaintenanceState
from django_enterprise_maintenance_suite.services.exceptions import InvalidTransitionError
from django_enterprise_maintenance_suite.services.audit import log_action

class MaintenanceService:
    """
    Enterprise-grade service for maintenance lifecycle operations.
    """

    @staticmethod
    def approve(window: MaintenanceState, user, ip=None):
        if window.status != MaintenanceState.Status.PENDING:
            raise InvalidTransitionError(
                "Only PENDING maintenance windows can be approved."
            )

        with transaction.atomic():
            window.status = MaintenanceState.Status.APPROVED
            window.approved_by = user
            window.is_enabled = True
            window.save(update_fields=["status", "approved_by", "is_enabled"])

            log_action(
                actor=user,
                action="APPROVE",
                window=window,
                payload={"status": "APPROVED"},
                ip_address=ip,
            )

        return window

    @staticmethod
    def reject(window: MaintenanceState, user, ip=None):
        if window.status != MaintenanceState.Status.PENDING:
            raise InvalidTransitionError(
                "Only PENDING maintenance windows can be rejected."
            )

        with transaction.atomic():
            window.status = MaintenanceState.Status.REJECTED
            window.is_enabled = False
            window.save(update_fields=["status", "is_enabled"])

            log_action(
                actor=user,
                action="REJECT",
                window=window,
                payload={"status": "REJECTED"},
                ip_address=ip,
            )

        return window

    @staticmethod
    def enable(window: MaintenanceState, user):
        if window.status != MaintenanceState.Status.APPROVED:
            raise InvalidTransitionError(
                "Only APPROVED maintenance windows can be enabled."
            )

        with transaction.atomic():
            window.is_enabled = True
            window.save(update_fields=["is_enabled"])

        return window

    @staticmethod
    def disable(window: MaintenanceState, user):
        if not window.is_enabled:
            return window  # no-op

        with transaction.atomic():
            window.is_enabled = False
            window.save(update_fields=["is_enabled"])

        return window

    @staticmethod
    def abort(window: MaintenanceState, user, ip=None):
        if window.status != MaintenanceState.Status.APPROVED:
            raise InvalidTransitionError(
                "Only APPROVED maintenance windows can be aborted."
            )

        if not window.is_active:
            raise InvalidTransitionError(
                "Only ACTIVE maintenance windows can be aborted."
            )

        with transaction.atomic():
            window.status = MaintenanceState.Status.ABORTED
            window.is_enabled = False
            window.save(update_fields=["status", "is_enabled"])

            log_action(
                actor=user,
                action="ABORT",
                window=window,
                payload={"status": "ABORTED"},
                ip_address=ip,
            )

        return window

    @staticmethod
    def complete(window: MaintenanceState, user=None, ip=None):
        if window.status != MaintenanceState.Status.APPROVED:
            raise InvalidTransitionError(
                "Only APPROVED maintenance windows can be completed."
            )

        with transaction.atomic():
            window.status = MaintenanceState.Status.COMPLETED
            window.is_enabled = False
            window.end_time = window.end_time or timezone.now()
            window.save(update_fields=["status", "is_enabled", "end_time"])

            log_action(
                actor=user,
                action="COMPLETE",
                window=window,
                payload={"status": "COMPLETED"},
                ip_address=ip,
            )

        return window

