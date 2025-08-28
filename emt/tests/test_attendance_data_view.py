from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Class
from emt.models import EventProposal, EventReport, AttendanceRow, Student


class AttendanceDataViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="pass")
        self.client.force_login(self.user)
        proposal = EventProposal.objects.create(
            submitted_by=self.user, event_title="Sample"
        )
        self.report = EventReport.objects.create(proposal=proposal)
        bob_user = User.objects.create_user("bobuser", password="pass", first_name="Bob")
        eve_user = User.objects.create_user("eveuser", password="pass", first_name="Eve")
        Student.objects.create(user=bob_user, registration_number="R1")
        Student.objects.create(user=eve_user, registration_number="R2")
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
        self.assertIn("CSE", data["students"])
        self.assertListEqual(sorted(data["students"]["CSE"]), ["Bob", "Eve"])
        self.assertEqual(data["faculty"], {})

    def test_returns_target_audience_when_no_rows(self):
        proposal = EventProposal.objects.create(
            submitted_by=self.user,
            event_title="Sample 2",
            target_audience="Bob, Carol",
        )
        report = EventReport.objects.create(proposal=proposal)
        cls = Class.objects.create(name="CSE", code="CSE")
        bob_user = User.objects.create_user("bobuser", password="pass", first_name="Bob")
        bob = Student.objects.create(user=bob_user, registration_number="R1")
        cls.students.add(bob)
        carol_user = User.objects.create_user(
            "caroluser", password="pass", first_name="Carol"
        )
        carol = Student.objects.create(user=carol_user, registration_number="R2")
        cls.students.add(carol)

        url = reverse("emt:attendance_data", args=[report.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["rows"]), 2)
        rows_by_name = {r["full_name"]: r for r in data["rows"]}
        self.assertEqual(rows_by_name["Bob"]["registration_no"], "R1")
        self.assertEqual(rows_by_name["Bob"]["student_class"], "CSE")
        self.assertEqual(rows_by_name["Carol"]["registration_no"], "R2")
        self.assertEqual(data["counts"]["total"], 2)
        self.assertEqual(data["counts"]["present"], 2)
        self.assertIn("CSE", data["students"])
        self.assertListEqual(sorted(data["students"]["CSE"]), ["Bob", "Carol"])

