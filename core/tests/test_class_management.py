from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from core.models import OrganizationType, Organization, Class

class ClassManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        ot = OrganizationType.objects.create(name='Dept')
        self.org = Organization.objects.create(name='Math', org_type=ot)
        self.cls = Class.objects.create(name='A', code='A', organization=self.org)

    def test_class_toggle_archives(self):
        self.client.force_login(self.admin)
        url = reverse('admin_org_users_class_toggle', args=[self.org.id, self.cls.id])
        self.assertTrue(self.cls.is_active)
        self.client.post(url)
        self.cls.refresh_from_db()
        self.assertFalse(self.cls.is_active)

    def test_user_activate(self):
        user = User.objects.create_user('stud', 'stud@example.com', 'pass', is_active=False)
        self.client.force_login(self.admin)
        url = reverse('admin_user_activate', args=[user.id])
        self.client.post(url, {'next': '/'})
        user.refresh_from_db()
        self.assertTrue(user.is_active)
