import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import (Organization, OrganizationRole, OrganizationType,
                         RoleAssignment)
from emt.models import EventProposal


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

    def test_autosave_updates_existing_draft_in_place(self):
        first = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 200)
        initial_id = first.json()["proposal_id"]

        payload = self._payload()
        payload.update(
            {
                "proposal_id": initial_id,
                "event_title": "Seminar",
                "committees_collaborations": "Committee A",
            }
        )
        second = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(second.status_code, 200)
        body = second.json()
        self.assertEqual(body["proposal_id"], initial_id)
        self.assertEqual(
            EventProposal.objects.filter(
                submitted_by=self.user,
                status=EventProposal.Status.DRAFT,
                is_user_deleted=False,
            ).count(),
            1,
        )

        proposal = EventProposal.objects.get(id=initial_id)
        self.assertEqual(proposal.event_title, "Seminar")
        self.assertEqual(proposal.committees_collaborations, "Committee A")

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

    def test_autosave_saves_complete_activities_ignoring_incomplete(self):
        payload = self._payload()
        payload.update(
            {
                "num_activities": "2",
                "activity_name_1": "Orientation",
                "activity_date_1": "2024-01-01",
                "activity_name_2": "Workshop",
            }
        )
        resp = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        pid = resp.json()["proposal_id"]
        proposal = EventProposal.objects.get(id=pid)
        activities = list(proposal.activities.all())
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0].name, "Orientation")

    def test_save_continue_speakers_ignores_future_section_errors(self):
        # Initial autosave to obtain proposal ID
        base = self._payload()
        base["event_title"] = "My Event"
        resp1 = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(base),
            content_type="application/json",
        )
        self.assertEqual(resp1.status_code, 200)
        pid = resp1.json()["proposal_id"]

        payload = {
            "proposal_id": pid,
            "speaker_full_name_0": "Dr. Jane",
            "speaker_designation_0": "Prof",
            "speaker_affiliation_0": "Uni",
            "speaker_contact_email_0": "a@b.com",
            "speaker_detailed_profile_0": "Profile",
            "speaker_linkedin_url_0": "https://linkedin.com/in/jane",
            # Incomplete expense to trigger future-section error
            "expense_particulars_0": "Venue",
        }
        resp2 = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp2.status_code, 200)
        data = resp2.json()
        self.assertIn("errors", data)
        # Speakers saved without errors
        self.assertNotIn("speakers", data["errors"])
        self.assertIn("expenses", data["errors"])  # future section error

        future_error_keys_map = {"speakers": ["expenses", "income"]}
        ignore = future_error_keys_map["speakers"]
        relevant = {
            k: v
            for k, v in data["errors"].items()
            if not any(k == key or k.startswith(f"{key}.") for key in ignore)
        }
        self.assertEqual(relevant, {})

        proposal = EventProposal.objects.get(id=pid)
        sp = proposal.speakers.first()
        self.assertIsNotNone(sp)
        self.assertEqual(sp.full_name, "Dr. Jane")
        self.assertEqual(sp.linkedin_url, "https://linkedin.com/in/jane")
