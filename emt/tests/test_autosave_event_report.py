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
        self.assertIn("report_id", data)
        report = EventReport.objects.get(proposal=self.proposal)
        self.assertEqual(report.location, "Main Hall")
        self.assertEqual(report.summary, "Summary text")
        self.assertEqual(report.outcomes, "Outcome text")
        activities = list(EventActivity.objects.filter(proposal=self.proposal))
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0].name, "Intro")

    def test_autosave_saves_participant_counts_and_committee(self):
        url = reverse("emt:autosave_event_report")
        payload = {
            "proposal_id": self.proposal.id,
            "num_participants": 25,
            "num_student_participants": 15,
            "num_faculty_participants": 5,
            "num_external_participants": 5,
            "num_student_volunteers": 5,
            "organizing_committee": "Alice, Bob",
            "attendance_notes": json.dumps([{"name": "Alice"}]),
        }
        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("report_id", resp.json())
        report = EventReport.objects.get(proposal=self.proposal)
        self.assertEqual(report.num_participants, 25)
        self.assertEqual(report.num_student_participants, 15)
        self.assertEqual(report.num_faculty_participants, 5)
        self.assertEqual(report.num_external_participants, 5)
        self.assertEqual(report.num_student_volunteers, 5)
        self.assertEqual(report.organizing_committee, "Alice, Bob")
        self.assertEqual(report.attendance_notes, json.dumps([{"name": "Alice"}]))

        # Reload the form and confirm values are pre-filled
        response = self.client.get(reverse("emt:submit_event_report", args=[self.proposal.id]))
        self.assertContains(response, 'name="num_participants" value="25"', html=False)
        self.assertContains(response, 'name="num_student_participants" value="15"', html=False)
        self.assertContains(response, 'name="num_faculty_participants" value="5"', html=False)
        self.assertContains(response, 'name="num_external_participants" value="5"', html=False)

    def test_autosave_saves_analysis_section(self):
        url = reverse("emt:autosave_event_report")
        payload = {
            "proposal_id": self.proposal.id,
            "analysis": "Detailed analysis text",
        }
        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("report_id", resp.json())
        report = EventReport.objects.get(proposal=self.proposal)
        self.assertEqual(report.analysis, "Detailed analysis text")

    def test_autosave_with_report_id_updates(self):
        url = reverse("emt:autosave_event_report")
        payload = {"proposal_id": self.proposal.id, "location": "Room 1"}
        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        report_id = resp.json()["report_id"]

        payload2 = {"proposal_id": self.proposal.id, "report_id": report_id, "location": "Room 2"}
        self.client.post(url, data=json.dumps(payload2), content_type="application/json")
        report = EventReport.objects.get(id=report_id)
        self.assertEqual(report.location, "Room 2")

    def test_autosave_invalid_json(self):
        url = reverse("emt:autosave_event_report")
        resp = self.client.post(url, data="not json", content_type="application/json")
        self.assertEqual(resp.status_code, 400)
