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


class AdminUserEditFormsetTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin", "admin@example.com", "pass")
        self.client.force_login(self.admin)
        # create a target user
        self.user = User.objects.create_user("tuser", password="pw")

    def test_post_all_deleted_role_forms_allowed(self):
        # Load edit page to get management form values
        url = reverse('admin_user_edit', args=[self.user.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        # Extract TOTAL_FORMS and construct POST where any existing forms are marked DELETE
        # For simplicity, post with zero total forms which should be acceptable
        post = {
            'first_name': 'T', 'last_name': 'User', 'email': 't@example.com',
            'roles-TOTAL_FORMS': '0', 'roles-INITIAL_FORMS': '0', 'roles-MIN_NUM_FORMS': '0', 'roles-MAX_NUM_FORMS': '1000'
        }
        # The exact prefix may vary; try common prefixes by inspecting rendered management form
        # Fallback: submit using the keys from the response content (search for name="-TOTAL_FORMS")
        import re
        m = re.search(r'name="(?P<prefix>[^\"]+-TOTAL_FORMS)" value="(?P<val>\d+)"', resp.content.decode('utf-8'))
        if m:
            full = m.group('prefix')
            prefix = full[: -len('-TOTAL_FORMS')]
            post = {'first_name': 'T', 'last_name': 'User', 'email': 't@example.com'}
            post[f'{prefix}-TOTAL_FORMS'] = '0'
            post[f'{prefix}-INITIAL_FORMS'] = '0'
            post[f'{prefix}-MIN_NUM_FORMS'] = '0'
            post[f'{prefix}-MAX_NUM_FORMS'] = '1000'

        resp2 = self.client.post(url, data=post)
        # Should redirect on success
        self.assertIn(resp2.status_code, (302, 303))


class NotificationsAPITests(TestCase):
    def setUp(self):
        from django.utils import timezone
        from emt.models import EventProposal
        self.admin = User.objects.create_superuser("admin2", "a2@example.com", "pw")
        self.client.force_login(self.admin)
        # create two proposals with different updated_at
        self.p1 = EventProposal.objects.create(submitted_by=self.admin, event_title='One', status=EventProposal.Status.SUBMITTED)
        self.p2 = EventProposal.objects.create(submitted_by=self.admin, event_title='Two', status=EventProposal.Status.REJECTED)
        # ensure p2 is newer
        from django.db import connection
        self.p1.updated_at = timezone.now() - timezone.timedelta(hours=2)
        self.p1.save()
        self.p2.updated_at = timezone.now()
        self.p2.save()

    def test_api_returns_newest_first_and_no_duplicates(self):
        url = reverse('api_get_notifications')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('notifications', data)
        notifs = data['notifications']
        # newest (p2) should be first
        self.assertGreaterEqual(len(notifs), 2)
        self.assertEqual(notifs[0]['title'], 'Two')
        # ids should be unique
        ids = [n.get('id') for n in notifs]
        self.assertEqual(len(ids), len(set(ids)))
