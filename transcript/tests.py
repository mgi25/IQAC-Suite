from django.test import TestCase
from datetime import date

from .models import (
    GraduateAttribute,
    CharacterStrength,
    AttributeStrengthMap,
    AcademicYear,
    School,
    Course,
    Student,
    Event,
    Role,
    Participation,
)
from .views import calculate_strength_data


class StrengthCalculationTests(TestCase):
    def test_calculate_strength_data_returns_scores(self):
        ga = GraduateAttribute.objects.create(name="GA1")
        cs = CharacterStrength.objects.create(name="CS1")
        AttributeStrengthMap.objects.create(
            graduate_attribute=ga,
            character_strength=cs,
            weight=1.0,
        )

        school = School.objects.create(name="School")
        course = Course.objects.create(name="Course", school=school)
        year = AcademicYear.objects.create(year="2024")
        student = Student.objects.create(
            roll_no="1",
            name="Student",
            school=school,
            course=course,
            academic_year=year,
        )

        role = Role.objects.create(name="First Level", factor=1.0)
        event = Event.objects.create(name="Event", date=date.today())
        event.attributes.add(ga)

        Participation.objects.create(student=student, event=event, role=role)

        strength_data, participations = calculate_strength_data(student)

        self.assertEqual(participations.count(), 1)
        self.assertTrue(any(s["average"] > 0 for s in strength_data))
