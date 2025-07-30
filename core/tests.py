from django.test import TestCase
from django.contrib.auth.models import User
from django.forms import inlineformset_factory
import json
from .models import (
    OrganizationType,
    Organization,
    ApprovalFlowTemplate,
    OrganizationRole,
    RoleAssignment,
)
from .views import RoleAssignmentForm, RoleAssignmentFormSet


class OrganizationModelTests(TestCase):
    def test_create_organization(self):
        org_type = OrganizationType.objects.create(name="Department")
        org = Organization.objects.create(name="Math", org_type=org_type)

        self.assertEqual(Organization.objects.count(), 1)
        self.assertEqual(org.org_type.name, "Department")


class ApprovalFlowViewTests(TestCase):
    def test_delete_approval_flow(self):
        ot = OrganizationType.objects.create(name="Dept")
        org = Organization.objects.create(name="Math", org_type=ot)
        ApprovalFlowTemplate.objects.create(
            organization=org, step_order=1, role_required="faculty"
        )

        admin = User.objects.create_superuser("admin", "a@x.com", "pass")
        self.client.force_login(admin)

        resp = self.client.post(f"/core-admin/approval-flow/{org.id}/delete/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ApprovalFlowTemplate.objects.count(), 0)

    def test_save_approval_flow_forbidden_for_non_superuser(self):
        ot = OrganizationType.objects.create(name="Dept")
        org = Organization.objects.create(name="Math", org_type=ot)
        user = User.objects.create_user("user", "u@x.com", "pass")
        self.client.force_login(user)

        resp = self.client.post(
            f"/core-admin/approval-flow/{org.id}/save/",
            data=json.dumps({"steps": []}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)


class SaveApprovalFlowTests(TestCase):
    def setUp(self):
        self.ot = OrganizationType.objects.create(name="Dept")
        self.org = Organization.objects.create(name="Math", org_type=self.ot)

    def test_save_approval_flow_creates_steps(self):
        admin = User.objects.create_superuser("admin", "a@x.com", "pass")
        user1 = User.objects.create(username="u1")
        self.client.force_login(admin)

        steps = [
            {"role_required": "faculty"},
            {"role_required": "hod", "user_id": user1.id},
        ]

        resp = self.client.post(
            f"/core-admin/approval-flow/{self.org.id}/save/",
            data=json.dumps({"steps": steps}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

        templates = list(ApprovalFlowTemplate.objects.filter(organization=self.org).order_by("step_order"))
        self.assertEqual(len(templates), 2)
        self.assertEqual(templates[0].step_order, 1)
        self.assertEqual(templates[0].role_required, "faculty")
        self.assertIsNone(templates[0].user)
        self.assertEqual(templates[1].step_order, 2)
        self.assertEqual(templates[1].role_required, "hod")
        self.assertEqual(templates[1].user, user1)

    def test_save_approval_flow_forbidden_for_non_superuser(self):
        user = User.objects.create_user("user", "u@x.com", "pass")
        self.client.force_login(user)

        resp = self.client.post(
            f"/core-admin/approval-flow/{self.org.id}/save/",
            data=json.dumps({"steps": []}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)


class RoleManagementTests(TestCase):
    def test_add_role(self):
        ot = OrganizationType.objects.create(name="Dept")
        org = Organization.objects.create(name="Math", org_type=ot)
        admin = User.objects.create_superuser("admin", "a@x.com", "pass")
        self.client.force_login(admin)

        resp = self.client.post("/core-admin/user-roles/add/", {
            "org_id": org.id,
            "name": "Coordinator"
        })

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(OrganizationRole.objects.filter(organization=org, name="Coordinator").count(), 1)

    def test_add_role_to_org_type(self):
        ot = OrganizationType.objects.create(name="Club")
        org1 = Organization.objects.create(name="Art", org_type=ot)
        org2 = Organization.objects.create(name="Music", org_type=ot)
        admin = User.objects.create_superuser("admin", "a@x.com", "pass")
        self.client.force_login(admin)

        resp = self.client.post("/core-admin/user-roles/add/", {
            "org_type_id": ot.id,
            "name": "Coordinator",
        })

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            OrganizationRole.objects.filter(organization__org_type=ot, name="Coordinator").count(),
            2,
        )

    def test_duplicate_role_assignments_rejected(self):
        user = User.objects.create(username="u1")
        ot = OrganizationType.objects.create(name="Dept")
        org = Organization.objects.create(name="Math", org_type=ot)
        role_obj = OrganizationRole.objects.create(organization=org, name="hod")
        RoleAssignment.objects.create(user=user, role=role_obj, organization=org)

        RoleFormSet = inlineformset_factory(
            User,
            RoleAssignment,
            form=RoleAssignmentForm,
            formset=RoleAssignmentFormSet,
            fields=("role", "organization"),
            extra=0,
            can_delete=True,
        )

        data = {
            "role_assignments-TOTAL_FORMS": "2",
            "role_assignments-INITIAL_FORMS": "1",
            "role_assignments-MIN_NUM_FORMS": "0",
            "role_assignments-MAX_NUM_FORMS": "1000",
            "role_assignments-0-id": str(RoleAssignment.objects.first().id),
            "role_assignments-0-role": str(role_obj.id),
            "role_assignments-0-organization": str(org.id),
            "role_assignments-1-role": str(role_obj.id),
            "role_assignments-1-organization": str(org.id),
        }
        formset = RoleFormSet(data, instance=user)
        self.assertFalse(formset.is_valid())
        self.assertIn("Duplicate role assignment", formset.non_form_errors()[0])


class SearchUsersTests(TestCase):
    def setUp(self):
        self.ot = OrganizationType.objects.create(name="Dept")
        self.org = Organization.objects.create(name="Math", org_type=self.ot)
        self.role_obj = OrganizationRole.objects.create(organization=self.org, name="Faculty")
        self.user = User.objects.create(username="u1", first_name="Alpha", email="alpha@example.com")
        RoleAssignment.objects.create(user=self.user, role=self.role_obj, organization=self.org)
        self.admin = User.objects.create_superuser("admin", "admin@example.com", "pass")
        self.client.force_login(self.admin)

    def test_search_users_by_role(self):
        resp = self.client.get("/core-admin/api/search-users/", {
            "role": "faculty",
            "org_id": self.org.id,
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data.get("users", [])), 1)
        self.assertEqual(data["users"][0]["id"], self.user.id)


class ApprovalFlowTemplateDisplayTests(TestCase):
    def setUp(self):
        self.ot = OrganizationType.objects.create(name="Dept")
        self.org = Organization.objects.create(name="Math", org_type=self.ot)

    def test_get_role_required_display_uses_org_role(self):
        OrganizationRole.objects.create(organization=self.org, name="Faculty")
        step = ApprovalFlowTemplate.objects.create(
            organization=self.org, step_order=1, role_required="faculty"
        )
        self.assertEqual(step.get_role_required_display(), "Faculty")

    def test_get_role_required_display_formats_fallback(self):
        step = ApprovalFlowTemplate.objects.create(
            organization=self.org,
            step_order=1,
            role_required="committee_member",
        )
        self.assertEqual(step.get_role_required_display(), "Committee Member")

    def test_get_approval_flow_endpoint_returns_display(self):
        OrganizationRole.objects.create(organization=self.org, name="Faculty")
        ApprovalFlowTemplate.objects.create(
            organization=self.org, step_order=1, role_required="faculty"
        )
        resp = self.client.get(f"/core-admin/approval-flow/{self.org.id}/get/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["steps"][0]["role_display"], "Faculty")
