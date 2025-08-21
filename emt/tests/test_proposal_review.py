from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
import json

from emt.models import EventProposal
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
        self.user = User.objects.create(username="u1", first_name="Test", email="u1@example.com")
        RoleAssignment.objects.create(user=self.user, role=self.faculty_role, organization=self.org)
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
        resp2 = self.client.post(reverse("emt:submit_proposal_with_pk", args=[pid]), post_data)
        self.assertEqual(resp2.status_code, 302)
        self.assertIn(reverse("emt:review_proposal", args=[pid]), resp2.headers["Location"])

        resp3 = self.client.post(reverse("emt:review_proposal", args=[pid]), {"final_submit": "1"})
        self.assertEqual(resp3.status_code, 302)
        proposal = EventProposal.objects.get(id=pid)
        self.assertEqual(proposal.status, EventProposal.Status.SUBMITTED)
