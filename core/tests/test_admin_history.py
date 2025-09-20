from datetime import timedelta
from types import SimpleNamespace

from bs4 import BeautifulSoup
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from core import signals
from core.middleware import ActivityLogMiddleware
from core.models import ActivityLog


class AdminHistoryFilterTests(TestCase):
    def setUp(self):
        post_save.disconnect(signals.create_or_update_user_profile, sender=User)
        user_logged_in.disconnect(signals.assign_role_on_login)
        self.admin = User.objects.create_superuser("admin", "admin@example.com", "pass")
        self.client.login(username="admin", password="pass")
        self.u1 = User.objects.create_user("alice")
        self.u2 = User.objects.create_user("bob")
        log1 = ActivityLog.objects.create(
            user=self.u1, action="login", description="first"
        )
        log1.timestamp = timezone.now() - timedelta(days=1)
        log1.save()
        self.log1 = log1
        self.log2 = ActivityLog.objects.create(
            user=self.u2, action="logout", description="second"
        )

    def tearDown(self):
        post_save.connect(signals.create_or_update_user_profile, sender=User)
        user_logged_in.connect(signals.assign_role_on_login)

    def test_search_filters_results(self):
        url = reverse("admin_history")
        resp = self.client.get(url, {"q": "logout"})
        self.assertContains(resp, "logout")
        self.assertNotContains(resp, "alice")

    def test_date_range_filters_results(self):
        url = reverse("admin_history")
        today = timezone.now().date().strftime("%Y-%m-%d")
        resp = self.client.get(url, {"start": today, "end": today})
        self.assertContains(resp, "logout")
        self.assertNotContains(resp, "alice")

    def test_shows_activity_for_all_users(self):
        """The admin page should expose actions for every user on the system."""

        # Add an explicit log entry for the admin to prove we don't filter on
        # the logged-in user.
        ActivityLog.objects.create(
            user=self.admin, action="reset", description="admin-only"
        )

        url = reverse("admin_history")
        resp = self.client.get(url)

        # Admin, alice and bob should all appear in the table.
        self.assertContains(resp, "admin")
        self.assertContains(resp, "reset")
        self.assertContains(resp, "alice")
        self.assertContains(resp, "login")
        self.assertContains(resp, "bob")
        self.assertContains(resp, "logout")


class AdminHistoryDescriptionTests(TestCase):
    def setUp(self):
        post_save.disconnect(signals.create_or_update_user_profile, sender=User)
        self.factory = RequestFactory()
        self.middleware = ActivityLogMiddleware(lambda request: HttpResponse("ok"))
        self.admin = User.objects.create_superuser("admin", "admin@example.com", "pass")
        self.client.login(username="admin", password="pass")

        request = self.factory.get("/admin/sites/site/?q=1")
        request.user = self.admin
        request.META["REMOTE_ADDR"] = "9.9.9.9"
        request.resolver_match = SimpleNamespace(
            view_name="admin:sites_site_changelist"
        )
        self.middleware(request)

    def tearDown(self):
        post_save.connect(signals.create_or_update_user_profile, sender=User)

    def test_sanitized_description_rendered(self):
        url = reverse("admin_history")
        resp = self.client.get(url)
        soup = BeautifulSoup(resp.content, "html.parser")
        desc_cell = soup.find(
            "td", string=lambda s: s and "admin viewed site list" in s
        )
        self.assertIsNotNone(desc_cell)
        self.assertNotIn("/admin/sites/site", desc_cell.text)
        self.assertNotIn("9.9.9.9", desc_cell.text)
