from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in
import json
import csv

from core.signals import create_or_update_user_profile, assign_role_on_login
from core.models import OrganizationType, Organization, OrganizationRole, RoleAssignment

from emt.models import EventProposal, EventReport


class AudienceCSVViewTests(TestCase):
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
            target_audience="Bob, Carol",
        )

    def test_download_student_audience_csv(self):
        url = reverse("emt:download_audience_csv", args=[self.proposal.id]) + "?type=students"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        reader = csv.reader(response.content.decode().splitlines())
        rows = list(reader)
        self.assertEqual(
            rows[0],
            ["Registration No", "Full Name", "Class", "Absent", "Student Volunteer"],
        )
        self.assertEqual(rows[1][1], "Bob")
        self.assertEqual(rows[2][1], "Carol")
        self.assertEqual(len(rows[1]), 5)

    def test_download_faculty_audience_csv(self):
        url = reverse("emt:download_audience_csv", args=[self.proposal.id]) + "?type=faculty"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(
            "Employee No,Full Name,Department,Absent,Student Volunteer",
            content,
        )

    def test_api_faculty_returns_department(self):
        dept_type = OrganizationType.objects.create(name="Department")
        dept = Organization.objects.create(name="CSE", org_type=dept_type)
        role = OrganizationRole.objects.create(organization=dept, name="Faculty")
        faculty = User.objects.create_user(username="fac1", password="pass", first_name="John")
        RoleAssignment.objects.create(user=faculty, role=role, organization=dept)
        url = reverse("emt:api_faculty") + f"?org_id={dept.id}&q=fac1"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data[0]["department"], "CSE")

    def test_attendance_selection_saved(self):
        url = reverse("emt:submit_event_report", args=[self.proposal.id])
        notes = [
            {
                "number": "R1",
                "name": "Bob",
                "class_or_dept": "CSE",
                "absent": False,
                "student_volunteer": True,
            },
            {
                "number": "R2",
                "name": "Carol",
                "class_or_dept": "CSE",
                "absent": True,
                "student_volunteer": False,
            },
        ]
        data = {
            "actual_event_type": "Seminar",
            "report_signed_date": "2024-01-10",
            "num_activities": "0",
            "num_participants": "1",
            "num_student_volunteers": "1",
            "attendance_notes": json.dumps(notes),
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        report = EventReport.objects.get(proposal=self.proposal)
        saved = json.loads(report.attendance_notes)
        self.assertEqual(len(saved), 2)
        self.assertTrue(saved[0]["student_volunteer"])
        self.assertTrue(saved[1]["absent"])
        self.assertEqual(report.num_student_volunteers, 1)
        self.assertEqual(report.num_participants, 1)

