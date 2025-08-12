from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from core.models import OrganizationType, Organization, OrganizationRole


class AdminUserManagementRoleFilterTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.client.force_login(self.admin)

        org_type = OrganizationType.objects.create(name='Department')
        self.org1 = Organization.objects.create(name='Org One', org_type=org_type)
        self.org2 = Organization.objects.create(name='Org Two', org_type=org_type)
        OrganizationRole.objects.create(organization=self.org1, name='Role A')
        OrganizationRole.objects.create(organization=self.org2, name='Role B')

    def test_roles_filtered_by_selected_organization(self):
        url = reverse('admin_user_management')
        resp = self.client.get(url, {'organization[]': str(self.org1.id)})
        self.assertContains(resp, 'Role A')
        self.assertNotContains(resp, 'Role B')
