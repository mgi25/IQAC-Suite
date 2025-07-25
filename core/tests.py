from django.test import TestCase
from django.contrib.auth.models import User
from .models import (
    OrganizationType,
    Organization,
    ApprovalFlowTemplate,
    OrganizationRole,  # Ensure this exists in models.py
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
        ApprovalFlowTemplate.objects.create(
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
