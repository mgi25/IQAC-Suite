from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from transcript.models import AcademicYear


class AcademicYearSettingsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="pass"
        )
        self.client.force_login(self.user)
        self.url = reverse("admin_academic_year_settings")

    def test_duplicate_year_does_not_archive_existing(self):
        existing = AcademicYear.objects.create(
            year="2024-2025",
            start_date=date(2024, 6, 1),
            end_date=date(2025, 5, 31),
            is_active=True,
        )

        response = self.client.post(
            self.url,
            {
                "start_date": "2024-06-01",
                "end_date": "2025-05-31",
            },
            follow=True,
        )

        self.assertContains(response, "already exists")
        existing.refresh_from_db()
        self.assertTrue(existing.is_active)
        self.assertEqual(AcademicYear.objects.count(), 1)

    def test_new_year_becomes_active_and_archives_previous(self):
        previous = AcademicYear.objects.create(
            year="2023-2024",
            start_date=date(2023, 6, 1),
            end_date=date(2024, 5, 31),
            is_active=True,
        )

        response = self.client.post(
            self.url,
            {
                "start_date": "2024-06-01",
                "end_date": "2025-05-31",
            },
        )

        self.assertEqual(response.status_code, 302)
        previous.refresh_from_db()
        self.assertFalse(previous.is_active)
        new_year = AcademicYear.objects.get(year="2024-2025")
        self.assertTrue(new_year.is_active)
