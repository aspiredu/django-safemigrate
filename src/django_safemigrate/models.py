from django.db import models
from django.utils.translation import gettext_lazy as _


class SafeMigration(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["app", "name"], name="safemigration_unique"
            ),
        ]

    created = models.DateTimeField(auto_now_add=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    detected = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_(
            "The time the migration was detected. This is used to determine when a migration with Safe.after_deploy() should be migrated."
        ),
    )
