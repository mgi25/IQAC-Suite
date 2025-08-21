from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from emt.models import EventProposal, EventReport, AttendanceRow


class AttendanceDataViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="pass")
        self.client.force_login(self.user)
        proposal = EventProposal.objects.create(
            submitted_by=self.user, event_title="Sample"
        )
        self.report = EventReport.objects.create(proposal=proposal)
        AttendanceRow.objects.create(
            event_report=self.report,
            registration_no="R1",
            full_name="Bob",
            student_class="CSE",
            absent=False,
            volunteer=True,
        )
        AttendanceRow.objects.create(
            event_report=self.report,
            registration_no="R2",
            full_name="Eve",
            student_class="CSE",
            absent=True,
            volunteer=False,
        )

    def test_returns_rows_and_counts(self):
        url = reverse("emt:attendance_data", args=[self.report.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["rows"]), 2)
        self.assertEqual(data["counts"]["absent"], 1)
        self.assertEqual(data["counts"]["volunteers"], 1)

