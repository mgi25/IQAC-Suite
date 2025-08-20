from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client
from django.urls import reverse

from core.context_processors import sidebar_permissions
from core.models import SidebarPermission


class SidebarPermissionsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _get_request(self, user):
        request = self.factory.get("/")
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        request.user = user
        return request

    def test_superuser_bypasses_sidebar_permission(self):
        """Superusers should ignore any stored sidebar permissions."""
        user = User.objects.create_user("super", password="pass", is_superuser=True)
        SidebarPermission.objects.create(user=user, items=["dashboard"])

        request = self._get_request(user)
        result = sidebar_permissions(request)

        self.assertEqual(result["allowed_nav_items"], [])

    def test_admin_role_bypasses_sidebar_permission(self):
        """Users with admin role should bypass sidebar restrictions."""
        user = User.objects.create_user("regular", password="pass")
        SidebarPermission.objects.create(role="admin", items=["dashboard"])

        request = self._get_request(user)
        request.session["role"] = "admin"
        result = sidebar_permissions(request)

        self.assertEqual(result["allowed_nav_items"], [])

    def test_user_permission_applied(self):
        """Explicit user permissions should be returned."""
        user = User.objects.create_user("alice", password="pass")
        SidebarPermission.objects.create(user=user, items=["dashboard"])

        request = self._get_request(user)
        result = sidebar_permissions(request)

        self.assertEqual(result["allowed_nav_items"], ["dashboard"])

    def test_role_permission_applied(self):
        """Role permissions should apply when user has none."""
        user = User.objects.create_user("bob", password="pass")
        SidebarPermission.objects.create(role="faculty", items=["events"])

        request = self._get_request(user)
        request.session["role"] = "faculty"
        result = sidebar_permissions(request)

        self.assertEqual(result["allowed_nav_items"], ["events"])

    def test_user_permission_overrides_role(self):
        """User-specific permissions override role permissions."""
        user = User.objects.create_user("carol", password="pass")
        SidebarPermission.objects.create(role="faculty", items=["events"])
        SidebarPermission.objects.create(user=user, items=["dashboard"])

        request = self._get_request(user)
        request.session["role"] = "faculty"
        result = sidebar_permissions(request)

        self.assertEqual(result["allowed_nav_items"], ["dashboard"])


class SidebarPermissionsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser("admin", "admin@example.com", "pass")
        self.client.login(username="admin", password="pass")

    def test_assign_permission_to_user(self):
        target = User.objects.create_user("dave", password="pass")
        url = reverse("admin_sidebar_permissions")
        response = self.client.post(url, {"user": str(target.id), "items": ["dashboard", "events"]})
        self.assertEqual(response.status_code, 302)
        self.assertIn(f"?user={target.id}", response["Location"])
        perm = SidebarPermission.objects.get(user=target)
        self.assertEqual(perm.items, ["dashboard", "events"])
