from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from core.models import OrganizationType, Organization, OrganizationRole, RoleAssignment


class RegistrationMiddlewareTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="u1", email="u1@example.com", password="pass"
        )
        self.client.login(username="u1", password="pass")

    def test_redirects_unregistered_user(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, reverse("registration_form"))

    def test_allows_access_after_role_assignment(self):
        ot = OrganizationType.objects.create(name="Dept")
        org = Organization.objects.create(name="Math", org_type=ot)
        role = OrganizationRole.objects.create(name="Member", organization=org)
        RoleAssignment.objects.create(user=self.user, role=role, organization=org)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)


class RegistrationAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="u2", email="u2@example.com", password="pass"
        )
        self.client.login(username="u2", password="pass")
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
