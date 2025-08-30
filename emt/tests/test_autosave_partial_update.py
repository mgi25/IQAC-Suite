from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
import json

from core.models import OrganizationType, Organization, OrganizationRole, RoleAssignment
from emt.models import EventProposal, EventActivity, SpeakerProfile


class AutosavePartialUpdateTests(TestCase):
    def setUp(self):
        self.ot = OrganizationType.objects.create(name="Dept")
        self.org = Organization.objects.create(name="Science", org_type=self.ot)
        self.faculty_role = OrganizationRole.objects.create(
            organization=self.org, name="Faculty"
        )
        self.user = User.objects.create(username="u1", first_name="Test", email="u1@example.com")
        RoleAssignment.objects.create(user=self.user, role=self.faculty_role, organization=self.org)
        self.faculty = User.objects.create(username="fac1", first_name="Fac", email="fac@example.com")
        RoleAssignment.objects.create(user=self.faculty, role=self.faculty_role, organization=self.org)
        self.client.force_login(self.user)

    def _payload(self):
        return {
            "organization_type": str(self.ot.id),
            "organization": str(self.org.id),
            "academic_year": "2024-2025",
        }

    def test_autosave_single_activity_no_other_errors(self):
        resp = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        pid = resp.json()["proposal_id"]

        payload = {"proposal_id": pid, "activity_name_1": "Intro", "activity_date_1": "2024-01-01"}
        resp2 = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        data2 = resp2.json()
        self.assertTrue(data2["success"])
        self.assertNotIn("event_title", data2.get("errors", {}))
        self.assertNotIn("activities", data2.get("errors", {}))
        proposal = EventProposal.objects.get(id=pid)
        activities = list(EventActivity.objects.filter(proposal=proposal))
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0].name, "Intro")

    def test_autosave_faculty_incharge_persists(self):
        resp = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        pid = resp.json()["proposal_id"]

        payload = {"proposal_id": pid, "faculty_incharges": [str(self.faculty.id)]}
        resp2 = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        data2 = resp2.json()
        self.assertTrue(data2["success"])
        self.assertNotIn("event_title", data2.get("errors", {}))
        proposal = EventProposal.objects.get(id=pid)
        self.assertEqual(list(proposal.faculty_incharges.values_list("id", flat=True)), [self.faculty.id])

        get_resp = self.client.get(reverse("emt:submit_proposal_with_pk", args=[pid]))
        self.assertContains(get_resp, f'value="{self.faculty.id}" selected')

    def test_autosave_remove_all_speakers(self):
        resp = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        pid = resp.json()["proposal_id"]

        add_payload = {
            "proposal_id": pid,
            "speaker_full_name_0": "Dr. Jane",
            "speaker_designation_0": "Prof",
            "speaker_affiliation_0": "Uni",
            "speaker_contact_email_0": "jane@example.com",
            "speaker_detailed_profile_0": "Profile",
        }
        resp2 = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(add_payload),
            content_type="application/json",
        )
        self.assertTrue(resp2.json()["success"])
        self.assertEqual(SpeakerProfile.objects.filter(proposal_id=pid).count(), 1)

        remove_payload = {"proposal_id": pid, "speaker_full_name_0": ""}
        resp3 = self.client.post(
            reverse("emt:autosave_proposal"),
            data=json.dumps(remove_payload),
            content_type="application/json",
        )
        self.assertTrue(resp3.json()["success"])
        self.assertEqual(SpeakerProfile.objects.filter(proposal_id=pid).count(), 0)
