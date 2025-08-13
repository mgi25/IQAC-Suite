from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from core.models import OrganizationType, Organization, OrganizationRole


class RegistrationAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="u1", email="u1@example.com", password="pass"
        )
        self.client.force_login(self.user)

    def test_dashboard_access_without_registration(self):
        # Simulate an unregistered user by clearing their profile role
        profile = self.user.profile
        profile.role = ""
        profile.save(update_fields=["role"])
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)


class RegistrationAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="u2", email="u2@example.com", password="pass"
        )
        self.client.force_login(self.user)
        self.ot = OrganizationType.objects.create(name="Dept")
        self.org = Organization.objects.create(name="Science", org_type=self.ot)
        self.role = OrganizationRole.objects.create(
            name="Member", organization=self.org
        )

    def test_api_organizations_accessible(self):
        response = self.client.get(reverse("api_organizations"))
        self.assertEqual(response.status_code, 200)
        data = response.json()["organizations"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["text"], self.org.name)

    def test_api_roles_accessible(self):
        response = self.client.get(
            reverse("api_roles"), {"organization": self.org.id}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["roles"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["text"], self.role.name)
