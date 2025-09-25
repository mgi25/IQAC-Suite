from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from core.models import Organization, OrganizationRole, RoleAssignment, OrganizationType
from emt.models import EventProposal, EventReport


class ReviewCenterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        # Create required OrganizationType and Organization
        self.org_type = OrganizationType.objects.create(name="Department")
        self.org = Organization.objects.create(name="Dept A", org_type=self.org_type)
        self.proposer = self.user
        self.proposal = EventProposal.objects.create(
            submitted_by=self.proposer,
            organization=self.org,
            event_title="Sample Event",
        )
        self.report = EventReport.objects.create(proposal=self.proposal)
        self.client = Client()
        self.client.login(username="u", password="p")

    def test_page_renders(self):
        url = reverse("emt:review_center")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Review Center")

    def test_feedback_required(self):
        url = reverse("emt:review_action")
        resp = self.client.post(url, {"report_id": self.report.id, "action": "approve"})
        self.assertEqual(resp.status_code, 400)

    def test_feedback_required(self):
        # Already checks feedback is required for actions
        url = reverse("emt:review_action")
        resp = self.client.post(url, {"report_id": self.report.id, "action": "approve"})
        self.assertEqual(resp.status_code, 400)
