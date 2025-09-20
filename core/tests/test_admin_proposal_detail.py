from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from emt.models import (EventNeedAnalysis, EventObjectives, EventProposal,
                        ExpenseDetail, SpeakerProfile, TentativeFlow)


class AdminProposalDetailViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="pass"
        )
        faculty = User.objects.create_user(
            username="fac", password="pass", first_name="Fac", last_name="User"
        )
        self.proposal = EventProposal.objects.create(
            submitted_by=self.admin,
            committees="Organizing",
            event_title="Sample Event",
            fest_fee_participants=10,
            fest_fee_rate=Decimal("100.00"),
            fest_fee_amount=Decimal("1000.00"),
        )
        self.proposal.faculty_incharges.add(faculty)
        EventNeedAnalysis.objects.create(
            proposal=self.proposal, content="Need analysis content"
        )
        EventObjectives.objects.create(
            proposal=self.proposal, content="Objectives content"
        )
        TentativeFlow.objects.create(proposal=self.proposal, content="Flow content")
        SpeakerProfile.objects.create(
            proposal=self.proposal,
            full_name="John Speaker",
            designation="Professor",
            affiliation="Uni",
            contact_email="speaker@example.com",
            contact_number="1234567890",
        )
        ExpenseDetail.objects.create(
            proposal=self.proposal,
            sl_no=1,
            particulars="Item 1",
            amount=Decimal("500.00"),
        )
        self.client.force_login(self.admin)

    def test_admin_proposal_detail_renders_sections(self):
        url = reverse("admin_proposal_detail", args=[self.proposal.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Organizing")
        self.assertContains(response, "Fac User")
        self.assertContains(response, "Need analysis content")
        self.assertContains(response, "Objectives content")
        self.assertContains(response, "Flow content")
        self.assertContains(response, "John Speaker")
        self.assertContains(response, "1000")
        self.assertContains(response, "Item 1")
