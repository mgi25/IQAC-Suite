from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in
import json

from core.signals import create_or_update_user_profile, assign_role_on_login
from emt.models import EventProposal, EventReport


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
        self.proposal = EventProposal.objects.create(
            submitted_by=self.user,
            event_title="Sample Event",
        )
        self.report = EventReport.objects.create(proposal=self.proposal)

    def test_save_attendance_updates_report(self):
        url = reverse("emt:attendance_save", args=[self.report.id])
        rows = [
            {
                "registration_no": "R1",
                "full_name": "Bob",
                "student_class": "CSE",
                "absent": False,
                "volunteer": True,
            },
            {
                "registration_no": "R2",
                "full_name": "Carol",
                "student_class": "ECE",
                "absent": True,
                "volunteer": False,
            },
        ]
        response = self.client.post(
            url,
            data=json.dumps({"rows": rows}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.report.refresh_from_db()
        self.assertEqual(self.report.num_participants, 1)
        self.assertEqual(self.report.num_student_volunteers, 1)
        saved = list(
            self.report.attendance_rows.order_by("registration_no").values(
                "registration_no", "absent", "volunteer"
            )
        )
        self.assertEqual(len(saved), 2)
        self.assertTrue(saved[0]["volunteer"])
        self.assertTrue(saved[1]["absent"])
