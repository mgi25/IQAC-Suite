from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.http import HttpResponse

from core.middleware import ActivityLogMiddleware
from core.models import ActivityLog


class ActivityLogMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user('alice', 'alice@example.com', 'pass')
        self.middleware = ActivityLogMiddleware(lambda request: HttpResponse("ok"))

    def test_creates_log_for_post_request(self):
        request = self.factory.post('/some/path', {'foo': 'bar', 'csrfmiddlewaretoken': 'token'})
        request.user = self.user
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        log = ActivityLog.objects.get()
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, 'POST /some/path')
        self.assertEqual(log.ip_address, '127.0.0.1')
        self.assertEqual(log.metadata, {'foo': 'bar'})
        self.assertEqual(log.description, 'foo=bar')

    def test_creates_log_for_get_request(self):
        request = self.factory.get('/some/path', {'q': 'test'})
        request.user = self.user
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        log = ActivityLog.objects.get()
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, 'GET /some/path')
        self.assertEqual(log.ip_address, '127.0.0.1')
        self.assertEqual(log.metadata, {'q': 'test'})
        self.assertEqual(log.description, 'q=test')
