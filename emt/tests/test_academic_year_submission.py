from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.test import TestCase
from django.urls import reverse

from core.models import Organization, OrganizationType
from core.signals import assign_role_on_login, create_or_update_user_profile
from emt.models import EventProposal
from transcript.models import get_active_academic_year


class AcademicYearSubmissionTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        post_save.disconnect(create_or_update_user_profile, sender=User)
        user_logged_in.disconnect(assign_role_on_login)

    @classmethod
    def tearDownClass(cls):
        user_logged_in.connect(assign_role_on_login)
        post_save.connect(create_or_update_user_profile, sender=User)
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="pass")
        self.client.force_login(self.user)
        self.ot = OrganizationType.objects.create(name="Dept")
        self.org = Organization.objects.create(name="Science", org_type=self.ot)
        self.active_year = get_active_academic_year()

    def test_hidden_field_cannot_override_academic_year(self):
        url = reverse("emt:submit_proposal")
        data = {
            "organization_type": str(self.ot.id),
            "organization": str(self.org.id),
            "academic_year": "1999-2000",
            "num_activities": "0",
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        proposal = EventProposal.objects.get(submitted_by=self.user)
        self.assertEqual(proposal.academic_year, self.active_year.year)
