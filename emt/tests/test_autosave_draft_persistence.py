from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
import json

from emt.models import EventProposal
from core.models import OrganizationType, Organization, OrganizationRole, RoleAssignment


class AutosaveDraftPersistenceTests(TestCase):
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

    def test_draft_persists_with_missing_required_fields(self):
        resp = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["success"])
        self.assertIn("event_title", data["errors"])
        pid = data["proposal_id"]
        proposal = EventProposal.objects.get(id=pid)
        self.assertEqual(proposal.event_title, "")

        payload = self._payload()
        payload.update({"proposal_id": pid, "event_title": "My Event"})
        resp2 = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertTrue(data2["success"])
        self.assertNotIn("event_title", data2.get("errors", {}))
        proposal.refresh_from_db()
        self.assertEqual(proposal.event_title, "My Event")

    def test_organization_fields_persist_after_autosave(self):
        ot2 = OrganizationType.objects.create(name="Club")
        org2 = Organization.objects.create(name="Robotics", org_type=ot2)
        payload = {
            "organization_type": str(ot2.id),
            "organization": str(org2.id),
            "academic_year": "2024-2025",
        }
        resp = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        pid = resp.json()["proposal_id"]

        resp2 = self.client.get(reverse("emt:submit_proposal_with_pk", args=[pid]))
        self.assertEqual(resp2.status_code, 200)
        html = resp2.content.decode()
        self.assertIn(f'<option value="{ot2.id}" selected', html)
        self.assertIn(f'<option value="{org2.id}" selected', html)

    def test_organization_fields_update_on_subsequent_autosave(self):
        # initial save uses default organization values
        resp1 = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        self.assertEqual(resp1.status_code, 200)
        pid = resp1.json()["proposal_id"]

        # change to a different organization type and organization
        ot2 = OrganizationType.objects.create(name="Club")
        org2 = Organization.objects.create(name="Robotics", org_type=ot2)
        payload = {
            "proposal_id": pid,
            "organization_type": str(ot2.id),
            "organization": str(org2.id),
            "academic_year": "2024-2025",
        }
        resp2 = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp2.status_code, 200)

        resp3 = self.client.get(reverse("emt:submit_proposal_with_pk", args=[pid]))
        self.assertEqual(resp3.status_code, 200)
        html = resp3.content.decode()
        self.assertIn(f'<option value="{ot2.id}" selected', html)
        self.assertIn(f'<option value="{org2.id}" selected', html)
