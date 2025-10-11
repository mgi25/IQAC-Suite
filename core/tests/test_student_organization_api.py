import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Organization, OrganizationMembership, OrganizationType
from usermanagement.models import JoinRequest
from emt.models import Student


class StudentOrganizationApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="student_org",
            email="student_org@example.com",
            password="testpass123",
        )
        self.student = Student.objects.create(user=self.user)
        self.client.defaults["REMOTE_ADDR"] = "127.0.0.1"

        self.org_type_a = OrganizationType.objects.create(name="Clubs", is_active=True)
        self.org_type_b = OrganizationType.objects.create(name="Committees", is_active=True)

        self.org_a = Organization.objects.create(
            name="Chess Club",
            org_type=self.org_type_a,
            is_active=True,
        )
        self.org_b = Organization.objects.create(
            name="Debate Committee",
            org_type=self.org_type_b,
            is_active=True,
        )

        self.client.login(username="student_org", password="testpass123")

    def test_get_organization_types_success(self):
        response = self.client.get(reverse("api_student_organization_types"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        returned_names = {item["name"] for item in payload["types"]}
        self.assertSetEqual(returned_names, {"Clubs", "Committees"})

    def test_get_organizations_excludes_already_joined(self):
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.org_a,
            academic_year="2025-2026",
            role="student",
            is_active=True,
        )

        response = self.client.get(
            reverse("api_student_organizations"),
            {"type_id": self.org_type_a.id},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        # The organization already joined should be excluded
        returned_ids = {int(item["id"]) for item in payload["organizations"]}
        self.assertNotIn(self.org_a.id, returned_ids)

    def test_join_organization_creates_pending_request(self):
        response = self.client.post(
            reverse("api_student_join_organization"),
            data=json.dumps({"organization_id": self.org_a.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["success"])
        join_request = JoinRequest.objects.get(user=self.user, organization=self.org_a)
        self.assertEqual(join_request.status, JoinRequest.STATUS_PENDING)
        self.assertIn("join_request", payload)
        self.assertEqual(payload["join_request"]["id"], join_request.id)
        self.assertFalse(
            OrganizationMembership.objects.filter(
                user=self.user, organization=self.org_a, is_active=True
            ).exists()
        )

    def test_join_organization_returns_existing_pending_request(self):
        JoinRequest.objects.create(
            user=self.user,
            organization=self.org_a,
            status=JoinRequest.STATUS_PENDING,
        )

        response = self.client.post(
            reverse("api_student_join_organization"),
            data=json.dumps({"organization_id": self.org_a.id}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertIn("join_request", payload)
        self.assertEqual(payload["join_request"]["status"], JoinRequest.STATUS_PENDING)

    def test_join_requires_student_profile(self):
        other_user = User.objects.create_user(
            username="not_student",
            email="not_student@example.com",
            password="testpass123",
        )
        self.client.logout()
        self.client.login(username="not_student", password="testpass123")

        response = self.client.get(reverse("api_student_organization_types"))
        self.assertEqual(response.status_code, 403)

    def test_get_organizations_excludes_pending_requests(self):
        JoinRequest.objects.create(
            user=self.user,
            organization=self.org_a,
            status=JoinRequest.STATUS_PENDING,
        )

        response = self.client.get(
            reverse("api_student_organizations"),
            {"type_id": self.org_type_a.id},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        returned_ids = {int(item["id"]) for item in payload["organizations"]}
        self.assertNotIn(self.org_a.id, returned_ids)

    def test_leave_organization_creates_pending_request(self):
        membership = OrganizationMembership.objects.create(
            user=self.user,
            organization=self.org_a,
            academic_year="2025-2026",
            role="student",
            is_active=True,
        )

        response = self.client.post(
            reverse("api_student_leave_organization", args=[self.org_a.id])
        )
        self.assertEqual(response.status_code, 201)

        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertIn("join_request", payload)
        self.assertEqual(payload["join_request"]["request_type"], JoinRequest.TYPE_LEAVE)
        self.assertEqual(payload["join_request"]["status"], JoinRequest.STATUS_PENDING)

        membership.refresh_from_db()
        self.assertTrue(membership.is_active)

        leave_request = JoinRequest.objects.get(user=self.user, organization=self.org_a)
        self.assertEqual(leave_request.request_type, JoinRequest.TYPE_LEAVE)
        self.assertEqual(leave_request.status, JoinRequest.STATUS_PENDING)

    def test_leave_organization_returns_existing_pending_request(self):
        membership = OrganizationMembership.objects.create(
            user=self.user,
            organization=self.org_a,
            academic_year="2025-2026",
            role="student",
            is_active=True,
        )

        JoinRequest.objects.create(
            user=self.user,
            organization=self.org_a,
            request_type=JoinRequest.TYPE_LEAVE,
            status=JoinRequest.STATUS_PENDING,
        )

        response = self.client.post(
            reverse("api_student_leave_organization", args=[self.org_a.id])
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["join_request"]["request_type"], JoinRequest.TYPE_LEAVE)
        membership.refresh_from_db()
        self.assertTrue(membership.is_active)
