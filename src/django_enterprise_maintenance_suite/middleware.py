from django.conf import settings
from django.utils.module_loading import import_string
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.template import TemplateDoesNotExist
from django.db import transaction
from django_enterprise_maintenance_suite.models import MaintenanceState

class MaintenanceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
        # 1. Load the Backend Class dynamically from settings
        conf = getattr(settings, 'MAINTENANCE_SUITE', {})
        backend_path = conf.get(
            'BACKEND', 
            'enterprise_maintenance_suit.backends.DefaultMaintenanceBackend'
        )
        self.backend = import_string(backend_path)()

    def __call__(self, request):
        # Ask the backend: "Is there an active window for this request?"
        current_state = self.backend.get_maintenance_window(request)

        if not current_state:
            return self.get_response(request)

        # --- MODE: MAINTENANCE (503) ---
        if current_state.mode == MaintenanceState.Mode.MAINTENANCE:
            if request.headers.get('Accept') == 'application/json':
                 return JsonResponse({
                     "error": "Service Unavailable", 
                     "reason": current_state.reason
                 }, status=503)
            
            # (Rendering logic remains here as it's view-layer concern)
            template_name = getattr(settings, 'MAINTENANCE_SUITE', {}).get('MAINTENANCE_TEMPLATE', 'enterprise_maintenance_suit/503.html')
            try:
                return render(request, template_name, {'state': current_state}, status=503)
            except TemplateDoesNotExist:
                return HttpResponse(f"<h1>Service Unavailable</h1><p>{current_state.reason}</p>", status=503)

        # --- MODE: READ_ONLY ---
        if current_state.mode == MaintenanceState.Mode.READ_ONLY:
            
            # Ask the backend: "Is this a write method?"
            if self.backend.is_write_method(request):
                 return JsonResponse({
                     "error": "Read Only Mode", 
                     "detail": "Write requests are blocked."
                 }, status=403)

            # Strict Transaction Rollback
            try:
                with transaction.atomic():
                    response = self.get_response(request)
                    transaction.set_rollback(True)
                    response['X-Maintenance-Mode'] = 'Read-Only-Strict'
                    return response
            except Exception:
                raise

        return self.get_response(request)