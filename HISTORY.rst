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
