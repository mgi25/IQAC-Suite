from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in
import json

from core.signals import create_or_update_user_profile, assign_role_on_login
from emt.models import EventProposal, EventReport, EventActivity


class AutosaveEventReportTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        post_save.disconnect(create_or_update_user_profile, sender=User)
        user_logged_in.disconnect(assign_role_on_login)

    @classmethod
    def tearDownClass(cls):
        user_logged_in.connect(assign_role_on_login)
        post_save.connect(create_or_update_user_profile, sender=User)
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="pass")
        self.client.force_login(self.user)
        self.proposal = EventProposal.objects.create(
            submitted_by=self.user,
            event_title="Sample Event",
        )

    def test_autosave_creates_report_and_saves_fields(self):
        url = reverse("emt:autosave_event_report")
        payload = {
            "proposal_id": self.proposal.id,
            "location": "Main Hall",
            "event_summary": "Summary text",
            "event_outcomes": "Outcome text",
            "num_activities": "1",
            "activity_name_1": "Intro",
            "activity_date_1": "2024-01-01",
        }
        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))
        report = EventReport.objects.get(proposal=self.proposal)
        self.assertEqual(report.location, "Main Hall")
        self.assertEqual(report.summary, "Summary text")
        self.assertEqual(report.outcomes, "Outcome text")
        activities = list(EventActivity.objects.filter(proposal=self.proposal))
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0].name, "Intro")

    def test_autosave_invalid_json(self):
        url = reverse("emt:autosave_event_report")
        resp = self.client.post(url, data="not json", content_type="application/json")
        self.assertEqual(resp.status_code, 400)
