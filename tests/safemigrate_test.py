"""Unit tests for the safemigrate command."""
import pytest
from django.core.management.base import CommandError

from django_safemigrate import Safe
from django_safemigrate.check import validate_migrations
from django_safemigrate.management.commands.safemigrate import Command


class Migration:
    """A mock migration."""

    def __init__(
        self, app_label=None, name=None, dependencies=None, run_before=None, safe=None
    ):
        self.app_label = app_label or "app_label"
        self.name = name or "0001_fake_migration"
        self.dependencies = dependencies or []
        self.run_before = run_before or []
        if safe is not None:
            self.safe = safe

    def __repr__(self):
        return f"<Migration {self.app_label}.{self.name}>"


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
        """It should fail to run backward."""
        plan = [(Migration(), True)]
        with pytest.raises(CommandError):
            receiver(plan=plan)

    def default_after(self, receiver):
        """Migrations are after by default."""
        plan = [(Migration(), False)]
        receiver(plan=plan)
        assert len(plan) == 0

    def test_all_before(self, receiver):
        """Before migrations will remain in the plan."""
        plan = [(Migration(safe=Safe.before_deploy), False)]
        receiver(plan=plan)
        assert len(plan) == 1

    def test_final_after(self, receiver):
        """Run everything except the final migration."""
        plan = [
            (Migration("spam", "0001_initial", safe=Safe.before_deploy), False),
            (
                Migration(
                    "spam",
                    "0002_followup",
                    safe=Safe.after_deploy,
                    dependencies=[("spam", "0001_initial")],
                ),
                False,
            ),
        ]
        receiver(plan=plan)
        assert len(plan) == 1

    def test_multiple_after(self, receiver):
        """Run up to the first after migration."""
        plan = [
            (Migration("spam", "0001_initial", safe=Safe.before_deploy), False),
            (
                Migration(
                    "spam",
                    "0002_followup",
                    safe=Safe.after_deploy,
                    dependencies=[("spam", "0001_initial")],
                ),
                False,
            ),
            (Migration("eggs", "0001_followup", safe=Safe.after_deploy), False),
        ]
        receiver(plan=plan)
        assert len(plan) == 1

    def test_blocked_by_after(self, receiver):
        """Blocked before migrations indicate a failure state.

        This might happen when an after migration is shipped, but
        is not run manually after the deployment happened. Safe
        migrations should be run automatically, so this needs to
        block to avoid release failures.
        """
        plan = [
            (Migration("spam", "0001_initial", safe=Safe.before_deploy), False),
            (
                Migration(
                    "spam",
                    "0002_followup",
                    safe=Safe.after_deploy,
                    dependencies=[("spam", "0001_initial")],
                ),
                False,
            ),
            (
                Migration(
                    "spam",
                    "0003_safety",
                    safe=Safe.before_deploy,
                    dependencies=[("spam", "0002_followup")],
                ),
                False,
            ),
        ]
        with pytest.raises(CommandError):
            receiver(plan=plan)

    def test_blocked_by_after_run_before(self, receiver):
        """Consider run_before when tracking dependencies.

        run_before allows for dependency inversion when a migration
        needs to be run before a migration that may not be under
        your control to add a dependency to directly.
        """
        plan = [
            (Migration("spam", "0001_initial", safe=Safe.before_deploy), False),
            (
                Migration(
                    "spam",
                    "0002_followup",
                    safe=Safe.after_deploy,
                    dependencies=[("spam", "0001_initial")],
                    run_before=[("eggs", "0001_safety")],
                ),
                False,
            ),
            (Migration("eggs", "0001_safety", safe=Safe.before_deploy), False),
        ]
        with pytest.raises(CommandError):
            receiver(plan=plan)

    def test_consecutive_after(self, receiver):
        """Consecutive after migrations are ok."""
        plan = [
            (Migration("spam", "0001_initial", safe=Safe.before_deploy), False),
            (
                Migration(
                    "spam",
                    "0002_followup",
                    safe=Safe.after_deploy,
                    dependencies=[("spam", "0001_initial")],
                ),
                False,
            ),
            (
                Migration(
                    "spam",
                    "0003_safety",
                    safe=Safe.after_deploy,
                    dependencies=[("spam", "0002_followup")],
                ),
                False,
            ),
        ]
        receiver(plan=plan)
        assert len(plan) == 1

    def test_always_before_after(self, receiver):
        """Always migrations will run before after migrations."""
        plan = [
            (Migration("spam", "0001_initial", safe=Safe.always), False),
            (
                Migration(
                    "spam",
                    "0002_followup",
                    safe=Safe.after_deploy,
                    dependencies=[("spam", "0001_initial")],
                ),
                False,
            ),
        ]
        receiver(plan=plan)
        assert len(plan) == 1

    def test_always_after_after(self, receiver):
        """Always migrations will not block after deployments."""
        plan = [
            (Migration("spam", "0001_initial", safe=Safe.after_deploy), False),
            (
                Migration(
                    "spam",
                    "0002_followup",
                    safe=Safe.always,
                    dependencies=[("spam", "0001_initial")],
                ),
                False,
            ),
        ]
        receiver(plan=plan)
        assert len(plan) == 0

    def test_blocked_by_after_nonstrict(self, settings, receiver):
        """Nonstrict mode allows before blocked migrations.

        This allows the command to succeed where it would normally
        error. This allows for development environments, where
        errors are acceptable during transitions, to avoid having
        to migrate everything incrementall the way production
        environments are expected to.
        """
        settings.SAFEMIGRATE = "nonstrict"
        plan = [
            (Migration("spam", "0001_initial", safe=Safe.before_deploy), False),
            (
                Migration(
                    "spam",
                    "0002_followup",
                    safe=Safe.after_deploy,
                    dependencies=[("spam", "0001_initial")],
                ),
                False,
            ),
            (
                Migration(
                    "spam",
                    "0003_safety",
                    safe=Safe.before_deploy,
                    dependencies=[("spam", "0002_followup")],
                ),
                False,
            ),
        ]
        receiver(plan=plan)
        assert len(plan) == 1

    def test_string_invalid(self, receiver):
        """Invalid settings of the safe property will raise an error."""
        plan = [(Migration("spam", "0001_initial", safe="before_deploy"), False)]
        with pytest.raises(CommandError):
            receiver(plan=plan)

    def test_boolean_invalid(self, receiver):
        """Booleans are invalid for the safe property."""
        plan = [(Migration("spam", "0001_initial", safe=False), False)]
        with pytest.raises(CommandError):
            receiver(plan=plan)


class TestCheck:
    """Exercise the check command."""

    MARKED = """
from django.db import migrations
from django_safemigrate import Safe

class Migration(migrations.Migration):
    safe = Safe.always
"""

    UNMARKED = """
from django.db import migrations

class Migration(migrations.Migration):
    pass
"""

    def test_validate_migrations_success(self, tmp_path):
        with open(tmp_path / "0001_initial.py", "w") as f:
            f.write(self.MARKED)
        assert validate_migrations([tmp_path / "0001_initial.py"])

    def test_validate_migrations_failure(self, tmp_path):
        with open(tmp_path / "0001_initial.py", "w") as f:
            f.write(self.UNMARKED)
        assert not validate_migrations([tmp_path / "0001_initial.py"])

    def test_validate_migrations_falsematch(self, tmp_path):
        with open(tmp_path / "0001_initial.py", "w") as f:
            f.write("THIS IS NOT A MIGRATION")
        assert validate_migrations([tmp_path / "0001_initial.py"])
