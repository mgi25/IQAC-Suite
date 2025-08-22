from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.http import HttpResponse
from types import SimpleNamespace

from core.middleware import ActivityLogMiddleware
from core.models import ActivityLog
from core import signals


class ActivityLogMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        post_save.disconnect(signals.create_or_update_user_profile, sender=User)
        self.user = User.objects.create_user('alice', 'alice@example.com', 'pass')
        self.middleware = ActivityLogMiddleware(lambda request: HttpResponse("ok"))

    def tearDown(self):
        post_save.connect(signals.create_or_update_user_profile, sender=User)

    def test_creates_friendly_log_for_post_request(self):
        request = self.factory.post(
            '/contact/',
            {'foo': 'bar', 'csrfmiddlewaretoken': 'token'}
        )
        request.user = self.user
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.META['HTTP_USER_AGENT'] = 'TestAgent/1.0'
        request.resolver_match = SimpleNamespace(view_name='contact_form')
        request.object = SimpleNamespace(title='Feedback')

        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        log = ActivityLog.objects.get()
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, 'POST /contact/')
        self.assertEqual(log.ip_address, '127.0.0.1')
        self.assertEqual(log.metadata, {'foo': 'bar', 'object_title': 'Feedback'})
        self.assertEqual(
            log.description,
            'alice submitted contact form "Feedback"'
        )

    def test_creates_friendly_log_for_get_request(self):
        request = self.factory.get('/profile/', {'q': 'test'})
        request.user = self.user
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.META['HTTP_USER_AGENT'] = 'TestAgent/1.0'
        request.resolver_match = SimpleNamespace(view_name='profile')

        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        log = ActivityLog.objects.get()
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, 'GET /profile/')
        self.assertEqual(log.ip_address, '127.0.0.1')
        self.assertEqual(log.metadata, {'q': 'test'})
        self.assertEqual(log.description, 'alice viewed profile')


class AdminActivityLogMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        post_save.disconnect(signals.create_or_update_user_profile, sender=User)
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.middleware = ActivityLogMiddleware(lambda request: HttpResponse("ok"))

    def tearDown(self):
        post_save.connect(signals.create_or_update_user_profile, sender=User)

    def test_admin_get_request_has_friendly_description(self):
        request = self.factory.get('/admin/sites/site/')
        request.user = self.admin
        request.resolver_match = SimpleNamespace(view_name='admin:sites_site_changelist')

        self.middleware(request)
        log = ActivityLog.objects.get()
        self.assertEqual(log.description, 'admin viewed site list')

    def test_admin_post_request_has_friendly_description(self):
        request = self.factory.post('/admin/sites/site/add/', {})
        request.user = self.admin
        request.resolver_match = SimpleNamespace(view_name='admin:sites_site_add')

        self.middleware(request)
        log = ActivityLog.objects.get()
        self.assertEqual(log.description, 'admin added site')

    def test_noise_admin_endpoints_skipped(self):
        request = self.factory.get('/admin/jsi18n/')
        request.user = self.admin
        request.resolver_match = SimpleNamespace(view_name='admin:jsi18n')

        self.middleware(request)
        self.assertFalse(ActivityLog.objects.exists())
