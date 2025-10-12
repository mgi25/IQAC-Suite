import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from emt.models import Student


class StudentPersonalApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="student1",
            email="student@example.com",
            password="testpass123",
            first_name="Original",
            last_name="Name",
        )
        self.student = Student.objects.create(user=self.user, registration_number="OLD123")
        self.client.defaults["REMOTE_ADDR"] = "127.0.0.1"

    def test_update_personal_information(self):
        self.client.login(username="student1", password="testpass123")
        payload = {
            "first_name": "Alice",
            "last_name": "Johnson",
            "registration_number": "21ABC123",
        }

        response = self.client.post(
            reverse("api_update_student_personal"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("data", data)
        returned = data["data"]
        self.assertEqual(returned["first_name"], payload["first_name"])
        self.assertEqual(returned["last_name"], payload["last_name"])
        self.assertEqual(returned["registration_number"], payload["registration_number"])
        self.assertEqual(returned["full_name"], f"{payload['first_name']} {payload['last_name']}")

        self.user.refresh_from_db()
        self.student.refresh_from_db()
        self.assertEqual(self.user.first_name, payload["first_name"])
        self.assertEqual(self.user.last_name, payload["last_name"])
        self.assertEqual(self.student.registration_number, payload["registration_number"])

    def test_update_personal_information_requires_names(self):
        self.client.login(username="student1", password="testpass123")
        payload = {
            "first_name": "",
            "last_name": " ",
            "registration_number": "NEW123",
        }

        response = self.client.post(
            reverse("api_update_student_personal"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("errors", data)
        self.assertIn("first_name", data["errors"])
        self.assertIn("last_name", data["errors"])

        self.user.refresh_from_db()
        self.student.refresh_from_db()
        self.assertEqual(self.user.first_name, "Original")
        self.assertEqual(self.user.last_name, "Name")
        self.assertEqual(self.student.registration_number, "OLD123")

    def test_update_personal_information_without_student_record(self):
        Student.objects.all().delete()
        self.client.login(username="student1", password="testpass123")

        payload = {
            "first_name": "Sam",
            "last_name": "Taylor",
            "registration_number": "IGNORED",
        }

        response = self.client.post(
            reverse("api_update_student_personal"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["registration_number"], "")

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Sam")
        self.assertEqual(self.user.last_name, "Taylor")
