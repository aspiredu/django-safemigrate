5.0 (TBD)
*********

* Add support for Django 5.1.
* Drop support for Django 3.2, 4.0, 4.1.
* Convert ``Safe`` to be a custom class rather than an ``Enum``.
* The standard values of ``Safe`` now support being called. For example:

  * ``Safe.before_deploy()``
  * ``Safe.after_deploy()``
  * ``Safe.always()``
* Add support for allowing a ``Safe.after_deploy(delay=timedelta())``
  migration to be migrated after the delay has passed.
* Change the default value of ``safe`` to ``Safe.always``.
  This is a better default for third party apps that are not using
  ``django_safemigrate``.
* ``Safe.after_deploy`` and ``Safe.always`` migrations will be
  reported as blocked if they are behind a blocked ``Safe.before_deploy``
  migration.
* ``Safe.after_deploy`` migrations are now reported along with other
  delayed migrations instead of being separately reported as protected.
* Use PEP8 compliant capitalization for enums internally. This doesn't
  affect any documented API usage.

4.3 (2024-03-28)
++++++++++++++++

* Add ``settings.SAFEMIGRATE = "disabled"`` setting to disable ``safemigrate``
  protections.

4.2 (2023-12-13)
++++++++++++++++

* Add support for Django 5.0.
* Add support for Python 3.12.
* Expand test matrix to all supported combinations of Django and Python.

4.1 (2023-09-13)
++++++++++++++++

* Add a pre-commit hook to ensure migrations have a safe attribute.

4.0 (2022-10-07)
++++++++++++++++

* Add support for Django 4.1, 4.2.
* Add support for Python 3.11.
* Drop support for Django 3.0, 3.1.
* Drop support for Python 3.6, 3.7.

3.1 (2021-12-08)
++++++++++++++++

* Add support for Django 4.0.

3.0 (2020-10-07)
++++++++++++++++

* Drop support for Django<3.


2.1 (2019-12-05)
++++++++++++++++

* Add support for Django 3.

2.0 (2019-01-17)
++++++++++++++++

* The valid values for ``safe`` are:

  * ``Safe.before_deploy``
  * ``Safe.after_deploy``
  * ``Safe.always``

  Import with ``from django_safemigrate import Safe``.
  ``True`` is now ``Safe.before_deploy``,
  and ``False`` is now ``Safe.after_deploy``.
* The default safety marking, when unspecified,
  is now ``Safe.after_deploy``, instead of ``Safe.before_deploy``.
* ``Safe.always`` allows for migrations that may be run
  either before or after deployment,
  because they don't require any database changes.
* Multiple dependent ``Safe.after_deploy`` migrations do not block deployment
  as long as there are no dependent ``Safe.before_deploy`` migrations.
* Enforce that any given value of safe is valid.

1.0 (2019-01-13)
++++++++++++++++

* Initial Release
