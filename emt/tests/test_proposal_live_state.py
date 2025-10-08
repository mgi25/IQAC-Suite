from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Organization, OrganizationType, SDGGoal
from emt.models import (
    EventActivity,
    EventExpectedOutcomes,
    EventNeedAnalysis,
    EventObjectives,
    EventProposal,
    ExpenseDetail,
    IncomeDetail,
    SpeakerProfile,
    TentativeFlow,
)


class ProposalLiveStateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sync", password="pass1234")
        self.client.login(username="sync", password="pass1234")
        self.org_type = OrganizationType.objects.create(name="Department", is_active=True)
        self.organization = Organization.objects.create(
            name="Computer Science",
            org_type=self.org_type,
        )
        self.proposal = EventProposal.objects.create(
            submitted_by=self.user,
            organization=self.organization,
            event_title="Live Sync Showcase",
            event_start_date=timezone.now().date(),
            event_end_date=timezone.now().date(),
            venue="Innovation Hall",
            academic_year="2024-2025",
            target_audience="Students",
            event_focus_type="Seminar",
            num_activities=1,
            pos_pso="PO1",
            student_coordinators="Coordinator A",
            committees_collaborations="Robotics Club",
        )
        EventNeedAnalysis.objects.create(proposal=self.proposal, content="Need content")
        EventObjectives.objects.create(proposal=self.proposal, content="Objectives content")
        EventExpectedOutcomes.objects.create(
            proposal=self.proposal,
            content="Outcomes content",
        )
        TentativeFlow.objects.create(proposal=self.proposal, content="2024-05-01T10:00:00||Kickoff")
        EventActivity.objects.create(
            proposal=self.proposal,
            name="Introduction",
            date=timezone.now().date(),
        )
        SpeakerProfile.objects.create(
            proposal=self.proposal,
            full_name="Dr. Jane Speaker",
            designation="Professor",
            affiliation="Computer Science",
            contact_email="speaker@example.com",
            contact_number="1234567890",
            detailed_profile="Keynote speaker",
        )
        ExpenseDetail.objects.create(
            proposal=self.proposal,
            sl_no=1,
            particulars="Logistics",
            amount=2500,
        )
        IncomeDetail.objects.create(
            proposal=self.proposal,
            sl_no=1,
            particulars="Registration",
            participants=50,
            rate=100,
            amount=5000,
        )
        sdg = SDGGoal.objects.create(name="Quality Education")
        self.proposal.sdg_goals.add(sdg)

        self.url = reverse("emt:proposal_live_state", args=[self.proposal.id])

    def test_live_state_returns_serialized_payload(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("changed"))
        self.assertIsNotNone(data.get("updated_at"))

        payload = data.get("payload", {})
        self.assertEqual(payload.get("fields", {}).get("event_title"), "Live Sync Showcase")
        self.assertEqual(payload.get("fields", {}).get("organization"), str(self.organization.id))
        self.assertEqual(payload.get("text_sections", {}).get("need_analysis"), "Need content")

        activities = payload.get("activities", [])
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0].get("name"), "Introduction")
        self.assertTrue(activities[0].get("date"))

        speakers = payload.get("speakers", [])
        self.assertEqual(len(speakers), 1)
        self.assertEqual(speakers[0].get("full_name"), "Dr. Jane Speaker")

        expenses = payload.get("expenses", [])
        self.assertEqual(len(expenses), 1)
        self.assertEqual(expenses[0].get("amount"), 2500.0)

        income = payload.get("income", [])
        self.assertEqual(len(income), 1)
        self.assertEqual(income[0].get("amount"), 5000.0)

    def test_since_parameter_avoids_duplicate_payload(self):
        future = (timezone.now() + timedelta(minutes=5)).isoformat()
        response = self.client.get(self.url, {"since": future})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data.get("changed"))

    def test_live_state_enforces_owner(self):
        other = User.objects.create_user(username="other", password="pass1234")
        self.client.logout()
        self.client.login(username="other", password="pass1234")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)
