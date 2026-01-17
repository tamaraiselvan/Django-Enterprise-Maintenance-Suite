from django.apps import AppConfig

class EnterpriseMaintenanceSuitConfig(AppConfig):
    name = "enterprise_maintenance_suit"
    verbose_name = "Enterprise Maintenance Suite"

    def ready(self):
        import enterprise_maintenance_suit.signals
