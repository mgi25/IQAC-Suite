from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from core.models import ActivityLog

class AdminHistoryFilterTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.client.login(username='admin', password='pass')
        self.u1 = User.objects.create_user('alice')
        self.u2 = User.objects.create_user('bob')
        log1 = ActivityLog.objects.create(user=self.u1, action='login', description='first')
        log1.timestamp = timezone.now() - timedelta(days=1)
        log1.save()
        self.log1 = log1
        self.log2 = ActivityLog.objects.create(user=self.u2, action='logout', description='second')

    def test_search_filters_results(self):
        url = reverse('admin_history')
        resp = self.client.get(url, {'q': 'logout'})
        self.assertContains(resp, 'logout')
        self.assertNotContains(resp, 'alice')

    def test_date_range_filters_results(self):
        url = reverse('admin_history')
        today = timezone.now().date().strftime('%Y-%m-%d')
        resp = self.client.get(url, {'start': today, 'end': today})
        self.assertContains(resp, 'logout')
        self.assertNotContains(resp, 'alice')
