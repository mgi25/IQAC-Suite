from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from emt.models import EventProposal


class AIGenerationDisabledTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", "u@example.com", "p")
        self.client.force_login(self.user)
        self.proposal = EventProposal.objects.create(
            submitted_by=self.user,
            event_title="Example Event",
        )

    def _post(self, name, data=None):
        url = reverse(name)
        return self.client.post(url, data or {})

    def test_generate_need_analysis_disabled(self):
        resp = self._post("emt:generate_need_analysis", {"title": "T"})
        self.assertEqual(resp.status_code, 503)
        data = resp.json()
        self.assertFalse(data["ok"])
        self.assertIn("disabled", data["error"].lower())

    def test_generate_objectives_disabled(self):
        resp = self._post("emt:generate_objectives", {"title": "T"})
        self.assertEqual(resp.status_code, 503)
        data = resp.json()
        self.assertFalse(data["ok"])
        self.assertIn("disabled", data["error"].lower())

    def test_generate_expected_outcomes_disabled(self):
        resp = self._post("emt:generate_expected_outcomes", {"title": "T"})
        self.assertEqual(resp.status_code, 503)
        data = resp.json()
        self.assertFalse(data["ok"])
        self.assertIn("disabled", data["error"].lower())

    def test_generate_why_event_disabled(self):
        resp = self._post("emt:generate_why_event", {"title": "T"})
        self.assertEqual(resp.status_code, 503)
        data = resp.json()
        self.assertFalse(data["ok"])
        self.assertIn("disabled", data["error"].lower())

    def test_ai_generate_report_disabled(self):
        url = reverse("emt:ai_generate_report", args=[self.proposal.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 503)

    def test_generate_ai_report_disabled(self):
        url = reverse("emt:generate_ai_report")
        resp = self.client.post(url, data="{}", content_type="application/json")
        self.assertEqual(resp.status_code, 503)
        data = resp.json()
        self.assertFalse(data["ok"])
        self.assertIn("disabled", data["error"].lower())

    def test_generate_ai_report_stream_disabled(self):
        url = reverse("emt:generate_ai_report_stream", args=[self.proposal.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 503)

    def test_ai_report_edit_disabled(self):
        url = reverse("emt:ai_report_edit", args=[self.proposal.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 503)

    def test_need_analysis_requires_login(self):
        self.client.logout()
        resp = self.client.post(reverse("emt:generate_need_analysis"))
        self.assertEqual(resp.status_code, 302)

    def test_objectives_requires_login(self):
        self.client.logout()
        resp = self.client.post(reverse("emt:generate_objectives"))
        self.assertEqual(resp.status_code, 302)

    def test_outcomes_requires_login(self):
        self.client.logout()
        resp = self.client.post(reverse("emt:generate_expected_outcomes"))
        self.assertEqual(resp.status_code, 302)

    def test_why_event_requires_login(self):
        self.client.logout()
        resp = self.client.post(reverse("emt:generate_why_event"))
        self.assertEqual(resp.status_code, 302)

    def test_need_analysis_get_not_allowed(self):
        resp = self.client.get(reverse("emt:generate_need_analysis"))
        self.assertEqual(resp.status_code, 405)

    def test_objectives_get_not_allowed(self):
        resp = self.client.get(reverse("emt:generate_objectives"))
        self.assertEqual(resp.status_code, 405)

    def test_outcomes_get_not_allowed(self):
        resp = self.client.get(reverse("emt:generate_expected_outcomes"))
        self.assertEqual(resp.status_code, 405)

    def test_why_event_get_not_allowed(self):
        resp = self.client.get(reverse("emt:generate_why_event"))
        self.assertEqual(resp.status_code, 405)
