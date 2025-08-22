from django.test import TestCase
from django.contrib.auth.models import User
from core.models import ActivityLog


class ActivityLogAutoDescriptionTests(TestCase):
    def test_generates_description_when_missing(self):
        user = User.objects.create_user('charlie')
        log = ActivityLog.objects.create(
            user=user,
            action='test_action',
            ip_address='1.2.3.4',
            metadata={'foo': 'bar'}
        )
        self.assertIn('charlie test action', log.description)
        self.assertIn('foo=bar', log.description)
        self.assertIn('1.2.3.4', log.description)
