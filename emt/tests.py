from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from emt.models import ApprovalStep, EventProposal
from core.models import (
    OrganizationType, Organization, OrganizationRole, RoleAssignment,
    Program, ProgramOutcome, ProgramSpecificOutcome,
)
import json

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

    def test_api_faculty_accepts_incharge_variants(self):
        user5 = User.objects.create(
            username="f5",
            first_name="Epsilon",
            email="epsilon@example.com",
        )
        variant_role = OrganizationRole.objects.create(
            organization=self.org,
            name="Faculty Incharge",
        )
        RoleAssignment.objects.create(
            user=user5,
            role=variant_role,
            organization=self.org,
        )

        resp = self.client.get(reverse("emt:api_faculty"), {"q": "Epsilon"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        ids = {item["id"] for item in data}
        self.assertIn(user5.id, ids)


class OutcomesAPITests(TestCase):
    def setUp(self):
        self.ot = OrganizationType.objects.create(name="Dept")
        self.org = Organization.objects.create(name="Science", org_type=self.ot)
        program = Program.objects.create(name="Prog", organization=self.org)
        self.po = ProgramOutcome.objects.create(program=program, description="PO1")
        self.pso = ProgramSpecificOutcome.objects.create(program=program, description="PSO1")
        self.user = User.objects.create(username="user")
        RoleAssignment.objects.create(
            user=self.user,
            role=OrganizationRole.objects.create(
                organization=self.org, name="Member"
            ),
            organization=self.org,
        )
        self.client.force_login(self.user)

    def test_api_outcomes_returns_outcomes(self):
        resp = self.client.get(reverse("emt:api_outcomes", args=[self.org.id]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["pos"]), 1)
        self.assertEqual(len(data["psos"]), 1)
        self.assertEqual(data["pos"][0]["description"], self.po.description)


class AutosaveProposalTests(TestCase):
    def setUp(self):
        self.ot = OrganizationType.objects.create(name="Dept")
        self.org = Organization.objects.create(name="Science", org_type=self.ot)
        self.faculty_role = OrganizationRole.objects.create(
            organization=self.org, name=ApprovalStep.Role.FACULTY.value
        )
        self.submitter = User.objects.create_user("creator", password="pass")
        self.f1 = User.objects.create(username="f1", first_name="Alpha")
        self.f2 = User.objects.create(username="f2", first_name="Beta")
        RoleAssignment.objects.create(
            user=self.f1, role=self.faculty_role, organization=self.org
        )
        RoleAssignment.objects.create(
            user=self.f2, role=self.faculty_role, organization=self.org
        )
        RoleAssignment.objects.create(
            user=self.submitter, role=self.faculty_role, organization=self.org
        )
        self.client.force_login(self.submitter)

    def _payload(self):
        return {
            "organization_type": str(self.ot.id),
            "organization": str(self.org.id),
            "academic_year": "2024-2025",
            "faculty_incharges": [str(self.f1.id), str(self.f2.id)],
        }

    def test_autosave_and_submit_retains_faculty(self):
        resp = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        pid = resp.json()["proposal_id"]
        proposal = EventProposal.objects.get(id=pid)
        ids = set(proposal.faculty_incharges.values_list("id", flat=True))
        self.assertEqual(ids, {self.f1.id, self.f2.id})

        get_resp = self.client.get(reverse("emt:submit_proposal_with_pk", args=[pid]))
        content = get_resp.content.decode()
        self.assertIn(f'value="{self.f1.id}" selected', content)
        self.assertIn(f'value="{self.f2.id}" selected', content)

        post_data = self._payload()
        post_data["final_submit"] = "1"
        resp2 = self.client.post(reverse("emt:submit_proposal_with_pk", args=[pid]), post_data)
        self.assertEqual(resp2.status_code, 302)
        proposal.refresh_from_db()
        ids_after = set(proposal.faculty_incharges.values_list("id", flat=True))
        self.assertEqual(ids_after, {self.f1.id, self.f2.id})
        self.assertEqual(proposal.status, EventProposal.Status.SUBMITTED)


class EventApprovalsNavTests(TestCase):
    def setUp(self):
        self.faculty = User.objects.create_user("faculty", password="pass")
        self.student = User.objects.create_user("student", password="pass")
        ot = OrganizationType.objects.create(name="Dept")
        org = Organization.objects.create(name="Science", org_type=ot)
        fac_role = OrganizationRole.objects.create(
            organization=org, name=ApprovalStep.Role.FACULTY.value
        )
        student_role = OrganizationRole.objects.create(
            organization=org, name="Student"
        )
        RoleAssignment.objects.create(
            user=self.faculty, role=fac_role, organization=org
        )
        RoleAssignment.objects.create(
            user=self.student, role=student_role, organization=org
        )

    def _set_role(self, role):
        session = self.client.session
        session["role"] = role
        session.save()

    def test_faculty_sees_event_approvals_link(self):
        self.client.force_login(self.faculty)
        self._set_role("faculty")
        resp = self.client.get(reverse("dashboard"))
        self.assertContains(resp, "Event Approvals")
        self.assertContains(resp, reverse("emt:my_approvals"))
        approvals = self.client.get(reverse("emt:my_approvals"))
        self.assertEqual(approvals.status_code, 200)

    def test_student_does_not_see_event_approvals_link(self):
        self.client.force_login(self.student)
        self._set_role("student")
        resp = self.client.get(reverse("dashboard"))
        self.assertNotContains(resp, "Event Approvals")
