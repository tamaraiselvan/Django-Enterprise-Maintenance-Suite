from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django_enterprise_maintenance_suite.manager import MaintenanceStateQuerySet

MAINTENANCE_CACHE_KEY = "active_maintenance_window"

class MaintenanceStateManager(models.Manager.from_queryset(MaintenanceStateQuerySet)):
    pass

class MaintenanceState(models.Model):
    class Mode(models.TextChoices):
        MAINTENANCE = 'maintenance', _('Full Maintenance (503)')
        READ_ONLY = 'read_only', _('Read Only (No Writes)')

    class Status(models.TextChoices):
        PENDING = 'pending'
        APPROVED = 'approved'
        REJECTED = 'rejected'
        ABORTED = 'aborted'
        COMPLETED = 'completed'
    objects = MaintenanceStateManager()
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.MAINTENANCE)
    reason = models.TextField(help_text="Why is this maintenance required?")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="maintenance_approvals"
    )
    is_enabled = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.start_time and self.end_time and self.start_time > self.end_time:
            raise ValidationError(_("End time must be after start time."))

        if self.is_enabled and self.status != self.Status.APPROVED:
            raise ValidationError(_("Only APPROVED maintenance windows can be enabled."))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        status = "ENABLED" if self.is_enabled else "DISABLED"
        return f"{self.get_mode_display()} - {status} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    def delete(self, *args, **kwargs):
        if self.status in (
            self.Status.APPROVED,
            self.Status.REJECTED,
        ):
            raise ProtectedError(
                "Approved or rejected maintenance windows cannot be deleted.",
                [self],
            )
        super().delete(*args, **kwargs)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Maintenance Window"
        indexes = [
            models.Index(fields=['is_enabled', 'status', '-created_at']),
        ]
        permissions = [
            ("can_approve_maintenance", "Can approve maintenance requests"),
        ]

class MaintenanceAuditLog(models.Model):
    """
    Immutable log of all maintenance state changes.
    """
    ACTION_CHOICES = [
        ('CREATE', 'Created Window'),
        ('UPDATE', 'Updated Window'),
        ('APPROVE', 'Approved Window'),
        ('REJECT', 'Rejected Window'),
        ('DELETE', 'Deleted Window'),
    ]

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        help_text="User who performed the action"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    maintenance_window = models.ForeignKey(
        MaintenanceState, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name="audit_logs"
    )
    window_snapshot = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Permanent snapshot of the window details (preserved after deletion)"
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    payload = models.JSONField(default=dict, help_text="Snapshot of the changes")
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Audit Log"

    def save(self, *args, **kwargs):
        if not self.window_snapshot and self.maintenance_window:
            self.window_snapshot = str(self.maintenance_window)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.actor} - {self.action} @ {self.timestamp}"

class MaintenanceIgnoreURL(models.Model):
    """
    Specific URL patterns to exempt from a maintenance window.
    """
    maintenance_window = models.ForeignKey(
        MaintenanceState, 
        on_delete=models.CASCADE, 
        related_name='exceptions'
    )
    pattern = models.CharField(
        max_length=255, 
        help_text="Regex pattern to ignore (e.g., ^/api/health/). Leading slash optional."
    )
    description = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Why is this ignored? (e.g., 'Stripe Webhook')"
    )

    def __str__(self):
        return self.pattern
