from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.messages import get_messages

from core.models import (
    OrganizationType,
    Organization,
    OrganizationRole,
    OrganizationMembership,
    RoleAssignment,
)


class BulkUserUploadTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        org_type = OrganizationType.objects.create(name='Dept')
        self.org = Organization.objects.create(name='Science', org_type=org_type)
        self.student_role = OrganizationRole.objects.create(organization=self.org, name='student')

    def _upload(self):
        csv_content = (
            "register_no,name,email,role\n"
            "001,John Doe,john@example.com,student\n"
            "002,Jane Doe,jane@example.com,ghost\n"
        )
        file = SimpleUploadedFile('users.csv', csv_content.encode('utf-8'), content_type='text/csv')
        url = reverse('admin_org_users_upload_csv', args=[self.org.id])
        data = {
            'class_name': 'A',
            'academic_year': '2024-2025',
            'csv_file': file,
        }
        referer = f'http://testserver/core-admin/org-users/{self.org.id}/students/'
        return self.client.post(url, data, follow=True, HTTP_REFERER=referer)

    def test_upload_and_login_flow(self):
        self.client.force_login(self.admin)
        response = self._upload()

        # warning for invalid role
        warnings = [m.message for m in get_messages(response.wsgi_request) if m.level_tag == 'warning']
        self.assertTrue(any('role' in msg.lower() for msg in warnings))

        # valid user exists but inactive
        user = User.objects.get(username='john@example.com')
        self.assertFalse(user.is_active)
        ra = RoleAssignment.objects.get(user=user, organization=self.org)
        self.assertEqual(ra.role, self.student_role)
        # invalid row skipped
        self.assertFalse(User.objects.filter(username='jane@example.com').exists())

        # simulate first login
        self.client.logout()
        session = self.client.session
        session['org_id'] = self.org.id
        session.save()
        self.client.force_login(user)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertEqual(user.profile.role, 'student')
        self.assertEqual(self.client.session['role'], 'student')


class BulkFacultyUploadTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        org_type = OrganizationType.objects.create(name='Dept')
        self.org = Organization.objects.create(name='Science', org_type=org_type)
        self.faculty_role = OrganizationRole.objects.create(organization=self.org, name='faculty')

    def _upload(self):
        csv_content = (
            "emp_id,name,email,role\n"
            "EMP1,Prof One,prof1@example.com,faculty\n"
        )
        file = SimpleUploadedFile('faculty.csv', csv_content.encode('utf-8'), content_type='text/csv')
        url = reverse('admin_org_users_upload_csv', args=[self.org.id])
        data = {
            'academic_year': '2024-2025',
            'csv_file': file,
        }
        referer = f'http://testserver/core-admin/org-users/{self.org.id}/faculty/'
        return self.client.post(url, data, follow=True, HTTP_REFERER=referer)

    def test_upload_and_archive_flow(self):
        self.client.force_login(self.admin)
        self._upload()

        user = User.objects.get(username='prof1@example.com')
        mem = user.org_memberships.get(organization=self.org)
        self.assertTrue(mem.is_active)

        # Toggle archive
        toggle_url = reverse('admin_org_users_faculty_toggle', args=[self.org.id, mem.id])
        self.client.post(toggle_url)
        mem.refresh_from_db()
        self.assertFalse(mem.is_active)

        # Ensure in archived list
        resp = self.client.get(reverse('admin_org_users_faculty', args=[self.org.id]) + '?archived=1')
        self.assertContains(resp, 'Prof One')
