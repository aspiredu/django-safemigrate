"""Hook into the migrate command to add safety.

Migration safety is enforced by a pre_migrate signal receiver.
"""
from django.conf import settings
from django.db.models.signals import pre_migrate
from django.core.management.base import CommandError
from django.core.management.commands import migrate


class Command(migrate.Command):
    """Run safe database migrations."""

    help = "Run safe database migrations."
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
            return  # Only run once.
        self.receiver_has_run = True

        # strict by default
        strict = getattr(settings, "SAFEMIGRATE", None) != "nonstrict"

        if any(backward for mig, backward in plan):
            raise CommandError("Backward migrations are not supported.")

        def issafe(migration):
            """Determine if a migration is safe to run before release."""
            return getattr(migration, "safe", True)

        # Pull the migrations into a new list.
        migrations = [migration for migration, backward in plan]
        safe = [migration for migration in migrations if issafe(migration)]
        unsafe = [migration for migration in migrations if not issafe(migration)]

        if not unsafe:
            return  # No unsafe migrations to protect.

        # Display the unsafe migrations that need to be run.
        self.stdout.write(self.style.MIGRATE_HEADING("Unsafe migrations:"))
        for migration in unsafe:
            self.stdout.write(f"  {migration.app_label}.{migration.name}")

        # Include unsafe migrations in initial unblocked list so that
        # we can show and check for blocked unsafe migrations.
        unblocked = list(migrations)
        blocked = []

        # Remove migrations blocked by unsafe migrations
        while True:
            blockers = unsafe + blocked
            blockers_deps = [(m.app_label, m.name) for m in blockers]
            to_block_deps = [dep for mig in blockers for dep in mig.run_before]
            block = [
                migration
                for migration in unblocked
                if any(dep in blockers_deps for dep in migration.dependencies)
                or (migration.app_label, migration.name) in to_block_deps
            ]
            if not block:
                break

            blocked.extend(block)
            for migration in blocked:
                unblocked.remove(migration)
                if migration in safe:
                    safe.remove(migration)

        # Order the blocked migrations in the order of the original plan.
        blocked = [m for m in migrations if m in blocked]

        # Display blocked migrations if they exist.
        if blocked:
            self.stdout.write(self.style.MIGRATE_HEADING("Blocked migrations:"))
            for migration in blocked:
                self.stdout.write(f"  {migration.app_label}.{migration.name}")

        if blocked and strict:
            raise CommandError("Aborting due to blocked migrations.")

        # Swap out the items in the plan with the safe migrations.
        # None are backward, so we can always set backward to False.
        plan[:] = [(migration, False) for migration in safe]
