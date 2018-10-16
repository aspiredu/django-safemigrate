===========================================================
django-safemigrate: Safely run migrations before deployment
===========================================================

django-safemigrate add a ``safemigrate`` command to Django
to allow for safely running a migration command when deploying.

Usage
=====

Install ``django-safemigrate``, then add this to the
``INSTALLED_APPS`` in the settings file:

.. code-block:: python

    INSTALLED_APPS = [
        # ...
        "django_safemigrate.apps.SafeMigrateConfig",
    ]

Then mark any migration that should not be run
during a pre-deployment stage,
such as a migration to remove a column.

.. code-block:: python

    class Migration(migrations.Migration):
        safe = False

At this point you can run the ``safemigrate`` Django command
to run the migrations, and the unsafe migrations will not run.
When the code is fully deployed, just run the normal ``migrate``
Django command, which still functions normally.

For example, you could add the command to the release phase
for your Heroku app, and the safe migrations will be run
automatically when the new release is promoted.

Nonstrict Mode
==============

Under normal operation, if there are migrations that depend
on any migration that is marked as unsafe,
the command will raise an error to indicate
that there are unsafe migrations that
should have already been run, but have not been.

In development, however, it is common that these
would accumulate between developers,
and since it is acceptable for there to be downtime
during the transitional period in development,
it is better to allow the command to continue without raising.

To enable nonstrict mode, add the ``SAFEMIGRATE`` setting:

.. code-block:: python

    SAFEMIGRATE = "nonstrict"

In this mode ``safemigrate`` will run all the migrations
that are not blocked by any unsafe migrations.
Any remaining migrations can be run after the fact
using the normal ``migrate`` Django command.
