from django.apps import AppConfig

class EnterpriseMaintenanceSuitConfig(AppConfig):
    name = "django_enterprise_maintenance_suite"
    verbose_name = "Enterprise Maintenance Suite"

    def ready(self):
        import django_enterprise_maintenance_suite.signals
