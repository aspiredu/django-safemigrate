"""Unit tests for the safemigrate command."""
import pytest
from django.core.management.base import CommandError
from django_safemigrate.management.commands.safemigrate import Command


class Migration:
    """A mock migration."""

    def __init__(self, app_label=None, name=None, dependencies=None, safe=None):
        self.app_label = app_label or "app_label"
        self.name = name or "0001_fake_migration"
        self.dependencies = dependencies or []
        if safe is not None:
            self.safe = safe


class TestSafeMigrate:
    """Unit tests for the safemigrate command."""

    @pytest.fixture
    def receiver(self):
        """A bound receiver to test against."""
        return Command().pre_migrate_receiver

    def test_receiver_addition(self, mocker):
        connect = mocker.patch(
            "django_safemigrate.management.commands.safemigrate.pre_migrate.connect"
        )
        super_handle = mocker.patch(
            "django_safemigrate.management.commands.safemigrate.migrate.Command.handle"
        )
        command = Command()
        receiver = mocker.patch.object(command, "pre_migrate_receiver")
        command.handle()
        super_handle.assert_called_once_with()
        connect.assert_called_once_with(receiver, dispatch_uid="django_safemigrate")

    def test_rerun(self, receiver):
        """Avoid running the pre_migrate_receiver twice."""
        receiver.__self__.receiver_has_run = True
        plan = [(Migration(), False)]
        receiver(plan=plan)
        assert len(plan) == 1

    def test_backward(self, receiver):
        """It should be able to run backward."""
        plan = [(Migration(), True)]
        receiver(plan=plan)
        assert len(plan) == 1

    def test_all_safe(self, receiver):
        """Safe migrations will remain in the plan."""
        plan = [(Migration(), False)]
        receiver(plan=plan)
        assert len(plan) == 1

    def test_final_unsafe(self, receiver):
        """Run everything except the final migration."""
        plan = [
            (Migration("spam", "0001_initial", safe=True), False),
            (
                Migration(
                    "spam",
                    "0002_followup",
                    safe=False,
                    dependencies=[("spam", "0001_initial")],
                ),
                False,
            ),
        ]
        receiver(plan=plan)
        assert len(plan) == 1

    def test_multiple_unsafe(self, receiver):
        """Run up to the first unsafe migration."""
        plan = [
            (Migration("spam", "0001_initial", safe=True), False),
            (
                Migration(
                    "spam",
                    "0002_followup",
                    safe=False,
                    dependencies=[("spam", "0001_initial")],
                ),
                False,
            ),
            (Migration("eggs", "0001_followup", safe=False), False),
        ]
        receiver(plan=plan)
        assert len(plan) == 1

    def test_blocked_by_unsafe(self, receiver):
        """Blocked safe migrations indicate a failure state.

        This might happen when an unsafe migration is shipped, but
        is not run manually after the deployment happened. Safe
        migrations should be run automatically, so this needs to
        block to avoid release failures.
        """
        plan = [
            (Migration("spam", "0001_initial", safe=True), False),
            (
                Migration(
                    "spam",
                    "0002_followup",
                    safe=False,
                    dependencies=[("spam", "0001_initial")],
                ),
                False,
            ),
            (
                Migration(
                    "spam",
                    "0003_safety",
                    safe=True,
                    dependencies=[("spam", "0002_followup")],
                ),
                False,
            ),
        ]
        with pytest.raises(CommandError):
            receiver(plan=plan)

    def test_unsafe_blocked_by_unsafe(self, receiver):
        """Blocked unsafe migrations indicate a failure state.

        Like blocked safe migrations, dependent unsafe migrations are
        disallowed. They should either be combined into a single
        migration, or deployed separately.
        """
        plan = [
            (Migration("spam", "0001_initial", safe=True), False),
            (
                Migration(
                    "spam",
                    "0002_followup",
                    safe=False,
                    dependencies=[("spam", "0001_initial")],
                ),
                False,
            ),
            (
                Migration(
                    "spam",
                    "0003_safety",
                    safe=False,
                    dependencies=[("spam", "0002_followup")],
                ),
                False,
            ),
        ]
        with pytest.raises(CommandError):
            receiver(plan=plan)

    def test_blocked_by_unsafe_nonstrict(self, settings, receiver):
        """Nonstrict mode allows safe blocked migrations.

        This allows the command to succeed where it would normally
        error. This allows for development environments, where
        errors are acceptable during transitions, to avoid having
        to migrate everything incrementall the way production
        environments are expected to.
        """
        settings.SAFEMIGRATE = "nonstrict"
        plan = [
            (Migration("spam", "0001_initial", safe=True), False),
            (
                Migration(
                    "spam",
                    "0002_followup",
                    safe=False,
                    dependencies=[("spam", "0001_initial")],
                ),
                False,
            ),
            (
                Migration(
                    "spam",
                    "0003_safety",
                    safe=True,
                    dependencies=[("spam", "0002_followup")],
                ),
                False,
            ),
        ]
        receiver(plan=plan)
        assert len(plan) == 1

    def test_unsafe_blocked_by_unsafe_nonstrict(self, settings, receiver):
        """Nonstrict mode allows unsafe blocked migrations.

        This allows the command to succeed where it would normally
        error. This allows for development environments, where
        errors are acceptable during transitions, to avoid having
        to migrate everything incrementally the way production
        environments are expected to.
        """
        settings.SAFEMIGRATE = "nonstrict"
        plan = [
            (Migration("spam", "0001_initial", safe=True), False),
            (
                Migration(
                    "spam",
                    "0002_followup",
                    safe=False,
                    dependencies=[("spam", "0001_initial")],
                ),
                False,
            ),
            (
                Migration(
                    "spam",
                    "0003_safety",
                    safe=False,
                    dependencies=[("spam", "0002_followup")],
                ),
                False,
            ),
        ]
        receiver(plan=plan)
        assert len(plan) == 1
