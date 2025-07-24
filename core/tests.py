from django.test import TestCase

from .models import OrganizationType, Organization


class OrganizationModelTests(TestCase):
    def test_create_organization(self):
        org_type = OrganizationType.objects.create(name="Department")
        org = Organization.objects.create(name="Math", org_type=org_type)

        self.assertEqual(Organization.objects.count(), 1)
        self.assertEqual(org.org_type.name, "Department")
