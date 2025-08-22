from django.test import TestCase
from django.contrib.auth.models import User
from core.models import ActivityLog


class ActivityLogAutoDescriptionTests(TestCase):
    def test_generates_description_when_missing(self):
        user = User.objects.create_user('charlie')
        log = ActivityLog.objects.create(
            user=user,
            action='GET /events/123/?next=/foo',
            ip_address='1.2.3.4',
            metadata={'foo': 'bar'}
        )
        # Description should be friendly and omit technical details
        self.assertEqual(log.description, 'charlie viewed events')
        self.assertNotIn('foo=bar', log.description)
        self.assertNotIn('1.2.3.4', log.description)
        self.assertNotIn('123', log.description)
