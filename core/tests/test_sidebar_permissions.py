from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, AnonymousUser

from core.context_processors import sidebar_permissions
from core.models import SidebarPermission


class SidebarPermissionsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user("u", email="u@example.com", password="pass")

    def _request(self, user=None, session=None):
        request = self.factory.get("/")
        request.user = user or self.user
        request.session = session or {}
        return request

    def test_returns_empty_list_when_not_authenticated(self):
        request = self._request(user=AnonymousUser())
        ctx = sidebar_permissions(request)
        self.assertEqual(ctx["allowed_nav_items"], [])

    def test_user_specific_permission(self):
        SidebarPermission.objects.create(user=self.user, items=["dashboard"])
        request = self._request()
        ctx = sidebar_permissions(request)
        self.assertEqual(ctx["allowed_nav_items"], ["dashboard"])

    def test_role_based_permission(self):
        SidebarPermission.objects.create(role="student", items=["dashboard"])
        request = self._request(session={"role": "student"})
        ctx = sidebar_permissions(request)
        self.assertEqual(ctx["allowed_nav_items"], ["dashboard"])

    def test_superuser_bypasses_permissions(self):
        self.user.is_superuser = True
        self.user.save()
        SidebarPermission.objects.create(user=self.user, items=["dashboard"])
        request = self._request()
        ctx = sidebar_permissions(request)
        self.assertEqual(ctx["allowed_nav_items"], [])

    def test_admin_role_bypasses_permissions(self):
        SidebarPermission.objects.create(role="admin", items=["dashboard"])
        request = self._request(session={"role": "admin"})
        ctx = sidebar_permissions(request)
        self.assertEqual(ctx["allowed_nav_items"], [])
