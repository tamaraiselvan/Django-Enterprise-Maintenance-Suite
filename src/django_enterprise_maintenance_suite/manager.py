from django.db import models
from django.db.models.deletion import ProtectedError

class MaintenanceStateQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_enabled=True)

    def protected(self):
        return self.filter(
            status__in=[
                MaintenanceState.Status.APPROVED,
                MaintenanceState.Status.REJECTED,
                MaintenanceState.Status.ABORTED,
                MaintenanceState.Status.COMPLETED,
            ]
        )
        
    def delete(self, *args, **kwargs):

        if self.filter(status__in=self.protected()).exists():
            raise ProtectedError(
                "Maintenance windows that are approved, aborted, or completed cannot be deleted.",
                list(self[:1]),
            )

        return super().delete(*args, **kwargs)
