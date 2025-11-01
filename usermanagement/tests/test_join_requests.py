from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import SidebarPermission


User = get_user_model()


class JoinRequestsViewTests(TestCase):
    def setUp(self):
        self.url = reverse("usermanagement:join_requests")

    def test_user_without_permission_gets_403(self):
        user = User.objects.create_user("regular", password="pass")
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_staff_user_can_access(self):
        staff = User.objects.create_user("staff", password="pass", is_staff=True)
        self.client.force_login(staff)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_user_with_sidebar_permission_can_access(self):
        user = User.objects.create_user("permitted", password="pass")
        SidebarPermission.objects.create(user=user, items=["user_management"])
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
