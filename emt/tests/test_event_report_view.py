from datetime import date
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in

from core.signals import create_or_update_user_profile, assign_role_on_login

from emt.models import EventProposal, EventActivity


class SubmitEventReportViewTests(TestCase):
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
        self.proposal = EventProposal.objects.create(
            submitted_by=self.user,
            event_title="Sample Event",
        )
        EventActivity.objects.create(
            proposal=self.proposal,
            name="Orientation",
            date=date(2024, 1, 1),
        )

    def test_activity_name_rendered_in_report_form(self):
        response = self.client.get(
            reverse("emt:submit_event_report", args=[self.proposal.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Orientation")

