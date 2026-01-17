from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET
from django_enterprise_maintenance_suite.models import MaintenanceState

@require_GET
@cache_control(max_age=60, public=True)
def maintenance_status_view(request):
    """
    Public endpoint to check system health.
    Returns 200 OK with JSON describing the current state.
    """
    # 1. Check for active, approved maintenance
    active = MaintenanceState.objects.filter(
        is_enabled=True,
        status=MaintenanceState.Status.APPROVED
    ).order_by('-created_at').first()

    data = {
        "system_status": "operational",
        "timestamp": timezone.now().isoformat(),
        "maintenance_window": None
    }

    # 2. Validation Logic (Must match Middleware logic)
    if active:
        now = timezone.now()
        start_ok = not active.start_time or now >= active.start_time
        end_ok = not active.end_time or now <= active.end_time
        
        if start_ok and end_ok:
            data["system_status"] = active.mode
            data["maintenance_window"] = {
                "reason": active.reason,
                "start_time": active.start_time,
                "end_time": active.end_time,
                "expected_duration_remaining": None 
            }
            
            # Optional: Calculate remaining time for UI countdowns
            if active.end_time:
                remaining = (active.end_time - now).total_seconds()
                if remaining > 0:
                    data["maintenance_window"]["expected_duration_remaining"] = remaining

    return JsonResponse(data)