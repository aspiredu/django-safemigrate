===========================================================
django-safemigrate: Safely run migrations before deployment
===========================================================

.. image:: https://img.shields.io/pypi/v/django-safemigrate.svg
   :target: https://pypi.org/project/django-safemigrate/
   :alt: Latest Version

.. image:: https://dev.azure.com/aspiredu/django-safemigrate/_apis/build/status/1?branchName=master
   :target: https://dev.azure.com/aspiredu/django-safemigrate/_build/latest?definitionId=1&branchName=master
   :alt: Build status

.. image:: https://codecov.io/gh/aspiredu/django-safemigrate/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/aspiredu/django-safemigrate
   :alt: Code Coverage

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/ambv/black
   :alt: Code style: black

|

django-safemigrate adds a ``safemigrate`` command to Django
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

Then mark any migration that may be run
during a pre-deployment stage,
such as a migration to add a column.

.. code-block:: python

    from django_safemigrate import Safe

    class Migration(migrations.Migration):
        safe = Safe.before_deploy

At this point you can run the ``safemigrate`` Django command
to run the migrations, and only these migrations will run.
However, if migrations that are not safe to run before
the code is deployed are dependencies of this migration,
then these migrations will be blocked, and the safemigrate
command will fail with an error.

When the code is fully deployed, just run the normal ``migrate``
Django command, which still functions normally.
For example, you could add the command to the release phase
for your Heroku app, and the safe migrations will be run
automatically when the new release is promoted.

Safety Options
==============

There are three options for the value of the
``safe`` property of the migration.

* ``Safe.before_deploy``

  This migration is only safe to run before the code change is deployed.
  For example, a migration that adds a new field to a model.

* ``Safe.after_deploy``

  This migration is only safe to run after the code change is deployed.
  This is the default that is applied if no ``safe`` property is given.
  For example, a migration that removes a field from a model.

* ``Safe.always``

  This migration is safe to run before *and* after
  the code change is deployed.
  For example, a migration that changes the ``help_text`` of a field.

Nonstrict Mode
==============

Under normal operation, if there are migrations
that must run before the deployment that depend
on any migration that is marked to run after deployment
(or is not marked),
the command will raise an error to indicate
that there are protected migrations that
should have already been run, but have not been,
and are blocking migrations that are expected to run.

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
