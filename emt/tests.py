from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from emt.models import ApprovalStep, EventProposal
from emt.utils import (
    build_approval_chain,
    auto_approve_non_optional_duplicates,
    unlock_optionals_after,
    skip_all_downstream_optionals,
)
from core.models import (
    OrganizationType, Organization, OrganizationRole, RoleAssignment,
    Program, ProgramOutcome, ProgramSpecificOutcome,
    ApprovalFlowTemplate, ApprovalFlowConfig,
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


class ApprovalLogicTests(TestCase):
    def test_faculty_incharge_auto_skips_duplicate_approval(self):
        ot = OrganizationType.objects.create(name="Dept")
        org = Organization.objects.create(name="Sci", org_type=ot)

        fic_role = OrganizationRole.objects.create(
            organization=org, name=ApprovalStep.Role.FACULTY_INCHARGE.value
        )
        hod_role = OrganizationRole.objects.create(
            organization=org, name=ApprovalStep.Role.HOD.value
        )

        user = User.objects.create_user("u1", password="pass")
        RoleAssignment.objects.create(user=user, role=fic_role, organization=org)
        RoleAssignment.objects.create(user=user, role=hod_role, organization=org)

        ApprovalFlowConfig.objects.create(
            organization=org, require_faculty_incharge_first=True
        )
        ApprovalFlowTemplate.objects.create(
            organization=org,
            step_order=1,
            role_required=ApprovalStep.Role.HOD.value,
            user=user,
        )

        proposal = EventProposal.objects.create(
            submitted_by=user,
            organization=org,
            status=EventProposal.Status.SUBMITTED,
        )
        proposal.faculty_incharges.add(user)

        build_approval_chain(proposal)
        step1 = proposal.approval_steps.get(step_order=1)
        step2 = proposal.approval_steps.get(step_order=2)

        self.client.force_login(user)
        resp = self.client.post(
            reverse("emt:review_approval_step", args=[step1.id]),
            {"action": "approve"},
        )
        self.assertEqual(resp.status_code, 302)

        step2.refresh_from_db()
        self.assertEqual(step2.status, ApprovalStep.Status.APPROVED)
        self.assertEqual(
            step2.note,
            "Auto-approved (duplicate non-optional step for same approver).",
        )

    def test_optional_picker_display(self):
        ot = OrganizationType.objects.create(name="Dept")
        org = Organization.objects.create(name="Sci", org_type=ot)

        hod_role = OrganizationRole.objects.create(
            organization=org, name=ApprovalStep.Role.HOD.value
        )
        director_role = OrganizationRole.objects.create(
            organization=org, name=ApprovalStep.Role.DIRECTOR.value
        )

        hod = User.objects.create_user("hod", password="pass")
        director = User.objects.create_user("director", password="pass")
        RoleAssignment.objects.create(user=hod, role=hod_role, organization=org)
        RoleAssignment.objects.create(user=director, role=director_role, organization=org)

        ApprovalFlowTemplate.objects.create(
            organization=org,
            step_order=1,
            role_required=ApprovalStep.Role.HOD.value,
            user=hod,
        )
        ApprovalFlowTemplate.objects.create(
            organization=org,
            step_order=2,
            role_required=ApprovalStep.Role.DIRECTOR.value,
            user=director,
            optional=True,
        )

        proposal = EventProposal.objects.create(
            submitted_by=hod,
            organization=org,
            status=EventProposal.Status.SUBMITTED,
        )
        build_approval_chain(proposal)
        self.assertEqual(proposal.approval_steps.count(), 2)
        step = proposal.approval_steps.get(role_required=ApprovalStep.Role.HOD)

        self.client.force_login(hod)
        resp = self.client.get(reverse("emt:review_approval_step", args=[step.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["show_optional_picker"])
        ids = [s.id for s in resp.context["optional_candidates"]]
        self.assertIn(
            proposal.approval_steps.get(role_required=ApprovalStep.Role.DIRECTOR).id,
            ids,
        )


class ForwardingFlowTests(TestCase):
    def setUp(self):
        self.ot = OrganizationType.objects.create(name="Dept")
        self.org = Organization.objects.create(name="Sci", org_type=self.ot)
        self.user = User.objects.create_user("u", password="pass")
        self.user_b = User.objects.create_user("b", password="pass")
        self.user_c = User.objects.create_user("c", password="pass")
        for u in (self.user, self.user_b, self.user_c):
            if hasattr(u, "profile"):
                u.profile.role = "faculty"
                u.profile.save()

    def _create_proposal(self):
        return EventProposal.objects.create(
            submitted_by=self.user,
            organization=self.org,
            status=EventProposal.Status.SUBMITTED,
        )

    def test_auto_approve_duplicate_non_optional(self):
        proposal = self._create_proposal()
        step1 = ApprovalStep.objects.create(
            proposal=proposal,
            step_order=1,
            order_index=1,
            assigned_to=self.user,
            status=ApprovalStep.Status.PENDING,
        )
        step2 = ApprovalStep.objects.create(
            proposal=proposal,
            step_order=2,
            order_index=2,
            assigned_to=self.user,
            status="waiting",
        )
        auto_approve_non_optional_duplicates(proposal, self.user, self.user)
        step2.refresh_from_db()
        self.assertEqual(step2.status, ApprovalStep.Status.APPROVED)
        self.assertEqual(
            step2.note,
            "Auto-approved (duplicate non-optional step for same approver).",
        )

    def test_optional_step_skipped_without_forward(self):
        proposal = self._create_proposal()
        step1 = ApprovalStep.objects.create(
            proposal=proposal,
            step_order=1,
            order_index=1,
            assigned_to=self.user,
            status=ApprovalStep.Status.PENDING,
        )
        step2 = ApprovalStep.objects.create(
            proposal=proposal,
            step_order=2,
            order_index=2,
            assigned_to=self.user,
            is_optional=True,
            status=ApprovalStep.Status.PENDING,
        )
        skip_all_downstream_optionals(step1)
        step2.refresh_from_db()
        self.assertEqual(step2.status, ApprovalStep.Status.SKIPPED)

    def test_optional_step_unlocked_with_forward(self):
        proposal = self._create_proposal()
        step1 = ApprovalStep.objects.create(
            proposal=proposal,
            step_order=1,
            order_index=1,
            assigned_to=self.user,
            status=ApprovalStep.Status.PENDING,
        )
        step2 = ApprovalStep.objects.create(
            proposal=proposal,
            step_order=2,
            order_index=2,
            assigned_to=self.user,
            is_optional=True,
            status=ApprovalStep.Status.PENDING,
        )
        unlock_optionals_after(step1, [step2.id])
        step2.refresh_from_db()
        self.assertEqual(step2.status, ApprovalStep.Status.PENDING)
        self.assertTrue(step2.optional_unlocked)

    def test_optional_chain_forwarding(self):
        proposal = self._create_proposal()
        step1 = ApprovalStep.objects.create(
            proposal=proposal,
            step_order=1,
            order_index=1,
            assigned_to=self.user,
            status=ApprovalStep.Status.PENDING,
        )
        step2 = ApprovalStep.objects.create(
            proposal=proposal,
            step_order=2,
            order_index=2,
            assigned_to=self.user_b,
            is_optional=True,
            status=ApprovalStep.Status.PENDING,
        )
        step3 = ApprovalStep.objects.create(
            proposal=proposal,
            step_order=3,
            order_index=3,
            assigned_to=self.user_c,
            is_optional=True,
            status=ApprovalStep.Status.PENDING,
        )
        unlock_optionals_after(step1, [step2.id])
        skip_all_downstream_optionals(step2)
        step3.refresh_from_db()
        self.assertEqual(step3.status, ApprovalStep.Status.SKIPPED)

        proposal2 = self._create_proposal()
        s1 = ApprovalStep.objects.create(
            proposal=proposal2,
            step_order=1,
            order_index=1,
            assigned_to=self.user,
            status=ApprovalStep.Status.PENDING,
        )
        s2 = ApprovalStep.objects.create(
            proposal=proposal2,
            step_order=2,
            order_index=2,
            assigned_to=self.user_b,
            is_optional=True,
            status=ApprovalStep.Status.PENDING,
        )
        s3 = ApprovalStep.objects.create(
            proposal=proposal2,
            step_order=3,
            order_index=3,
            assigned_to=self.user_c,
            is_optional=True,
            status=ApprovalStep.Status.PENDING,
        )
        unlock_optionals_after(s1, [s2.id])
        unlock_optionals_after(s2, [s3.id])
        s3.refresh_from_db()
        self.assertEqual(s3.status, ApprovalStep.Status.PENDING)
        self.assertTrue(s3.optional_unlocked)

    def test_visible_for_ui_hides_locked_optional_steps(self):
        proposal = self._create_proposal()
        base = ApprovalStep.objects.create(
            proposal=proposal,
            step_order=1,
            order_index=1,
            assigned_to=self.user,
            status=ApprovalStep.Status.PENDING,
        )
        opt = ApprovalStep.objects.create(
            proposal=proposal,
            step_order=2,
            order_index=2,
            assigned_to=self.user_b,
            is_optional=True,
            status=ApprovalStep.Status.PENDING,
        )

        qs = (
            ApprovalStep.objects.filter(proposal=proposal)
            .order_by("order_index")
            .visible_for_ui()
        )
        self.assertEqual(list(qs), [base])

        opt.optional_unlocked = True
        opt.save()
        qs2 = (
            ApprovalStep.objects.filter(proposal=proposal)
            .order_by("order_index")
            .visible_for_ui()
        )
        self.assertEqual(list(qs2), [base, opt])

        opt.status = ApprovalStep.Status.SKIPPED
        opt.save()
        qs3 = (
            ApprovalStep.objects.filter(proposal=proposal)
            .order_by("order_index")
            .visible_for_ui()
        )
        self.assertEqual(list(qs3), [base])

    def test_visible_for_ui_hides_waiting_optional_steps(self):
        proposal = self._create_proposal()
        base = ApprovalStep.objects.create(
            proposal=proposal,
            step_order=1,
            order_index=1,
            assigned_to=self.user,
            status=ApprovalStep.Status.PENDING,
        )
        opt = ApprovalStep.objects.create(
            proposal=proposal,
            step_order=2,
            order_index=2,
            assigned_to=self.user_b,
            is_optional=True,
            status="waiting",
        )

        qs = (
            ApprovalStep.objects.filter(proposal=proposal)
            .order_by("order_index")
            .visible_for_ui()
        )
        self.assertEqual(list(qs), [base])

        opt.optional_unlocked = True
        opt.status = ApprovalStep.Status.PENDING
        opt.save()
        qs2 = (
            ApprovalStep.objects.filter(proposal=proposal)
            .order_by("order_index")
            .visible_for_ui()
        )
        self.assertEqual(list(qs2), [base, opt])
