from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class EnhanceSummaryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", "u@example.com", "p")
        self.client.force_login(self.user)

    def test_enhance_summary_requires_text(self):
        resp = self.client.post(reverse("emt:enhance_summary"), {})
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertFalse(data["ok"])
        self.assertIn("no summary", data["error"].lower())

    def test_enhance_summary_disabled(self):
        resp = self.client.post(
            reverse("emt:enhance_summary"),
            {"text": "original", "title": "T"},
        )
        self.assertEqual(resp.status_code, 503)
        data = resp.json()
        self.assertFalse(data["ok"])
        self.assertIn("disabled", data["error"].lower())
