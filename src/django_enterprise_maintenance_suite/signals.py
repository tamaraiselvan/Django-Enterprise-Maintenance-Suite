from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from django_enterprise_maintenance_suite.models import MaintenanceState, MaintenanceIgnoreURL, MAINTENANCE_CACHE_KEY

@receiver([post_save, post_delete], sender=MaintenanceState)
@receiver([post_save, post_delete], sender=MaintenanceIgnoreURL)
def clear_maintenance_cache(**kwargs):
    cache.delete(MAINTENANCE_CACHE_KEY)