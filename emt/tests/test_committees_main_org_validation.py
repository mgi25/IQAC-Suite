from django.test import TestCase
from emt.forms import EventProposalForm
from core.models import OrganizationType, Organization

class CommitteesMainOrgValidationTests(TestCase):
    def setUp(self):
        self.org_type = OrganizationType.objects.create(name="Department")
        self.org = Organization.objects.create(name="Data Science", org_type=self.org_type, is_active=True)

    def get_base_data(self):
        return {
            'organization_type': self.org_type.id,
            'organization': self.org.id,
            'event_title': 'Test Event',
            'event_start_date': '2025-01-01',
            'event_end_date': '2025-01-02',
            'venue': 'Hall',
            'academic_year': '2024-2025',
        }

    def test_same_org_not_allowed(self):
        data = self.get_base_data()
        data['committees_collaborations'] = 'Data Science, Other Org'
        form = EventProposalForm(data=data, selected_academic_year='2024-2025')
        self.assertFalse(form.is_valid())
        self.assertIn('committees_collaborations', form.errors)

    def test_different_org_allowed(self):
        data = self.get_base_data()
        data['committees_collaborations'] = 'Other Org'
        form = EventProposalForm(data=data, selected_academic_year='2024-2025')
        self.assertTrue(form.is_valid())
