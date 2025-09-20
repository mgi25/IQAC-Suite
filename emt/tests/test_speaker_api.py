import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import Organization, OrganizationType
from emt.models import EventProposal, SpeakerProfile


class SpeakerApiTests(TestCase):
    def setUp(self):
        super().setUp()
        self._media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self._media_root)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(lambda: shutil.rmtree(self._media_root, ignore_errors=True))

        self.submitter = User.objects.create_user(username="submitter", password="pass")
        self.other_user = User.objects.create_user(username="other", password="pass")

        org_type = OrganizationType.objects.create(name="Department")
        organization = Organization.objects.create(name="IQAC", org_type=org_type)

        self.proposal = EventProposal.objects.create(
            event_title="Test Event",
            organization=organization,
            submitted_by=self.submitter,
            academic_year="2024-2025",
        )

        self.speaker = SpeakerProfile.objects.create(
            proposal=self.proposal,
            full_name="John Doe",
            designation="Analyst",
            affiliation="Research Lab",
            contact_email="john@example.com",
            contact_number="1234567890",
            linkedin_url="https://linkedin.com/in/johndoe",
            detailed_profile="Bio information",
        )

        self.url = reverse(
            "emt:api_update_speaker", args=[self.proposal.id, self.speaker.id]
        )

    def _payload(self, **overrides):
        data = {
            "full_name": "Dr. Jane Doe",
            "designation": "Senior Analyst",
            "affiliation": "Innovation Hub",
            "contact_email": "jane@example.com",
            "contact_number": "5551234567",
            "linkedin_url": "https://linkedin.com/in/janedoe",
            "detailed_profile": "Updated biography",
        }
        data.update(overrides)
        return data

    def test_requires_permission(self):
        self.client.force_login(self.other_user)
        response = self.client.post(self.url, self._payload())
        self.assertEqual(response.status_code, 403)

    def test_updates_speaker_fields(self):
        self.client.force_login(self.submitter)
        payload = self._payload()
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["speaker"]["full_name"], payload["full_name"])
        self.speaker.refresh_from_db()
        self.assertEqual(self.speaker.full_name, payload["full_name"])
        self.assertEqual(self.speaker.designation, payload["designation"])
        self.assertEqual(self.speaker.affiliation, payload["affiliation"])
        self.assertEqual(self.speaker.contact_email, payload["contact_email"])
        self.assertEqual(self.speaker.contact_number, payload["contact_number"])
        self.assertEqual(self.speaker.linkedin_url, payload["linkedin_url"])
        self.assertEqual(self.speaker.detailed_profile, payload["detailed_profile"])

    def test_remove_photo(self):
        photo = SimpleUploadedFile("photo.jpg", b"file", content_type="image/jpeg")
        self.speaker.photo.save("photo.jpg", photo, save=True)
        self.client.force_login(self.submitter)
        payload = self._payload(remove_photo="1")
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["speaker"].get("photo"), "")
        self.speaker.refresh_from_db()
        self.assertFalse(bool(self.speaker.photo))

    def test_upload_new_photo(self):
        self.client.force_login(self.submitter)
        payload = self._payload()
        new_photo = SimpleUploadedFile("new.jpg", b"newfile", content_type="image/jpeg")
        payload["photo"] = new_photo
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertNotEqual(data["speaker"].get("photo"), "")
        self.speaker.refresh_from_db()
        self.assertTrue(bool(self.speaker.photo))
