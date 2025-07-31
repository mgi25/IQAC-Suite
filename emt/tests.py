from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from emt.models import ApprovalStep
from core.models import (
    OrganizationType, Organization, OrganizationRole, RoleAssignment,
    Program, ProgramOutcome, ProgramSpecificOutcome,
)

class FacultyAPITests(TestCase):
    def setUp(self):
        self.ot = OrganizationType.objects.create(name="Dept")
        self.org = Organization.objects.create(name="Science", org_type=self.ot)
        self.faculty_role = OrganizationRole.objects.create(
            organization=self.org, name=ApprovalStep.Role.FACULTY.value
        )
        self.faculty_incharge_role = OrganizationRole.objects.create(
            organization=self.org, name=ApprovalStep.Role.FACULTY_INCHARGE.value
        )
        self.user1 = User.objects.create(
            username="f1", first_name="Alpha", email="alpha@example.com"
        )
        self.user2 = User.objects.create(
            username="f2", first_name="Beta", email="beta@example.com"
        )
        RoleAssignment.objects.create(
            user=self.user1, role=self.faculty_role, organization=self.org
        )
        RoleAssignment.objects.create(
            user=self.user2, role=self.faculty_incharge_role, organization=self.org
        )
        self.admin = User.objects.create_superuser(
            "admin", "admin@example.com", "pass"
        )
        self.client.force_login(self.admin)

    def test_api_faculty_returns_faculty_like_roles(self):
        resp = self.client.get(reverse("emt:api_faculty"), {"q": ""})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        ids = {item["id"] for item in data}
        self.assertIn(self.user1.id, ids)
        self.assertIn(self.user2.id, ids)


    def test_api_faculty_matches_capitalized_roles(self):
        user4 = User.objects.create(
            username="f4",
            first_name="Delta",
            email="delta@example.com",
        )
        cap_role = OrganizationRole.objects.create(
            organization=self.org,
            name="Faculty",
        )
        RoleAssignment.objects.create(
            user=user4,
            role=cap_role,
            organization=self.org,
        )

        resp = self.client.get(reverse("emt:api_faculty"), {"q": "Delta"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        ids = {item["id"] for item in data}
        self.assertIn(user4.id, ids)


class OutcomesAPITests(TestCase):
    def setUp(self):
        self.ot = OrganizationType.objects.create(name="Dept")
        self.org = Organization.objects.create(name="Science", org_type=self.ot)
        program = Program.objects.create(name="Prog", organization=self.org)
        self.po = ProgramOutcome.objects.create(program=program, description="PO1")
        self.pso = ProgramSpecificOutcome.objects.create(program=program, description="PSO1")
        self.user = User.objects.create(username="user")
        self.client.force_login(self.user)

    def test_api_outcomes_returns_outcomes(self):
        resp = self.client.get(reverse("emt:api_outcomes", args=[self.org.id]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["pos"]), 1)
        self.assertEqual(len(data["psos"]), 1)
        self.assertEqual(data["pos"][0]["description"], self.po.description)
