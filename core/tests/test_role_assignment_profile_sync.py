from django.contrib.auth.models import User
from django.test import TestCase

from core.models import (Organization, OrganizationRole, OrganizationType,
                         RoleAssignment)


class RoleAssignmentProfileSyncTests(TestCase):
    def setUp(self):
        org_type = OrganizationType.objects.create(name="Dept")
        self.org = Organization.objects.create(name="Science", org_type=org_type)
        self.student_role = OrganizationRole.objects.create(
            organization=self.org, name="student"
        )
        self.faculty_role = OrganizationRole.objects.create(
            organization=self.org, name="faculty"
        )
        self.user = User.objects.create_user(
            "john", email="john@example.com", password="pass"
        )

    def test_profile_role_updates_on_assignment_save_and_delete(self):
        RoleAssignment.objects.create(
            user=self.user, organization=self.org, role=self.student_role
        )
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.role, "student")

        ra = RoleAssignment.objects.get(user=self.user, organization=self.org)
        ra.role = self.faculty_role
        ra.save()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.role, "faculty")

        ra.delete()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.role, "student")
