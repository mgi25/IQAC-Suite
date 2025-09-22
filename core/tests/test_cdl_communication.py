from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse


class CDLCommunicationTests(TestCase):
    def setUp(self):
        self.group, _ = Group.objects.get_or_create(name="CDL_MEMBER")

    def _login_member(self, username: str) -> None:
        user = User.objects.create_user(username=username, password="pass123")
        user.groups.add(self.group)
        logged_in = self.client.login(username=username, password="pass123")
        self.assertTrue(logged_in)

    def test_create_and_list_messages(self):
        self._login_member("alice")
        url = reverse("api_cdl_communication")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["messages"], [])

        response = self.client.post(url, {"comment": "Hello world"})
        self.assertEqual(response.status_code, 201)
        msg1 = response.json()
        self.assertEqual(msg1["comment"], "Hello world")

        uploaded = SimpleUploadedFile(
            "note.txt",
            b"Attachment content",
            content_type="text/plain",
        )
        response = self.client.post(
            url,
            {"comment": "With file", "attachment": uploaded},
        )
        self.assertEqual(response.status_code, 201)
        msg2 = response.json()
        self.assertIsNotNone(msg2["attachment_url"])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["messages"]), 2)
        comments = {m["comment"] for m in data["messages"]}
        self.assertSetEqual(comments, {"Hello world", "With file"})

    def test_page_sets_csrf_cookie(self):
        self._login_member("bob")
        response = self.client.get(reverse("cdl_communication_page"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)
        self.assertTrue(response.cookies["csrftoken"].value)
