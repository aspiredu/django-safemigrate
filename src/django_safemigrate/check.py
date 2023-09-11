"""
Ensure migrations are using django_safemigrate.

This is fairly rudimentary and won't work if the class doesn't
explicitly inherit from ``Migration``.
"""
import re
import sys

MIGRATION_PATTERN = re.compile(r"class\s+(?P<MigrationClass>\w+)\s?\(.*Migration\):")

MISSING_SAFE_MESSAGE = (
    "{file_path}: {migration_class} is missing the 'safe' attribute.\n"
)
FAILURE_MESSAGE = (
    "\n"
    "Add the following to the migration class:\n"
    "\n"
    "from django_safemigrate import Safe\n"
    "class Migration(migrations.Migration):\n"
    "    safe = Safe.before_deploy\n"
    "\n"
    "You can also use the following:\n"
    "    safe = Safe.always\n"
    "    safe = Safe.after_deploy\n"
    "\n"
)


def validate_migrations(files):
    success = True
    for file_path in files:
        with open(file_path) as f:
            content = f.read()

        match = MIGRATION_PATTERN.search(content)
        if match:
            migration_class = match.group("MigrationClass")
            if "safe = Safe." not in content:
                success = False
                sys.stdout.write(
                    MISSING_SAFE_MESSAGE.format(
                        file_path=file_path, migration_class=migration_class
                    )
                )
    if not success:
        sys.stdout.write(FAILURE_MESSAGE)
    return success


def main():  # pragma: no cover
    sys.exit(0 if validate_migrations(sys.argv[1:]) else 1)


if __name__ == "__main__":  # pragma: no cover
    main()
