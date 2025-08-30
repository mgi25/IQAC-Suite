from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in

from core.signals import create_or_update_user_profile, assign_role_on_login
from core.models import OrganizationType, Organization

from emt.models import EventProposal, EventActivity


class ProposalActivityPersistenceTests(TestCase):
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
        self.user = User.objects.create_user(username="bob", password="pass")
        self.client.force_login(self.user)
        self.ot = OrganizationType.objects.create(name="Dept")
        self.org = Organization.objects.create(name="Science", org_type=self.ot)

    def test_proposal_activities_show_on_event_report(self):
        url = reverse("emt:submit_proposal")
        data = {
            "organization_type": str(self.ot.id),
            "organization": str(self.org.id),
            "academic_year": "2024-2025",
            "event_title": "My Event",
            "num_activities": "2",
            "activity_name_1": "Orientation",
            "activity_date_1": "2024-01-01",
            "activity_name_2": "Workshop",
            "activity_date_2": "2024-01-02",
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        proposal = EventProposal.objects.get(submitted_by=self.user)
        activities = list(EventActivity.objects.filter(proposal=proposal).order_by("date"))
        self.assertEqual(len(activities), 2)
        self.assertEqual(activities[0].name, "Orientation")
        self.assertEqual(activities[1].name, "Workshop")
        resp2 = self.client.get(reverse("emt:submit_event_report", args=[proposal.id]))
        self.assertContains(resp2, 'name="activity_name_1" value="Orientation"', html=False)
        self.assertContains(resp2, 'name="activity_name_2" value="Workshop"', html=False)

    def test_invalid_activity_submission_preserves_existing(self):
        url = reverse("emt:submit_proposal")
        data = {
            "organization_type": str(self.ot.id),
            "organization": str(self.org.id),
            "academic_year": "2024-2025",
            "event_title": "My Event",
            "num_activities": "1",
            "activity_name_1": "Orientation",
            "activity_date_1": "2024-01-01",
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        proposal = EventProposal.objects.get(submitted_by=self.user)
        self.assertEqual(proposal.activities.count(), 1)

        update = {
            "organization_type": str(self.ot.id),
            "organization": str(self.org.id),
            "academic_year": "2024-2025",
            "event_title": "My Event",
            "num_activities": "1",
            "activity_name_1": "Updated",
            # missing date
        }
        resp2 = self.client.post(
            reverse("emt:submit_proposal_with_pk", args=[proposal.id]),
            update,
        )
        self.assertEqual(resp2.status_code, 200)
        proposal.refresh_from_db()
        activities = list(proposal.activities.all())
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0].name, "Orientation")
