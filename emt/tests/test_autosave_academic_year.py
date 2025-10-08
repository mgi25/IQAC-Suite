import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Organization, OrganizationType
from emt.models import EventProposal
from transcript.models import get_active_academic_year


class AutosaveAcademicYearTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="autosave", password="pass")
        self.client.force_login(self.user)
        self.org_type = OrganizationType.objects.create(name="Dept")
        self.organization = Organization.objects.create(
            name="Science", org_type=self.org_type
        )

    def test_autosave_uses_active_academic_year_for_new_draft(self):
        active_year = get_active_academic_year()
        payload = {
            "organization_type": str(self.org_type.id),
            "organization": str(self.organization.id),
            "event_title": "Orientation Workshop",
        }

        resp = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertNotIn("academic_year", data.get("errors", {}))

        proposal = EventProposal.objects.get(id=data["proposal_id"])
        self.assertEqual(proposal.academic_year, active_year.year)

    def test_existing_draft_retains_stored_academic_year(self):
        proposal = EventProposal.objects.create(
            submitted_by=self.user,
            organization=self.organization,
            event_title="Existing Draft",
            academic_year="2020-2021",
            status=EventProposal.Status.DRAFT,
        )

        payload = {
            "proposal_id": str(proposal.id),
            "organization_type": str(self.org_type.id),
            "organization": str(self.organization.id),
            "event_title": "Updated Title",
        }

        resp = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertNotIn("academic_year", data.get("errors", {}))

        proposal.refresh_from_db()
        self.assertEqual(proposal.academic_year, "2020-2021")
