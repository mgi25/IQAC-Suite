import json

from django.contrib import messages
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Organization, OrganizationRole, OrganizationType, RoleAssignment
from emt.models import EventProposal


class ProposalDraftManagementTests(TestCase):
    def setUp(self):
        self.org_type = OrganizationType.objects.create(name="Department")
        self.organization = Organization.objects.create(
            name="Computer Science",
            org_type=self.org_type,
        )
        self.role = OrganizationRole.objects.create(
            organization=self.organization,
            name="Faculty",
        )
        self.user = User.objects.create_user("drafter", password="pass1234")
        RoleAssignment.objects.create(
            user=self.user,
            role=self.role,
            organization=self.organization,
        )
        self.client.force_login(self.user)

    def _make_draft(self, title="Untitled"):
        return EventProposal.objects.create(
            submitted_by=self.user,
            status=EventProposal.Status.DRAFT,
            event_title=title,
        )

    def _payload(self):
        return {
            "organization_type": str(self.org_type.id),
            "organization": str(self.organization.id),
            "academic_year": "2024-2025",
        }

    def test_reset_draft_marks_hidden_instead_of_deleting(self):
        draft = self._make_draft()
        response = self.client.post(
            reverse("emt:reset_proposal_draft"),
            data=json.dumps({"proposal_id": draft.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        draft.refresh_from_db()
        self.assertTrue(draft.is_user_deleted)
        self.assertTrue(
            EventProposal.objects.filter(id=draft.id, submitted_by=self.user).exists()
        )

    def test_start_proposal_respects_draft_limit(self):
        for idx in range(5):
            self._make_draft(title=f"Draft {idx}")

        response = self.client.get(reverse("emt:start_proposal"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("emt:proposal_drafts"))

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertTrue(messages_list)
        self.assertIn("Delete an older draft", messages_list[0].message)
        self.assertEqual(
            EventProposal.objects.filter(
                submitted_by=self.user,
                status=EventProposal.Status.DRAFT,
                is_user_deleted=False,
            ).count(),
            5,
        )

    def test_autosave_blocks_new_draft_when_limit_reached(self):
        for idx in range(5):
            self._make_draft(title=f"Draft {idx}")

        response = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload.get("success"))
        self.assertIn("draft_limit", payload.get("errors", {}))
        self.assertEqual(
            EventProposal.objects.filter(
                submitted_by=self.user,
                status=EventProposal.Status.DRAFT,
                is_user_deleted=False,
            ).count(),
            5,
        )

    def test_proposal_drafts_view_preserves_existing_drafts(self):
        for idx in range(3):
            self._make_draft(title=f"Draft {idx}")

        response = self.client.get(reverse("emt:proposal_drafts"))
        self.assertEqual(response.status_code, 200)

        active_titles = list(
            EventProposal.objects.filter(
                submitted_by=self.user,
                status=EventProposal.Status.DRAFT,
                is_user_deleted=False,
            )
            .order_by("-updated_at")
            .values_list("event_title", flat=True)
        )

        self.assertEqual(len(active_titles), 3)
        self.assertListEqual(active_titles, ["Draft 2", "Draft 1", "Draft 0"])

        archived_titles = set(
            EventProposal.objects.filter(
                submitted_by=self.user,
                status=EventProposal.Status.DRAFT,
                is_user_deleted=True,
            ).values_list("event_title", flat=True)
        )
        self.assertSetEqual(archived_titles, set())
