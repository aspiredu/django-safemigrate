"""Add a safemigrate command."""
from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class SafeMigrateConfig(AppConfig):
    """Safe migrate Django app config."""

    name = "django_safemigrate"
    verbose_name = _("Safe Migrate")
