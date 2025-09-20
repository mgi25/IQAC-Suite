import json

from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.test import TestCase
from django.urls import reverse

from core.models import Organization, OrganizationMembership, OrganizationType
from core.signals import assign_role_on_login, create_or_update_user_profile
from emt.models import EventProposal, EventReport, Student


class SaveAttendanceRowsTests(TestCase):
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

        org_type = OrganizationType.objects.create(name="Dept")
        self.organization = Organization.objects.create(name="Org", org_type=org_type)
        self.proposal = EventProposal.objects.create(
            submitted_by=self.user,
            event_title="Sample Event",
            organization=self.organization,
        )
        self.report = EventReport.objects.create(proposal=self.proposal)

        # Participants used in attendance rows
        student_user = User.objects.create_user(username="S1", password="pass")
        Student.objects.create(user=student_user, registration_number="S1")
        faculty_user = User.objects.create_user(username="F1", password="pass")
        OrganizationMembership.objects.create(
            user=faculty_user,
            organization=self.organization,
            academic_year="2024-2025",
            role="faculty",
        )

    def test_save_attendance_updates_report(self):
        url = reverse("emt:attendance_save", args=[self.report.id])
        rows = [
            {
                "registration_no": "S1",
                "full_name": "Stu Dent",
                "student_class": "CSE",
                "absent": False,
                "volunteer": True,
                "category": "student",
            },
            {
                "registration_no": "F1",
                "full_name": "Fac Ulty",
                "student_class": "",
                "absent": False,
                "volunteer": False,
                "category": "faculty",
            },
            {
                "registration_no": "",
                "full_name": "Ext Person",
                "student_class": "",
                "absent": False,
                "volunteer": False,
                "category": "external",
            },
            {
                "registration_no": "A1",
                "full_name": "Ab Sent",
                "student_class": "ECE",
                "absent": True,
                "volunteer": False,
                "category": "student",
            },
        ]
        response = self.client.post(
            url,
            data=json.dumps({"rows": rows}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.report.refresh_from_db()
        self.assertEqual(self.report.num_participants, 3)
        self.assertEqual(self.report.num_student_volunteers, 1)
        self.assertEqual(self.report.num_student_participants, 1)
        self.assertEqual(self.report.num_faculty_participants, 1)
        self.assertEqual(self.report.num_external_participants, 1)

        saved = {
            r["registration_no"]: r
            for r in self.report.attendance_rows.values(
                "registration_no", "absent", "volunteer", "category"
            )
            if r["registration_no"]
        }
        self.assertTrue(saved["S1"]["volunteer"])
        self.assertTrue(saved["A1"]["absent"])
        self.assertEqual(saved["F1"]["category"], "faculty")
        self.assertEqual(len(saved), 3)  # empty registration_no excluded from keys

    def test_save_attendance_updates_session_draft(self):
        url = reverse("emt:attendance_save", args=[self.report.id])
        session = self.client.session
        session["event_report_draft"] = {str(self.proposal.id): {}}
        session.save()

        rows = [
            {
                "registration_no": "S1",
                "full_name": "Stu Dent",
                "student_class": "CSE",
                "absent": False,
                "volunteer": True,
                "category": "student",
            },
            {
                "registration_no": "F1",
                "full_name": "Fac Ulty",
                "student_class": "",
                "absent": False,
                "volunteer": False,
                "category": "faculty",
            },
            {
                "registration_no": "",
                "full_name": "Ext Person",
                "student_class": "",
                "absent": False,
                "volunteer": False,
                "category": "external",
            },
            {
                "registration_no": "A1",
                "full_name": "Ab Sent",
                "student_class": "ECE",
                "absent": True,
                "volunteer": False,
                "category": "student",
            },
        ]
        self.client.post(
            url,
            data=json.dumps({"rows": rows}),
            content_type="application/json",
        )
        session = self.client.session
        draft = session["event_report_draft"][str(self.proposal.id)]
        self.assertEqual(draft["num_participants"], 3)
        self.assertEqual(draft["num_student_volunteers"], 1)
        self.assertEqual(draft["num_student_participants"], 1)
        self.assertEqual(draft["num_faculty_participants"], 1)
        self.assertEqual(draft["num_external_participants"], 1)
