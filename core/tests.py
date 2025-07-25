from django.test import TestCase

from django.contrib.auth.models import User
from .models import (
    OrganizationType,
    Organization,
    ApprovalFlowTemplate,
    OrganizationRole,
)


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
        step = ApprovalFlowTemplate.objects.create(
            organization=org, step_order=1, role_required="faculty"
        )

        admin = User.objects.create_superuser("admin", "a@x.com", "pass")
        self.client.force_login(admin)
        resp = self.client.post(f"/core-admin/approval-flow/{org.id}/delete/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ApprovalFlowTemplate.objects.count(), 0)


class RoleManagementTests(TestCase):
    def test_add_role(self):
        ot = OrganizationType.objects.create(name="Dept")
        admin = User.objects.create_superuser("admin", "a@x.com", "pass")
        self.client.force_login(admin)
        resp = self.client.post("/core-admin/user-roles/add/", {"org_type_id": ot.id, "name": "Coordinator"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(OrganizationRole.objects.filter(org_type=ot, name="Coordinator").count(), 1)


class AdminViewsTests(TestCase):
    def test_role_management_access_control(self):
        user = User.objects.create_user("u", "u@x.com", "p")
        self.client.force_login(user)
        resp = self.client.get("/core-admin/user-roles/")
        self.assertEqual(resp.status_code, 302)

    def test_role_management_superuser(self):
        admin = User.objects.create_superuser("admin", "a@x.com", "pass")
        self.client.force_login(admin)
        resp = self.client.get("/core-admin/user-roles/")
        self.assertEqual(resp.status_code, 200)
