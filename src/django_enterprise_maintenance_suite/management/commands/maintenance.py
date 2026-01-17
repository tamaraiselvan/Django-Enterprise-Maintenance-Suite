import sys
from django.core.management.base import BaseCommand
from django.core.management import CommandError
from django.utils import timezone
from django.contrib.auth import get_user_model
from django_enterprise_maintenance_suite.models import MaintenanceState
from django_enterprise_maintenance_suite.services.maintenance import MaintenanceService
from django_enterprise_maintenance_suite.services.exceptions import InvalidTransitionError

User = get_user_model()


class Command(BaseCommand):
    help = "Manage system maintenance windows (enterprise-safe, service-driven)"

    # ------------------------------------------------------------------
    # ARGUMENTS
    # ------------------------------------------------------------------

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="action", required=True)

        # STATUS
        subparsers.add_parser(
            "status",
            help="Show current real-time maintenance status",
        )

        # ENABLE
        enable = subparsers.add_parser(
            "enable",
            help="Enable a new maintenance window",
        )
        enable.add_argument(
            "--actor",
            required=True,
            help="Username performing this action (audit & governance)",
        )
        enable.add_argument(
            "--mode",
            choices=[choice[0] for choice in MaintenanceState.Mode.choices],
            default=MaintenanceState.Mode.MAINTENANCE,
            help="Maintenance mode to activate",
        )
        enable.add_argument(
            "--reason",
            default="System Maintenance (CLI)",
            help="Reason displayed to users",
        )
        enable.add_argument(
            "--minutes",
            type=int,
            help="Auto-expire after X minutes (safety net)",
        )
        enable.add_argument(
            "--force",
            action="store_true",
            help="Override existing active maintenance",
        )

        # DISABLE
        disable = subparsers.add_parser(
            "disable",
            help="Disable all active maintenance windows",
        )
        disable.add_argument(
            "--actor",
            required=True,
            help="Username performing this action (audit & governance)",
        )

    # ------------------------------------------------------------------
    # ENTRY POINT
    # ------------------------------------------------------------------

    def handle(self, *args, **options):
        action = options["action"]

        if action == "status":
            self.handle_status()
        elif action == "enable":
            self.handle_enable(options)
        elif action == "disable":
            self.handle_disable(options)

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def get_actor(self, username):
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(
                f"User '{username}' does not exist. "
                "Create the user or pass a valid username."
            )

    # ------------------------------------------------------------------
    # STATUS
    # ------------------------------------------------------------------

    def handle_status(self):
        active = (
            MaintenanceState.objects
            .filter(
                is_enabled=True,
                status=MaintenanceState.Status.APPROVED,
            )
            .order_by("-created_at")
            .first()
        )

        if active and active.is_enabled:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  SYSTEM STATUS: {active.get_mode_display().upper()}"
                )
            )
            self.stdout.write(f"Reason: {active.reason}")
            self.stdout.write(f"Window ID: {active.id}")
            if active.end_time:
                self.stdout.write(f"Expires at: {active.end_time}")
            sys.exit(1)

        self.stdout.write(self.style.SUCCESS("SYSTEM STATUS: OPERATIONAL"))
        sys.exit(0)

    # ------------------------------------------------------------------
    # ENABLE
    # ------------------------------------------------------------------

    def handle_enable(self, options):
        actor = self.get_actor(options["actor"])

        active_exists = MaintenanceState.objects.filter(
            is_enabled=True,
            status=MaintenanceState.Status.APPROVED,
        ).exists()

        if active_exists and not options["force"]:
            self.stdout.write(
                self.style.ERROR(
                    "Maintenance already active. Use --force to override."
                )
            )
            sys.exit(2)

        end_time = None
        if options.get("minutes"):
            end_time = timezone.now() + timezone.timedelta(
                minutes=options["minutes"]
            )

        window = MaintenanceState.objects.create(
            mode=options["mode"],
            reason=options["reason"],
            start_time=timezone.now(),
            end_time=end_time,
            created_by=actor,
        )

        try:
            MaintenanceService.approve(
                window,
                user=actor,
                ip="127.0.0.1",
            )
        except InvalidTransitionError as exc:
            self.stdout.write(self.style.ERROR(str(exc)))
            sys.exit(3)

        self.stdout.write(
            self.style.SUCCESS(
                f"Maintenance ENABLED by '{actor.username}' "
                f"({options['mode']})"
            )
        )
        self.stdout.write(f"Reason: {options['reason']}")
        if end_time:
            self.stdout.write(f"Auto-expires at: {end_time}")

        sys.exit(0)

    # ------------------------------------------------------------------
    # DISABLE
    # ------------------------------------------------------------------

    def handle_disable(self, options):
        actor = self.get_actor(options["actor"])

        active_windows = MaintenanceState.objects.filter(
            is_enabled=True,
            status=MaintenanceState.Status.APPROVED,
        )

        if not active_windows.exists():
            self.stdout.write(
                self.style.WARNING("No active maintenance windows found.")
            )
            sys.exit(0)

        success = 0
        failed = 0

        for window in active_windows:
            try:
                MaintenanceService.complete(
                    window,
                    user=actor,
                    ip="127.0.0.1",
                )
                success += 1
            except InvalidTransitionError:
                failed += 1

        if success:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Maintenance DISABLED by '{actor.username}'. "
                    f"{success} window(s) closed."
                )
            )
        if failed:
            self.stdout.write(
                self.style.ERROR(
                    f"{failed} window(s) could not be closed cleanly."
                )
            )

        sys.exit(0 if failed == 0 else 4)
