from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from emt.models import EventProposal


class StartProposalViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="starter", password="pass")
        self.client.force_login(self.user)

    def test_reuses_pristine_draft(self):
        first_response = self.client.get(reverse("emt:start_proposal"))
        self.assertEqual(first_response.status_code, 302)

        first_proposal = EventProposal.objects.get()
        expected_location = reverse(
            "emt:submit_proposal_with_pk", args=[first_proposal.pk]
        )
        self.assertEqual(first_response["Location"], expected_location)

        second_response = self.client.get(reverse("emt:start_proposal"))
        self.assertEqual(second_response.status_code, 302)

        self.assertEqual(EventProposal.objects.count(), 1)
        self.assertEqual(second_response["Location"], expected_location)

    def test_creates_new_draft_after_modification(self):
        first_response = self.client.get(reverse("emt:start_proposal"))
        self.assertEqual(first_response.status_code, 302)

        first_proposal = EventProposal.objects.get()
        first_proposal.event_title = "Edited title"
        first_proposal.save(update_fields=["event_title"])

        second_response = self.client.get(reverse("emt:start_proposal"))
        self.assertEqual(second_response.status_code, 302)

        self.assertEqual(EventProposal.objects.count(), 2)

        second_proposal = EventProposal.objects.exclude(pk=first_proposal.pk).get()
        expected_second_location = reverse(
            "emt:submit_proposal_with_pk", args=[second_proposal.pk]
        )
        self.assertEqual(second_response["Location"], expected_second_location)

    def test_reuses_blank_title_draft(self):
        first_response = self.client.get(reverse("emt:start_proposal"))
        self.assertEqual(first_response.status_code, 302)

        proposal = EventProposal.objects.get()
        proposal.event_title = ""
        proposal.save(update_fields=["event_title"])

        second_response = self.client.get(reverse("emt:start_proposal"))
        self.assertEqual(second_response.status_code, 302)

        self.assertEqual(EventProposal.objects.count(), 1)

        expected_location = reverse(
            "emt:submit_proposal_with_pk", args=[proposal.pk]
        )
        self.assertEqual(second_response["Location"], expected_location)
