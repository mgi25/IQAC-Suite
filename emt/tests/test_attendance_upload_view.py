import csv
import json
from io import StringIO

from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.signals import post_save
from django.test import TestCase
from django.urls import reverse

from core.models import Organization, OrganizationType
from core.signals import create_or_update_user_profile, assign_role_on_login
from emt.models import EventProposal, EventReport


class UploadAttendanceCsvViewTests(TestCase):
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
        self.user = User.objects.create_user(username="upload", password="pass")
        self.client.force_login(self.user)

        org_type = OrganizationType.objects.create(name="Dept")
        organization = Organization.objects.create(name="Org", org_type=org_type)
        proposal = EventProposal.objects.create(
            submitted_by=self.user,
            event_title="Upload Test Event",
            organization=organization,
        )
        self.report = EventReport.objects.create(proposal=proposal)

    def _build_combined_csv(self, total_rows=101, faculty_index=-1):
        """Create a CSV payload with a faculty row at the desired index."""
        data = StringIO()
        writer = csv.writer(data)
        writer.writerow(
            [
                "Category",
                "Identifier",
                "Full Name",
                "Affiliation",
                "Absent",
                "Student Volunteer",
            ]
        )

        for idx in range(total_rows):
            if idx == faculty_index or (faculty_index < 0 and idx == total_rows - 1):
                writer.writerow(
                    [
                        "faculty",
                        f"FAC{idx}",
                        f"Faculty {idx}",
                        "Dept",
                        "FALSE",
                        "FALSE",
                    ]
                )
            else:
                writer.writerow(
                    [
                        "student",
                        f"STU{idx}",
                        f"Student {idx}",
                        "Class",
                        "FALSE",
                        "FALSE",
                    ]
                )

        data.seek(0)
        return SimpleUploadedFile(
            "attendance.csv", data.getvalue().encode("utf-8"), content_type="text/csv"
        )

    def test_uploaded_rows_include_faculty_beyond_first_page(self):
        url = reverse("emt:attendance_upload", args=[self.report.id])
        upload = self._build_combined_csv(total_rows=101)

        response = self.client.post(url, {"csv_file": upload})
        self.assertEqual(response.status_code, 200)

        rows = json.loads(response.context["rows_json"])
        self.assertEqual(len(rows), 101)
        self.assertEqual(rows[-1]["category"], "faculty")
        self.assertEqual(response.context["counts"]["total"], 101)
