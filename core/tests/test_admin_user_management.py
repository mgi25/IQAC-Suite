from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from core.models import Class, Organization, OrganizationRole, OrganizationType


class AdminUserManagementRoleFilterTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin", "admin@example.com", "pass")
        self.client.force_login(self.admin)

        org_type = OrganizationType.objects.create(name="Department")
        self.org1 = Organization.objects.create(name="Org One", org_type=org_type)
        self.org2 = Organization.objects.create(name="Org Two", org_type=org_type)
        OrganizationRole.objects.create(organization=self.org1, name="Role A")
        OrganizationRole.objects.create(organization=self.org2, name="Role B")

    def test_roles_filtered_by_selected_organization(self):
        url = reverse("admin_user_management")
        resp = self.client.get(url, {"organization[]": str(self.org1.id)})
        self.assertContains(resp, "Role A")
        self.assertNotContains(resp, "Role B")


class AdminUserManagementRoleDisplayTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin", "admin@example.com", "pass")
        self.client.force_login(self.admin)

        org_type = OrganizationType.objects.create(name="Department")
        self.org = Organization.objects.create(name="Commerce", org_type=org_type)
        self.role = OrganizationRole.objects.create(
            organization=self.org, name="student"
        )

    def test_user_role_not_duplicated_when_assignment_exists(self):
        user = User.objects.create(username="student1", email="student1@example.com")
        # RoleAssignment created via bulk upload should replace profile role display
        from core.models import RoleAssignment

        RoleAssignment.objects.create(user=user, organization=self.org, role=self.role)

        url = reverse("admin_user_management")
        resp = self.client.get(url)
        self.assertContains(
            resp,
            '<span class="badge bg-primary">student</span>',
            count=1,
            html=True,
        )


class BulkUploadClassActivationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin", "admin@example.com", "pass")
        self.client.force_login(self.admin)

        org_type = OrganizationType.objects.create(name="Department")
        self.org = Organization.objects.create(name="Org One", org_type=org_type)
        OrganizationRole.objects.create(organization=self.org, name="student")

    def test_bulk_upload_reactivates_archived_class(self):
        cls = Class.objects.create(
            organization=self.org,
            code="BSc-A",
            name="BSc-A",
            academic_year="2025-2026",
            is_active=False,
        )

        csv_content = (
            "register_no,name,email,role\n"
            "23112001,Alen Jin Shibu,alen@example.com,student\n"
        ).encode("utf-8")
        upload = SimpleUploadedFile(
            "students.csv", csv_content, content_type="text/csv"
        )

        url = reverse("admin_org_users_upload_csv", args=[self.org.id])
        resp = self.client.post(
            url,
            {
                "class_name": "BSc-A",
                "academic_year": "2025-2026",
                "csv_file": upload,
            },
        )
        self.assertEqual(resp.status_code, 302)

        cls.refresh_from_db()
        self.assertTrue(cls.is_active)
