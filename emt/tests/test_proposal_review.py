from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
import json

from emt.models import (
    EventProposal,
    CDLSupport,
    EventNeedAnalysis,
    EventObjectives,
    EventExpectedOutcomes,
    TentativeFlow,
    SpeakerProfile,
    ExpenseDetail,
    IncomeDetail,
)
from core.models import (
    OrganizationType,
    Organization,
    OrganizationRole,
    RoleAssignment,
)


class ProposalReviewFlowTests(TestCase):
    def setUp(self):
        self.ot = OrganizationType.objects.create(name="Dept")
        self.org = Organization.objects.create(name="Science", org_type=self.ot)
        self.faculty_role = OrganizationRole.objects.create(
            organization=self.org, name="Faculty"
        )
        self.user = User.objects.create(
            username="u1", first_name="Test", email="u1@example.com"
        )
        RoleAssignment.objects.create(
            user=self.user, role=self.faculty_role, organization=self.org
        )
        self.client.force_login(self.user)

    def _payload(self):
        return {
            "organization_type": str(self.ot.id),
            "organization": str(self.org.id),
            "academic_year": "2024-2025",
        }

    def test_review_and_final_submit_flow(self):
        resp = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        pid = resp.json()["proposal_id"]

        post_data = self._payload()
        post_data["review_submit"] = "1"
        resp2 = self.client.post(
            reverse("emt:submit_proposal_with_pk", args=[pid]), post_data
        )
        self.assertEqual(resp2.status_code, 302)
        self.assertIn(
            reverse("emt:review_proposal", args=[pid]), resp2.headers["Location"]
        )

        resp3 = self.client.post(
            reverse("emt:review_proposal", args=[pid]), {"final_submit": "1"}
        )
        self.assertEqual(resp3.status_code, 302)
        proposal = EventProposal.objects.get(id=pid)
        self.assertEqual(proposal.status, EventProposal.Status.SUBMITTED)

    def test_review_displays_all_cdl_support(self):
        resp = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        pid = resp.json()["proposal_id"]
        proposal = EventProposal.objects.get(id=pid)

        CDLSupport.objects.create(
            proposal=proposal,
            needs_support=True,
            poster_required=True,
            poster_choice=CDLSupport.PosterChoice.CDL_CREATE,
            organization_name="OrgX",
            poster_time="10am",
            poster_date="2024-06-01",
            poster_venue="Hall 1",
            resource_person_name="Dr. Smith",
            resource_person_designation="Professor",
            poster_event_title="PosterTitle",
            poster_summary="Summary text",
            poster_design_link="http://example.com/poster",
            certificates_required=True,
            certificate_help=True,
            certificate_choice=CDLSupport.CertificateChoice.CDL_CREATE,
            certificate_design_link="http://example.com/cert",
            other_services=["Photos"],
            blog_content="Blog text",
        )

        resp = self.client.get(reverse("emt:review_proposal", args=[pid]))
        self.assertContains(resp, "OrgX")
        self.assertContains(resp, "Hall 1")
        self.assertContains(resp, "Dr. Smith")
        self.assertContains(resp, "Blog text")
        self.assertContains(resp, "Photos")

    def test_cdl_support_review_flow(self):
        resp = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        pid = resp.json()["proposal_id"]

        post_data = {"needs_support": "on", "review_submit": "1"}
        resp2 = self.client.post(
            reverse("emt:submit_cdl_support", args=[pid]), post_data
        )
        self.assertEqual(resp2.status_code, 302)
        self.assertIn(
            reverse("emt:review_proposal", args=[pid]), resp2.headers["Location"]
        )

        proposal = EventProposal.objects.get(id=pid)
        self.assertEqual(proposal.status, EventProposal.Status.DRAFT)

    def test_ai_generated_text_persists(self):
        resp = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        pid = resp.json()["proposal_id"]

        ai_data = {
            **self._payload(),
            "proposal_id": pid,
            "need_analysis": "AI need",
            "objectives": "AI objectives",
            "outcomes": "AI outcomes",
        }
        self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(ai_data),
            content_type="application/json",
        )

        resp2 = self.client.get(reverse("emt:review_proposal", args=[pid]))
        self.assertContains(resp2, "AI need")
        self.assertContains(resp2, "AI objectives")
        self.assertContains(resp2, "AI outcomes")

    def test_review_lists_speakers_and_expenses(self):
        resp = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        pid = resp.json()["proposal_id"]
        proposal = EventProposal.objects.get(id=pid)

        SpeakerProfile.objects.create(
            proposal=proposal,
            full_name="Alice",
            designation="Prof",
            affiliation="Uni",
            contact_email="a@example.com",
            contact_number="123",
            detailed_profile="Bio",
        )
        SpeakerProfile.objects.create(
            proposal=proposal,
            full_name="Bob",
            designation="Dr",
            affiliation="Institute",
            contact_email="b@example.com",
            contact_number="321",
            detailed_profile="Bio2",
        )
        ExpenseDetail.objects.create(
            proposal=proposal, sl_no=1, particulars="Venue", amount=100
        )
        ExpenseDetail.objects.create(
            proposal=proposal, sl_no=2, particulars="Refreshments", amount=200
        )

        resp2 = self.client.get(reverse("emt:review_proposal", args=[pid]))
        # Speakers appear
        self.assertContains(resp2, "Alice")
        self.assertContains(resp2, "Prof")
        self.assertContains(resp2, "Bob")
        self.assertContains(resp2, "Dr")
        # Expenses appear
        self.assertContains(resp2, "Venue")
        self.assertContains(resp2, "100")
        self.assertContains(resp2, "Refreshments")
        self.assertContains(resp2, "200")

    def test_review_displays_all_sections(self):
        resp = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        pid = resp.json()["proposal_id"]
        proposal = EventProposal.objects.get(id=pid)

        EventNeedAnalysis.objects.create(proposal=proposal, content="Need content")
        EventObjectives.objects.create(proposal=proposal, content="Objective content")
        EventExpectedOutcomes.objects.create(
            proposal=proposal, content="Outcome content"
        )
        TentativeFlow.objects.create(proposal=proposal, content="Flow content")
        SpeakerProfile.objects.create(
            proposal=proposal,
            full_name="Alice",
            designation="Prof",
            affiliation="Uni",
            contact_email="a@example.com",
            contact_number="123",
            detailed_profile="Bio",
        )
        ExpenseDetail.objects.create(
            proposal=proposal, sl_no=1, particulars="Venue", amount=100
        )
        IncomeDetail.objects.create(
            proposal=proposal,
            sl_no=1,
            particulars="Ticket",
            participants=10,
            rate=100,
            amount=1000,
        )

        resp2 = self.client.get(reverse("emt:review_proposal", args=[pid]))
        self.assertContains(resp2, "Need content")
        self.assertContains(resp2, "Objective content")
        self.assertContains(resp2, "Outcome content")
        self.assertContains(resp2, "Flow content")
        self.assertContains(resp2, "Alice")
        self.assertContains(resp2, "Venue")
        self.assertContains(resp2, "Ticket")
