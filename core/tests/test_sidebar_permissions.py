from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client
from django.urls import reverse
import json

from core.context_processors import sidebar_permissions
from core.models import SidebarPermission
from core.navigation import SIDEBAR_ITEM_IDS


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

    def test_role_permission_case_insensitive(self):
        """Role matching should ignore case."""
        user = User.objects.create_user("eve", password="pass")
        SidebarPermission.objects.create(role="faculty", items=["events"])

        request = self._get_request(user)
        request.session["role"] = "Faculty"  # Mixed case
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

    def test_stale_user_role_record_ignored(self):
        """A user-specific record with a role should not override role defaults."""
        role_items = ["events"]
        SidebarPermission.objects.create(role="faculty", items=role_items)
        user = User.objects.create_user("erin", password="pass")
        SidebarPermission.objects.create(
            user=user, role="faculty", items=["dashboard"]
        )

        request = self._get_request(user)
        request.session["role"] = "faculty"
        result = sidebar_permissions(request)

        self.assertEqual(result["allowed_nav_items"], role_items)

    def test_user_specific_role_record_does_not_affect_others(self):
        """A user-specific record with a role should not override role defaults."""
        role_items = ["events"]
        SidebarPermission.objects.create(role="faculty", items=role_items)
        user_with_override = User.objects.create_user("carol", password="pass")
        SidebarPermission.objects.create(
            user=user_with_override, role="faculty", items=["dashboard"]
        )
        other_user = User.objects.create_user("dave", password="pass")

        request = self._get_request(other_user)
        request.session["role"] = "faculty"
        result = sidebar_permissions(request)

        self.assertEqual(result["allowed_nav_items"], role_items)


class SidebarPermissionsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser("admin", "admin@example.com", "pass")
        self.client.login(username="admin", password="pass")

    def test_assign_permission_to_user(self):
        target = User.objects.create_user("dave", password="pass")
        url = reverse("admin_sidebar_permissions")
        response = self.client.post(
            url,
            {
                "user": str(target.id),
                "assigned_order": json.dumps(["dashboard", "events"]),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(f"?user={target.id}", response["Location"])
        perm = SidebarPermission.objects.get(user=target)
        self.assertEqual(perm.items, ["dashboard", "events"])


class SidebarPermissionsAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser("apiadmin", "api@example.com", "pass")
        self.client.login(username="apiadmin", password="pass")

    def test_api_save_user_success(self):
        url = reverse("api_save_sidebar_permissions")
        payload = {
            "assignments": [next(iter(SIDEBAR_ITEM_IDS))],
            "user": self.admin.id,
        }
        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["success"])

    def test_api_save_exclusive_validation(self):
        url = reverse("api_save_sidebar_permissions")
        payload = {"assignments": [], "user": self.admin.id, "role": "faculty"}
        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertFalse(resp.json()["success"])

    def test_api_save_unknown_id(self):
        url = reverse("api_save_sidebar_permissions")
        payload = {"assignments": ["unknown"], "user": self.admin.id}
        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertFalse(resp.json()["success"])

    def test_api_get_user_success(self):
        u = User.objects.create_user("bobapi", password="pass")
        SidebarPermission.objects.create(user=u, items=["dashboard"])
        url = reverse("api_get_sidebar_permissions") + f"?user={u.id}"
        resp = self.client.get(url)
        self.assertEqual(resp.json()["assignments"], ["dashboard"])

    def test_api_get_role_trimmed(self):
        SidebarPermission.objects.create(role="faculty", items=["events"])
        url = reverse("api_get_sidebar_permissions") + "?role=%20faculty%20"
        resp = self.client.get(url)
        self.assertEqual(resp.json()["assignments"], ["events"])
