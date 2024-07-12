from datetime import timedelta

import pytest
from django.utils import timezone

from django_safemigrate.models import SafeMigration

pytestmark = pytest.mark.django_db


class TestSafeMigrationManager:
    def test_get_detected_map(self):
        m1 = SafeMigration.objects.create(
            app="spam", name="0001", detected=timezone.now() - timedelta(days=1)
        )
        m2 = SafeMigration.objects.create(
            app="spam", name="0002", detected=timezone.now()
        )
        mapping = SafeMigration.objects.get_detected_map(
            [("spam", "0001"), ("spam", "0002")]
        )
        assert mapping == {("spam", "0001"): m1.detected, ("spam", "0002"): m2.detected}

        mapping = SafeMigration.objects.get_detected_map([("spam", "0001")])
        assert mapping == {("spam", "0001"): m1.detected}
