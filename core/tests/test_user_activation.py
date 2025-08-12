from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse


class UserActivationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.client.force_login(self.admin)

    def test_user_inactive_until_first_login(self):
        user = User.objects.create_user(
            'newuser', email='new@example.com', password='pass', is_active=False
        )
        self.assertFalse(user.is_active)
        self.assertIsNone(user.profile.activated_at)

        resp = self.client.get(reverse('admin_user_management') + '?q=newuser')
        self.assertContains(resp, 'Inactive')

        user_client = Client()
        user_client.force_login(user)

        user.refresh_from_db()
        user.profile.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertIsNotNone(user.profile.activated_at)

        resp = self.client.get(reverse('admin_user_management') + '?q=newuser')
        self.assertContains(resp, 'Active')
