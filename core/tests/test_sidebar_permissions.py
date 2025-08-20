from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware

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
