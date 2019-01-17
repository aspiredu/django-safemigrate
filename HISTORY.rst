2.0 (TBD)
+++++++++

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

1.0 (2019-01-13)
++++++++++++++++

* Initial Release
