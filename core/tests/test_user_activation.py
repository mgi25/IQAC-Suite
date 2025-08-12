from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone


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
        login_success = user_client.login(username='newuser', password='pass')
        self.assertTrue(login_success)

        user.refresh_from_db()
        user.profile.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertIsNotNone(user.profile.activated_at)

        resp = self.client.get(reverse('admin_user_management') + '?q=newuser')
        self.assertContains(resp, 'Active')

    def test_deactivated_user_cannot_login(self):
        user = User.objects.create_user('olduser', email='old@example.com', password='pass', is_active=False)
        user.profile.activated_at = timezone.now()
        user.profile.save(update_fields=['activated_at'])

        user_client = Client()
        self.assertFalse(user_client.login(username='olduser', password='pass'))
