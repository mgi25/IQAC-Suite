import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from emt.models import Student


class StudentAcademicApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="student1",
            email="student@example.com",
            password="testpass123",
        )
        self.student = Student.objects.create(user=self.user)
        self.client.defaults['REMOTE_ADDR'] = '127.0.0.1'

    def test_update_academic_information(self):
        self.client.login(username="student1", password="testpass123")
        payload = {
            "registration_number": "21ABC123",
            "department": "Computer Science",
            "academic_year": "2025-2026",
            "current_semester": "Semester 5",
            "gpa": "7.89",
            "major": "Artificial Intelligence",
            "enrollment_year": "2022",
        }

        response = self.client.post(
            reverse("api_update_student_academic"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["success"])
        returned = data["data"]
        self.assertEqual(returned["registration_number"], payload["registration_number"])
        self.assertEqual(returned["department"], payload["department"])
        self.assertEqual(returned["academic_year"], payload["academic_year"])
        self.assertEqual(returned["current_semester"], payload["current_semester"])
        self.assertAlmostEqual(float(returned["gpa"]), float(payload["gpa"]))
        self.assertEqual(returned["major"], payload["major"])
        self.assertEqual(returned["enrollment_year"], int(payload["enrollment_year"]))

        self.student.refresh_from_db()
        self.assertEqual(self.student.registration_number, payload["registration_number"])
        self.assertEqual(self.student.department, payload["department"])
        self.assertEqual(self.student.academic_year, payload["academic_year"])
        self.assertEqual(self.student.current_semester, payload["current_semester"])
        self.assertAlmostEqual(float(self.student.gpa), float(payload["gpa"]))
        self.assertEqual(self.student.major, payload["major"])
        self.assertEqual(self.student.enrollment_year, int(payload["enrollment_year"]))

    def test_update_with_blank_values_clears_fields(self):
        self.student.department = "Commerce"
        self.student.academic_year = "2024-2025"
        self.student.current_semester = "Semester 3"
        self.student.gpa = 6.5
        self.student.major = "Finance"
        self.student.enrollment_year = 2021
        self.student.save()

        self.client.login(username="student1", password="testpass123")
        payload = {
            "department": "",
            "academic_year": None,
            "current_semester": "",
            "gpa": "",
            "major": None,
            "enrollment_year": "",
        }

        response = self.client.post(
            reverse("api_update_student_academic"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        returned = data["data"]
        self.assertIsNone(returned["department"])
        self.assertIsNone(returned["academic_year"])
        self.assertIsNone(returned["current_semester"])
        self.assertIsNone(returned["gpa"])
        self.assertIsNone(returned["major"])
        self.assertIsNone(returned["enrollment_year"])

        self.student.refresh_from_db()
        self.assertIsNone(self.student.department)
        self.assertIsNone(self.student.academic_year)
        self.assertIsNone(self.student.current_semester)
        self.assertIsNone(self.student.gpa)
        self.assertIsNone(self.student.major)
        self.assertIsNone(self.student.enrollment_year)
