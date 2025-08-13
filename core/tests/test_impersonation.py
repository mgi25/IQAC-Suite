from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from core.models import ImpersonationLog


class ImpersonationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.user = User.objects.create_user('alice', 'alice@example.com', 'pass')
        self.client.force_login(self.admin)

    def test_impersonation_flow(self):
        # start impersonation
        response = self.client.get(reverse('admin_impersonate_user', args=[self.user.id]))
        self.assertIn('impersonate_user_id', self.client.session)
        self.assertEqual(self.client.session['impersonate_user_id'], self.user.id)
        # request any page to trigger middleware
        resp = self.client.get(reverse('dashboard'))
        req = resp.wsgi_request
        self.assertTrue(req.is_impersonating)
        self.assertEqual(req.user, self.user)
        self.assertEqual(req.original_user, self.admin)
        # log entry created
        log = ImpersonationLog.objects.get()
        self.assertEqual(log.original_user, self.admin)
        self.assertEqual(log.impersonated_user, self.user)
        self.assertIsNone(log.ended_at)
        # stop impersonation
        self.client.get(reverse('stop_impersonation'))
        log.refresh_from_db()
        self.assertIsNotNone(log.ended_at)
