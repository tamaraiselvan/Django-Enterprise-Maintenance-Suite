from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django_enterprise_maintenance_suite.models import MaintenanceState, MaintenanceAuditLog, MaintenanceIgnoreURL
from django_enterprise_maintenance_suite.services.maintenance import MaintenanceService, InvalidTransitionError 

# Helper to create logs
def create_audit_log(user, action, window_obj, changes=None, ip=None):
    MaintenanceAuditLog.objects.create(
        actor=user,
        action=action,
        maintenance_window=window_obj,
        payload=changes or {},
        ip_address=ip
    )

class MaintenanceIgnoreURLInline(admin.TabularInline):
    model = MaintenanceIgnoreURL
    extra = 1
    fields = ('pattern', 'description')
    verbose_name = "Ignored URL Pattern"
    verbose_name_plural = "Ignored URL Patterns (Whitelist)"

@admin.register(MaintenanceAuditLog)
class MaintenanceAuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'actor', 'action', 'maintenance_window_link')
    readonly_fields = ('timestamp', 'actor', 'action', 'maintenance_window', 'window_snapshot', 'payload', 'ip_address')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
        
    def maintenance_window_link(self, obj):
        if obj.maintenance_window:
            return f"{obj.maintenance_window.get_mode_display()} ({obj.maintenance_window.id})"
        
        if obj.window_snapshot:
            return f"{obj.window_snapshot} (Deleted)"
            
        return "Deleted Window (No Snapshot)"

@admin.register(MaintenanceState)
class MaintenanceStateAdmin(admin.ModelAdmin):
    list_display = (
        'mode',
        'is_enabled',
        'start_time',
        'end_time',
        'created_by',
        'approved_by',
    )

    inlines = [MaintenanceIgnoreURLInline]
    list_filter = ('mode', 'status', 'is_enabled', 'approved_by')
    search_fields = ('mode', 'created_by__username', 'reason')

    readonly_fields = ('created_at', 'created_by', 'approved_by', 'status')

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)
        return actions

    actions = [
        'approve_maintenance',
        'reject_maintenance',
        'abort_maintenance',
        'complete_maintenance',
        'safe_delete_selected',
    ]

    @admin.action(description="Approve selected maintenance windows")
    def approve_maintenance(self, request, queryset):
        success, failed = 0, 0
        ip = request.META.get("REMOTE_ADDR")

        for obj in queryset:
            try:
                MaintenanceService.approve(obj, request.user, ip=ip)
                success += 1
            except InvalidTransitionError:
                failed += 1

        if success:
            self.message_user(
                request,
                f"Approved {success} maintenance window(s).",
                messages.SUCCESS,
            )
        if failed:
            self.message_user(
                request,
                f"{failed} window(s) could not be approved.",
                messages.ERROR,
            )
    
    @admin.action(description='Reject selected maintenance windows')
    def reject_maintenance(self, request, queryset):
        success, failed = 0, 0

        for obj in queryset:
            try:
                MaintenanceService.reject(obj, request.user)
                create_audit_log(request.user, "REJECT", obj)
                success += 1
            except InvalidTransitionError:
                failed += 1

        if success:
            self.message_user(
                request,
                f"Rejected {success} maintenance window(s).",
                messages.SUCCESS,
            )
        if failed:
            self.message_user(
                request,
                f"{failed} window(s) could not be rejected.",
                messages.ERROR,
            )
    
    @admin.action(description='Abort active maintenance windows')
    def abort_maintenance(self, request, queryset):
        success, failed = 0, 0

        for obj in queryset:
            try:
                MaintenanceService.abort(obj, request.user)
                create_audit_log(request.user, "ABORT", obj)
                success += 1
            except InvalidTransitionError:
                failed += 1

        if success:
            self.message_user(
                request,
                f"Aborted {success} maintenance window(s).",
                messages.WARNING,
            )
        if failed:
            self.message_user(
                request,
                f"{failed} window(s) could not be aborted.",
                messages.ERROR,
            )

    @admin.action(description='Mark maintenance windows as completed')
    def complete_maintenance(self, request, queryset):
        success, failed = 0, 0

        for obj in queryset:
            try:
                MaintenanceService.complete(obj)
                create_audit_log(request.user, "COMPLETE", obj)
                success += 1
            except InvalidTransitionError:
                failed += 1

        if success:
            self.message_user(
                request,
                f"Completed {success} maintenance window(s).",
                messages.SUCCESS,
            )
        if failed:
            self.message_user(
                request,
                f"{failed} window(s) could not be completed.",
                messages.ERROR,
            )

    @admin.action(description="Delete selected maintenance windows (safe)")
    def safe_delete_selected(self, request, queryset):
        try:
            deleted_count = queryset.count()
            queryset.delete()
            self.message_user(
                request,
                f"Successfully deleted {deleted_count} maintenance window(s).",
                messages.SUCCESS,
            )
        except ProtectedError as e:
            self.message_user(
                request,
                e.args[0],
                messages.ERROR,
            )



