import re
from django.conf import settings
from django.urls import reverse, NoReverseMatch
from django.core.cache import cache
from django.utils import timezone
from django_enterprise_maintenance_suite.models import MaintenanceState, MAINTENANCE_CACHE_KEY

class DefaultMaintenanceBackend:
    def __init__(self):
        self.conf = getattr(settings, 'MAINTENANCE_SUITE', {})
        self.global_ignore_patterns = [
            re.compile(p.lstrip('/')) 
            for p in self.conf.get('IGNORE_URL_PATTERNS', [])
        ]

    def get_maintenance_window(self, request):
        """
        Determines if there is an active maintenance window for this request.
        Returns the MaintenanceState object or None.
        """
        # 1. Global Ignores (Static/Health)
        path = request.path_info.lstrip('/')
        for pattern in self.global_ignore_patterns:
            if pattern.match(path):
                return None

        # 2. Admin & Status API Check
        if self._is_admin_or_status(request):
            return None

        # 3. Fetch State (Cache -> DB)
        current_state = cache.get(MAINTENANCE_CACHE_KEY)
        if current_state is None:
            try:
                current_state = MaintenanceState.objects.filter(
                    is_enabled=True,
                    status=MaintenanceState.Status.APPROVED
                ).order_by('-created_at').prefetch_related('exceptions').first()
                cache.set(MAINTENANCE_CACHE_KEY, current_state, timeout=3600)
            except Exception:
                return None

        if not current_state:
            return None

        # 4. Schedule & Expiry Check
        now = timezone.now()
        if current_state.start_time and now < current_state.start_time:
            return None
        if current_state.end_time and now > current_state.end_time:
            return None

        # 5. Per-Window URL Exceptions
        for exception in current_state.exceptions.all():
            if re.match(exception.pattern.lstrip('/'), path):
                return None

        return current_state

    def is_write_method(self, request):
        """
        Decides if a request is considered a 'Write' operation.
        Customizable via settings.
        """
        allowed_methods = self.conf.get('READ_ONLY_ALLOWED_METHODS', ['GET', 'HEAD', 'OPTIONS'])
        return request.method not in allowed_methods

    def _is_admin_or_status(self, request):
        """Helper to identify internal safe URLs"""
        admin_url_name = self.conf.get('ADMIN_URL_NAME', 'admin:index')
        try:
            admin_path = reverse(admin_url_name)
            if request.path.startswith(admin_path):
                return True
            if request.path == reverse('maintenance_status'):
                return True
        except NoReverseMatch:
            pass
        return False