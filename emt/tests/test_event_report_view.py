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

    def test_activities_prefilled_in_report_form(self):
        response = self.client.get(
            reverse("emt:submit_event_report", args=[self.proposal.id])
        )
        self.assertEqual(response.status_code, 200)
        # Activity data should be exposed for client-side rendering
        self.assertContains(response, 'Orientation')
        self.assertContains(response, '2024-01-01')
        # Number of activities should be pre-filled
        self.assertContains(
            response,
            'id="num-activities-modern" name="num_activities" value="1"',
            html=False,
        )
        # Add activity button for dynamic editing
        self.assertContains(response, 'id="add-activity-btn"')

    def test_can_update_activities_via_report_submission(self):
        url = reverse("emt:submit_event_report", args=[self.proposal.id])
        data = {
            "actual_event_type": "Seminar",
            "report_signed_date": "2024-01-10",
            "num_activities": "2",
            "activity_name_1": "Session 1",
            "activity_date_1": "2024-01-02",
            "activity_name_2": "Session 2",
            "activity_date_2": "2024-01-03",
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        activities = list(EventActivity.objects.filter(proposal=self.proposal).order_by("date"))
        self.assertEqual(len(activities), 2)
        self.assertEqual(activities[0].name, "Session 1")
        self.assertEqual(activities[1].name, "Session 2")

