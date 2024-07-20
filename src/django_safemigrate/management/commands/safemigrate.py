"""Hook into the migrate command to add safety.

Migration safety is enforced by a pre_migrate signal receiver.
"""

from __future__ import annotations

from functools import cached_property
from enum import Enum

from django.conf import settings
from django.core.management.base import CommandError
from django.core.management.commands import migrate
from django.db.migrations import Migration
from django.db.models.signals import pre_migrate
from django.utils import timezone
from django.utils.timesince import timeuntil

from django_safemigrate import Safe, When
from django_safemigrate.models import SafeMigration


class Mode(Enum):
    """The mode of operation for safemigrate.

    STRICT, the default mode, will throw an error if migrations
    marked Safe.before_deploy() are blocked by unrun migrations that
    are marked Safe.after_deploy() with an unfulfilled delay.

    NONSTRICT will run the same migrations as strict mode, but will
    not throw an error if migrations are blocked.

    DISABLED will completely bypass safemigrate protections and run
    exactly the same as the standard migrate command.
    """

    STRICT = "strict"
    NONSTRICT = "nonstrict"
    DISABLED = "disabled"


class Command(migrate.Command):
    """Run database migrations that are safe to run before deployment."""

    help = "Run database migrations that are safe to run before deployment."
    receiver_has_run = False
    fake = False

    def handle(self, *args, **options):
        self.fake = options.get("fake", False)
        # Only connect the handler when this command is run to
        # avoid running for tests.
        pre_migrate.connect(
            self.pre_migrate_receiver, dispatch_uid="django_safemigrate"
        )
        super().handle(*args, **options)

    def pre_migrate_receiver(self, *, plan: list[tuple[Migration, bool]], **_):
        """Modify the migration plan to apply deployment safety."""
        if self.receiver_has_run:
            return  # Only run once
        self.receiver_has_run = True

        if self.mode == Mode.DISABLED:
            return  # Run migrate normally

        if any(backward for _, backward in plan):
            raise CommandError("Backward migrations are not supported.")

        # Resolve the configuration for each migration
        config = {migration: self.safe(migration) for migration, _ in plan}

        # Give a command error if any safe configuration is invalid
        self.validate(config)

        # Get the dates of when migrations were detected
        detected = self.detected(config)

        # Resolve the current status for each migration respecting delays
        resolved = self.resolve(config, detected)

        # Categorize the migrations for display and action
        ready, delayed, blocked = self.categorize(resolved)

        # Blocked migrations require delayed migrations
        if not delayed:
            return  # Run all the migrations

        # Display the delayed migrations
        self.write_delayed(delayed, config, resolved, detected)

        # Display the blocked migrations
        if blocked:
            self.write_blocked(blocked)

        if blocked and self.mode == Mode.STRICT:
            raise CommandError("Aborting due to blocked migrations.")

        # Mark the delayed migrations as detected if not faking
        if not self.fake:
            self.detect(
                [
                    migration
                    for migration in delayed
                    if config[migration].when == When.AFTER_DEPLOY
                    and config[migration].delay is not None
                ]
            )

        # Swap out the items in the plan with the safe migrations.
        # None are backward, so we can always set backward to False.
        plan[:] = [(migration, False) for migration in ready]

    @cached_property
    def mode(self):
        """Determine the configured mode of operation for safemigrate."""
        try:
            return Mode(getattr(settings, "SAFEMIGRATE", "strict").lower())
        except ValueError:
            raise ValueError(
                "The SAFEMIGRATE setting is invalid."
                " It must be one of 'strict', 'nonstrict', or 'disabled'."
            )

    @staticmethod
    def safe(migration: Migration) -> Safe:
        """Determine the safety setting of a migration."""
        callables = [Safe.before_deploy, Safe.after_deploy, Safe.always]
        safe = getattr(migration, "safe", Safe.always)
        return safe() if safe in callables else safe

    def validate(self, config):
        """Check for invalid safe configurations.

        Exit with a command error if any configurations are invalid.
        """
        invalid = [
            migration
            for migration, safe in config.items()
            if not isinstance(safe, Safe)
        ]
        if invalid:
            self.stdout.write(self.style.MIGRATE_HEADING("Invalid migrations:"))
            for migration in invalid:
                self.stdout.write(f"  {migration.app_label}.{migration.name}")
            raise CommandError(
                "Aborting due to migrations with invalid safe properties."
            )

    def detected(
        self, config: dict[Migration, Safe]
    ) -> dict[Migration, timezone.datetime]:
        """Get the detected dates for each migration."""
        detected_map = SafeMigration.objects.get_detected_map(
            [
                (migration.app_label, migration.name)
                for migration, safe in config.items()
                if safe.when == When.AFTER_DEPLOY and safe.delay is not None
            ]
        )
        return {
            migration: detected_map[(migration.app_label, migration.name)]
            for migration in config
            if (migration.app_label, migration.name) in detected_map
        }

    def resolve(
        self,
        config: dict[Migration, Safe],
        detected: dict[Migration, timezone.datetime],
    ) -> dict[Migration, When]:
        """Resolve the current status of each migration.

        ``When.AFTER_DEPLOY`` migrations are resolved to ``When.ALWAYS``
        if they have previously been detected and their delay has passed.
        """
        now = timezone.now()
        return {
            migration: (
                When.ALWAYS
                if safe.when == When.AFTER_DEPLOY
                and safe.delay is not None
                and migration in detected
                and detected[migration] + safe.delay <= now
                else safe.when
            )
            for migration, safe in config.items()
        }

    def categorize(
        self, resolved: dict[Migration, When]
    ) -> tuple[list[Migration], list[Migration], list[Migration]]:
        """Categorize the migrations as ready, delayed, or blocked.

        Ready migrations are ready to be run immediately.

        Delayed migrations cannot be run immediately, but are safe to run
        after deployment.

        Blocked migrations are dependent on a delayed migration, but
        either need to run before deployment or depend on a migration
        that needs to run before deployment.
        """
        ready = [mig for mig, when in resolved.items() if when != When.AFTER_DEPLOY]
        delayed = [mig for mig, when in resolved.items() if when == When.AFTER_DEPLOY]
        blocked = []

        if not delayed and not blocked:
            return ready, delayed, blocked

        def to_block(target, blockers):
            """Find a round of migrations that depend on these blockers."""
            blocker_deps = [(m.app_label, m.name) for m in blockers]
            to_block_deps = [dep for m in blockers for dep in m.run_before]
            return [
                migration
                for migration in target
                if any(dep in blocker_deps for dep in migration.dependencies)
                or (migration.app_label, migration.name) in to_block_deps
            ]

        # Delay or block ready migrations that are behind delayed migrations.
        while True:
            block = to_block(ready, delayed + blocked)
            if not block:
                break

            for migration in block:
                ready.remove(migration)
                if resolved[migration] == When.BEFORE_DEPLOY:
                    blocked.append(migration)
                else:
                    delayed.append(migration)

        # Block delayed migrations that are behind other blocked migrations.
        while True:
            block = to_block(delayed, blocked)
            if not block:
                break

            for migration in block:
                delayed.remove(migration)
                blocked.append(migration)

        # Order the migrations in the order of the original plan.
        ready = [m for m in resolved if m in ready]
        delayed = [m for m in resolved if m in delayed]
        blocked = [m for m in resolved if m in blocked]

        return ready, delayed, blocked

    def write_delayed(
        self,
        migrations: list[Migration],
        config: dict[Migration, Safe],
        resolved: dict[Migration, When],
        detected: dict[Migration, timezone.datetime],
    ):
        """Display delayed migrations."""
        self.stdout.write(self.style.MIGRATE_HEADING("Delayed migrations:"))
        for migration in migrations:
            if (
                resolved[migration] == When.AFTER_DEPLOY
                and config[migration].delay is not None
            ):
                now = timezone.localtime()
                migrate_date = detected.get(migration, now) + config[migration].delay
                humanized_date = timeuntil(migrate_date, now=now, depth=2)
                self.stdout.write(
                    f"  {migration.app_label}.{migration.name} "
                    f"(can automatically migrate in {humanized_date} "
                    f"- {migrate_date.isoformat()})"
                )
            else:
                self.stdout.write(f"  {migration.app_label}.{migration.name}")

    def write_blocked(self, migrations: list[Migration]):
        """Display blocked migrations."""
        self.stdout.write(self.style.MIGRATE_HEADING("Blocked migrations:"))
        for migration in migrations:
            self.stdout.write(f"  {migration.app_label}.{migration.name}")

    def detect(self, migrations):
        """Mark the given migrations as detected."""
        # The detection datetime is what's used to determine if an
        # after_deploy() with a delay can be migrated or not.
        for migration in migrations:
            SafeMigration.objects.get_or_create(
                app=migration.app_label, name=migration.name
            )
