from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.http import HttpResponse

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

    def test_creates_log_for_post_request(self):
        request = self.factory.post('/some/path', {'foo': 'bar', 'csrfmiddlewaretoken': 'token'})
        request.user = self.user
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.META['HTTP_USER_AGENT'] = 'TestAgent/1.0'

        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        log = ActivityLog.objects.get()
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, 'POST /some/path')
        self.assertEqual(log.ip_address, '127.0.0.1')
        self.assertEqual(log.metadata, {'foo': 'bar'})
        self.assertEqual(
            log.description,
            'User alice performed POST /some/path. Params: foo=bar. IP: 127.0.0.1. '
            'User-Agent: TestAgent/1.0. Status: 200'
        )

    def test_creates_log_for_get_request(self):
        request = self.factory.get('/some/path', {'q': 'test'})
        request.user = self.user
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.META['HTTP_USER_AGENT'] = 'TestAgent/1.0'

        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        log = ActivityLog.objects.get()
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, 'GET /some/path')
        self.assertEqual(log.ip_address, '127.0.0.1')
        self.assertEqual(log.metadata, {'q': 'test'})
        self.assertEqual(
            log.description,
            'User alice performed GET /some/path. Params: q=test. IP: 127.0.0.1. '
            'User-Agent: TestAgent/1.0. Status: 200'
        )
