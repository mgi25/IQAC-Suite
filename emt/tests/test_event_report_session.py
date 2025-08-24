from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in

from core.signals import create_or_update_user_profile, assign_role_on_login
from emt.models import EventProposal


class EventReportSessionTests(TestCase):
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
        self.proposal = EventProposal.objects.create(submitted_by=self.user, event_title="Session Test")

    def _management_data(self):
        return {
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }

    def test_session_persists_and_prefills(self):
        url = reverse("emt:submit_event_report", args=[self.proposal.id])
        post_data = {"location": "Hall"}
        post_data.update(self._management_data())
        self.client.post(url, post_data)

        session = self.client.session.get("event_report_draft", {})
        self.assertIn(str(self.proposal.id), session)
        self.assertEqual(session[str(self.proposal.id)]["location"], "Hall")

        resp = self.client.get(url)
        self.assertContains(resp, 'name="location" value="Hall"', html=False)

    def test_session_cleared_after_submission(self):
        url = reverse("emt:submit_event_report", args=[self.proposal.id])
        post_data = {"location": "Hall"}
        post_data.update(self._management_data())
        self.client.post(url, post_data)

        resp = self.client.post(url, post_data)
        self.assertEqual(resp.status_code, 302)
        session = self.client.session.get("event_report_draft", {})
        self.assertNotIn(str(self.proposal.id), session)
