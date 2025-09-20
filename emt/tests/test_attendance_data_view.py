from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import (Class, Organization, OrganizationMembership,
                         OrganizationType)
from emt.models import AttendanceRow, EventProposal, EventReport, Student


class AttendanceDataViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="pass")
        self.client.force_login(self.user)
        proposal = EventProposal.objects.create(
            submitted_by=self.user, event_title="Sample"
        )
        self.report = EventReport.objects.create(proposal=proposal)
        bob_user = User.objects.create_user(
            "bobuser", password="pass", first_name="Bob"
        )
        eve_user = User.objects.create_user(
            "eveuser", password="pass", first_name="Eve"
        )
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
        rows_by_reg = {r["registration_no"]: r for r in data["rows"]}
        self.assertEqual(rows_by_reg["R1"]["category"], "student")
        self.assertEqual(rows_by_reg["R1"]["affiliation"], "CSE")

    def test_returns_target_audience_when_no_rows(self):
        proposal = EventProposal.objects.create(
            submitted_by=self.user,
            event_title="Sample 2",
            target_audience="Bob, Carol",
        )
        report = EventReport.objects.create(proposal=proposal)
        cls = Class.objects.create(name="CSE", code="CSE")
        bob_user = User.objects.create_user(
            "bobuser", password="pass", first_name="Bob"
        )
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

    def test_includes_faculty_incharges_when_no_rows(self):
        org_type = OrganizationType.objects.create(name="Dept of Arts")
        org = Organization.objects.create(name="Fine Arts", org_type=org_type)
        faculty_user = User.objects.create_user(
            "faclead",
            password="pass",
            first_name="Fiona",
            last_name="Lead",
        )
        faculty_user.profile.register_no = "FAC-900"
        faculty_user.profile.save()
        OrganizationMembership.objects.create(
            user=faculty_user,
            organization=org,
            academic_year="2024-2025",
            role="faculty",
        )

        proposal = EventProposal.objects.create(
            submitted_by=self.user,
            event_title="Faculty Seed",
        )
        proposal.faculty_incharges.add(faculty_user)
        report = EventReport.objects.create(proposal=proposal)

        url = reverse("emt:attendance_data", args=[report.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(len(data["rows"]), 1)
        row = data["rows"][0]
        self.assertEqual(row["registration_no"], "FAC-900")
        self.assertEqual(row["category"], "faculty")
        self.assertEqual(row["affiliation"], "Fine Arts")
        self.assertEqual(row["full_name"], "Fiona Lead")
        self.assertIn("Fine Arts", data["faculty"])
        self.assertIn("Fiona Lead", data["faculty"]["Fine Arts"])
        self.assertEqual(data["counts"]["total"], 1)
        self.assertEqual(data["counts"]["present"], 1)
        self.assertEqual(data["students"], {})

    def test_includes_faculty_incharges_with_existing_rows(self):
        org_type = OrganizationType.objects.create(name="Dept of Physics")
        org = Organization.objects.create(name="Physics", org_type=org_type)
        faculty_user = User.objects.create_user(
            "physlead",
            password="pass",
            first_name="Phil",
            last_name="Lead",
        )
        faculty_user.profile.register_no = "FAC-321"
        faculty_user.profile.save()
        OrganizationMembership.objects.create(
            user=faculty_user,
            organization=org,
            academic_year="2024-2025",
            role="faculty",
        )

        proposal = self.report.proposal
        proposal.faculty_incharges.add(faculty_user)

        url = reverse("emt:attendance_data", args=[self.report.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        rows_by_reg = {
            r["registration_no"]: r for r in data["rows"] if r.get("registration_no")
        }
        self.assertIn("FAC-321", rows_by_reg)
        row = rows_by_reg["FAC-321"]
        self.assertEqual(row["category"], "faculty")
        self.assertEqual(row["full_name"], "Phil Lead")
        self.assertEqual(row["affiliation"], "Physics")
        self.assertIn("Physics", data["faculty"])
        self.assertIn("Phil Lead", data["faculty"]["Physics"])

    def test_marks_faculty_rows_with_category(self):
        org_type = OrganizationType.objects.create(name="Dept")
        org = Organization.objects.create(name="Engineering", org_type=org_type)
        faculty_user = User.objects.create_user(
            "facuser", password="pass", first_name="Fac"
        )
        OrganizationMembership.objects.create(
            user=faculty_user,
            organization=org,
            academic_year="2024-2025",
            role="faculty",
        )
        faculty_user.profile.register_no = "FAC-001"
        faculty_user.profile.save()
        AttendanceRow.objects.create(
            event_report=self.report,
            registration_no="facuser",
            full_name="Fac Ulty",
            student_class="",
            absent=False,
            volunteer=False,
        )
        AttendanceRow.objects.create(
            event_report=self.report,
            registration_no="FAC-001",
            full_name="Fac Profile",
            student_class="",
            absent=False,
            volunteer=False,
        )

        url = reverse("emt:attendance_data", args=[self.report.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        rows_by_reg = {r["registration_no"]: r for r in data["rows"]}
        self.assertEqual(rows_by_reg["facuser"]["category"], "faculty")
        self.assertEqual(rows_by_reg["facuser"]["affiliation"], "Engineering")
        self.assertEqual(rows_by_reg["FAC-001"]["category"], "faculty")
        self.assertEqual(rows_by_reg["FAC-001"]["affiliation"], "Engineering")
        self.assertIn("Engineering", data["faculty"])
        self.assertIn("Fac Ulty", data["faculty"]["Engineering"])
        self.assertIn("Fac Profile", data["faculty"]["Engineering"])

    def test_faculty_row_without_name_uses_membership_display_name(self):
        org_type = OrganizationType.objects.create(name="Dept Faculty")
        org = Organization.objects.create(name="Science", org_type=org_type)
        faculty_user = User.objects.create_user(
            "facmissing",
            password="pass",
            first_name="Fiona",
            last_name="Faculty",
        )
        faculty_user.profile.register_no = "FAC-100"
        faculty_user.profile.save()
        OrganizationMembership.objects.create(
            user=faculty_user,
            organization=org,
            academic_year="2024-2025",
            role="faculty",
        )
        AttendanceRow.objects.create(
            event_report=self.report,
            registration_no="FAC-100",
            full_name="",
            student_class="",
            absent=False,
            volunteer=False,
            category=AttendanceRow.Category.FACULTY,
        )

        url = reverse("emt:attendance_data", args=[self.report.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        rows_by_reg = {r["registration_no"]: r for r in data["rows"]}
        self.assertEqual(rows_by_reg["FAC-100"]["full_name"], "Fiona Faculty")
        self.assertIn("Science", data["faculty"])
        self.assertIn("Fiona Faculty", data["faculty"]["Science"])

    def test_faculty_row_name_matching_registration_uses_membership_display(self):
        org_type = OrganizationType.objects.create(name="Dept Math")
        org = Organization.objects.create(name="Mathematics", org_type=org_type)
        faculty_user = User.objects.create_user(
            "facmatch",
            password="pass",
            first_name="Casey",
            last_name="Faculty",
        )
        faculty_user.profile.register_no = "FAC200"
        faculty_user.profile.save()
        OrganizationMembership.objects.create(
            user=faculty_user,
            organization=org,
            academic_year="2024-2025",
            role="faculty",
        )
        AttendanceRow.objects.create(
            event_report=self.report,
            registration_no="FAC200",
            full_name=" fac 200 ",
            student_class="",
            absent=False,
            volunteer=False,
            category=AttendanceRow.Category.FACULTY,
        )

        url = reverse("emt:attendance_data", args=[self.report.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        rows_by_reg = {r["registration_no"]: r for r in data["rows"]}
        self.assertEqual(rows_by_reg["FAC200"]["full_name"], "Casey Faculty")
        faculty_group = data["faculty"].get("Mathematics", [])
        self.assertListEqual(faculty_group, ["Casey Faculty"])

    def test_target_audience_faculty_name_uses_membership_details(self):
        org_type = OrganizationType.objects.create(name="Dept Humanities")
        org = Organization.objects.create(name="Humanities", org_type=org_type)
        faculty_user = User.objects.create_user(
            "henryfaculty",
            password="pass",
            first_name="Henry",
            last_name="Faculty",
        )
        OrganizationMembership.objects.create(
            user=faculty_user,
            organization=org,
            academic_year="2024-2025",
            role="faculty",
        )

        proposal = EventProposal.objects.create(
            submitted_by=self.user,
            event_title="Faculty Audience",
            target_audience="HenryFaculty",
        )
        report = EventReport.objects.create(proposal=proposal)

        url = reverse("emt:attendance_data", args=[report.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(len(data["rows"]), 1)
        row = data["rows"][0]
        self.assertEqual(row["category"], "faculty")
        self.assertEqual(row["affiliation"], "Humanities")
        self.assertEqual(row["student_class"], "Humanities")
        self.assertEqual(row["full_name"], "Henry Faculty")
        self.assertIn("Humanities", data["faculty"])
        self.assertIn("Henry Faculty", data["faculty"]["Humanities"])

    def test_target_audience_faculty_name_retained_with_existing_rows(self):
        org_type = OrganizationType.objects.create(name="Dept Social")
        org = Organization.objects.create(name="Social Sciences", org_type=org_type)
        faculty_user = User.objects.create_user(
            "henrysocial",
            password="pass",
            first_name="Henry",
            last_name="Faculty",
        )
        OrganizationMembership.objects.create(
            user=faculty_user,
            organization=org,
            academic_year="2024-2025",
            role="faculty",
        )

        proposal = self.report.proposal
        proposal.target_audience = "HenryFaculty"
        proposal.save(update_fields=["target_audience"])

        url = reverse("emt:attendance_data", args=[self.report.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        matching_rows = [r for r in data["rows"] if r["full_name"] == "Henry Faculty"]
        self.assertTrue(matching_rows)
        row = matching_rows[0]
        self.assertEqual(row["category"], "faculty")
        self.assertEqual(row["affiliation"], "Social Sciences")
        self.assertIn("Social Sciences", data["faculty"])
        self.assertIn("Henry Faculty", data["faculty"]["Social Sciences"])
