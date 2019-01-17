"""Hook into the migrate command to add safety.

Migration safety is enforced by a pre_migrate signal receiver.
"""
from django.conf import settings
from django.db.models.signals import pre_migrate
from django.core.management.base import CommandError
from django.core.management.commands import migrate
from django_safemigrate import Safe
from django_safemigrate.apps import SafeMigrateConfig


def safety(migration):
    """Determine the safety status of a migration."""
    return getattr(migration, "safe", Safe.after_deploy)


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

        # strict by default
        strict = getattr(settings, "SAFEMIGRATE", None) != "nonstrict"

        if any(backward for mig, backward in plan):
            raise CommandError("Backward migrations are not supported.")

        # Pull the migrations into a new list
        migrations = [migration for migration, backward in plan]

        # Check for invalid safe properties
        invalid = [
            migration for migration in migrations if safety(migration) not in Safe
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
            if safety(migration) == Safe.after_deploy
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
            if safety(migration) != Safe.after_deploy
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
                if safety(migration) == Safe.before_deploy:
                    blocked.append(migration)
                else:
                    delayed.append(migration)

        # Order the migrations in the order of the original plan.
        delayed = [m for m in migrations if m in delayed]
        blocked = [m for m in migrations if m in blocked]

        # Display delayed migrations if they exist:
        if delayed:
            self.stdout.write(self.style.MIGRATE_HEADING("Delayed migrations:"))
            for migration in delayed:
                self.stdout.write(f"  {migration.app_label}.{migration.name}")

        # Display blocked migrations if they exist.
        if blocked:
            self.stdout.write(self.style.MIGRATE_HEADING("Blocked migrations:"))
            for migration in blocked:
                self.stdout.write(f"  {migration.app_label}.{migration.name}")

        if blocked and strict:
            raise CommandError("Aborting due to blocked migrations.")

        # Swap out the items in the plan with the safe migrations.
        # None are backward, so we can always set backward to False.
        plan[:] = [(migration, False) for migration in ready]
