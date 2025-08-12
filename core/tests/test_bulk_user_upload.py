from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.messages import get_messages

from core.models import (
    OrganizationType,
    Organization,
    OrganizationRole,
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
        user.set_password('pass')
        user.save(update_fields=['password'])

        user_client = Client()
        session = user_client.session
        session['org_id'] = self.org.id
        session.save()

        self.assertTrue(user_client.login(username='john@example.com', password='pass'))
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertEqual(user.profile.role, 'student')
        self.assertEqual(user_client.session['role'], 'student')
