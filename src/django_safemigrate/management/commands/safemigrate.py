"""Hook into the migrate command to add safety.

Migration safety is enforced by a pre_migrate signal receiver.
"""
from enum import Enum

from django.conf import settings
from django.core.management.base import CommandError
from django.core.management.commands import migrate
from django.db.models.signals import pre_migrate
from django.utils import timezone
from django.utils.timesince import timeuntil

from django_safemigrate import Safe, SafeEnum


class SafeMigrate(Enum):
    strict = "strict"
    nonstrict = "nonstrict"
    disabled = "disabled"


def safety(migration):
    """Determine the safety status of a migration."""
    return getattr(migration, "safe", Safe.after_deploy())


def safemigrate():
    state = getattr(settings, "SAFEMIGRATE", None)
    if state is None:
        return state
    try:
        return SafeMigrate(state.lower())
    except ValueError as e:
        raise ValueError(
            "Invalid SAFEMIGRATE setting, it must be one of 'strict', 'nonstrict', or 'disabled'."
        ) from e


class Command(migrate.Command):
    """Run database migrations that are safe to run before deployment."""

    help = "Run database migrations that are safe to run before deployment."
    receiver_has_run = False

    def handle(self, *args, **options):
        # Only connect the handler when this command is run to
        # avoid running for tests.
        pre_migrate.connect(
            self.pre_migrate_receiver, dispatch_uid="django_safemigrate"
        )
        super().handle(*args, **options)

    def pre_migrate_receiver(self, *, plan, **_):
        """Handle the pre_migrate receiver for all apps."""
        if self.receiver_has_run:
            # Can't just look for the run for the current app,
            # because it only sends the signal to apps with models.
            return  # Only run once
        self.receiver_has_run = True

        safemigrate_state = safemigrate()
        if safemigrate_state == SafeMigrate.disabled:
            # When disabled, run migrate
            return

        # strict by default
        strict = safemigrate_state != SafeMigrate.nonstrict

        if any(backward for mig, backward in plan):
            raise CommandError("Backward migrations are not supported.")

        # Pull the migrations into a new list
        migrations = [migration for migration, backward in plan]

        # Check for invalid safe properties
        invalid = [
            migration
            for migration in migrations
            if not isinstance(safety(migration), Safe)
            or safety(migration).safe not in SafeEnum
        ]
        if invalid:
            self.stdout.write(self.style.MIGRATE_HEADING("Invalid migrations:"))
            for migration in invalid:
                self.stdout.write(f"  {migration.app_label}.{migration.name}")
            raise CommandError(
                "Aborting due to migrations with invalid safe properties."
            )

        protected = [
            migration
            for migration in migrations
            if safety(migration).safe == SafeEnum.after_deploy
        ]

        if not protected:
            return  # No migrations to protect.

        # Display the migrations that are protected
        self.stdout.write(self.style.MIGRATE_HEADING("Protected migrations:"))
        for migration in protected:
            self.stdout.write(f"  {migration.app_label}.{migration.name}")

        ready = [
            migration
            for migration in migrations
            if safety(migration).safe != SafeEnum.after_deploy
        ]
        delayed = []
        blocked = []

        while True:
            blockers = protected + delayed + blocked
            blockers_deps = [(m.app_label, m.name) for m in blockers]
            to_block_deps = [dep for mig in blockers for dep in mig.run_before]
            block = [
                migration
                for migration in ready
                if any(dep in blockers_deps for dep in migration.dependencies)
                or (migration.app_label, migration.name) in to_block_deps
            ]
            if not block:
                break

            for migration in block:
                ready.remove(migration)
                if safety(migration).safe == SafeEnum.before_deploy:
                    blocked.append(migration)
                else:
                    delayed.append(migration)

        # Order the migrations in the order of the original plan.
        delayed = [m for m in migrations if m in delayed]
        blocked = [m for m in migrations if m in blocked]

        self.delayed(delayed)
        self.blocked(blocked)

        if blocked and strict:
            raise CommandError("Aborting due to blocked migrations.")

        # Swap out the items in the plan with the safe migrations.
        # None are backward, so we can always set backward to False.
        plan[:] = [(migration, False) for migration in ready]

    def delayed(self, migrations):
        """Handle delayed migrations."""
        # Display delayed migrations if they exist:
        if migrations:
            self.stdout.write(self.style.MIGRATE_HEADING("Delayed migrations:"))
            for migration in migrations:
                migration_safe = safety(migration)
                if (
                    migration_safe.safe == SafeEnum.after_deploy
                    and migration_safe.delay is not None
                ):
                    now = timezone.localtime()
                    migrate_date = now + migration_safe.delay
                    humanized_date = timeuntil(migrate_date, now=now, depth=2)
                    self.stdout.write(
                        f"  {migration.app_label}.{migration.name} "
                        f"(can automatically migrate in {humanized_date} "
                        f"- {migrate_date.isoformat()})"
                    )
                else:
                    self.stdout.write(f"  {migration.app_label}.{migration.name}")

    def blocked(self, migrations):
        """Handle blocked migrations."""
        # Display blocked migrations if they exist.
        if migrations:
            self.stdout.write(self.style.MIGRATE_HEADING("Blocked migrations:"))
            for migration in migrations:
                self.stdout.write(f"  {migration.app_label}.{migration.name}")
