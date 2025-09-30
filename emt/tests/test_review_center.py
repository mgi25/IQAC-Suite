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
        url = reverse("emt:review_action")
        resp = self.client.post(url, {"report_id": self.report.id, "action": "approve"})
        self.assertEqual(resp.status_code, 400)

    def test_approve_reject_flow_denied_for_submitter(self):
        # Submitter (user stage) cannot approve/reject; expect 403 when valid payload but unauthorized stage
        url = reverse("emt:review_action")
        resp = self.client.post(
            url,
            {
                "report_id": self.report.id,
                "action": "approve",
                "feedback": "Looks good",
            },
        )
        self.assertEqual(resp.status_code, 403)

    def test_superuser_can_approve(self):
        # Promote existing user to superuser and attempt approval at USER stage
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save(update_fields=["is_superuser", "is_staff"])
        url = reverse("emt:review_action")
        resp = self.client.post(
            url,
            {
                "report_id": self.report.id,
                "action": "approve",
                "feedback": "Advancing as superuser",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.report.refresh_from_db()
        # After superuser approval from USER stage we jump to HOD
        self.assertEqual(self.report.review_stage, EventReport.ReviewStage.HOD)

    def test_staff_can_approve(self):
        # Staff (admin) but not superuser can also approve at any stage except finalized
        self.user.is_staff = True
        self.user.is_superuser = False
        self.user.save(update_fields=["is_staff", "is_superuser"])
        url = reverse("emt:review_action")
        resp = self.client.post(
            url,
            {
                "report_id": self.report.id,
                "action": "approve",
                "feedback": "Advancing as staff",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.report.refresh_from_db()
        self.assertEqual(self.report.review_stage, EventReport.ReviewStage.HOD)

    # NOTE: Role-based positive path (e.g., DIQAC/HOD/UIQAC) would require constructing role assignments.
    # This can be added when role factories/utilities exist in tests.
