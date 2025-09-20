import io

from django.test import SimpleTestCase

from emt.utils import (COMBINED_ATTENDANCE_HEADERS, FACULTY_ATTENDANCE_HEADERS,
                       STUDENT_ATTENDANCE_HEADERS, parse_attendance_csv)


class AttendanceParserTests(SimpleTestCase):
    def test_parse_combined_csv(self):
        data = io.StringIO()
        data.write(",".join(COMBINED_ATTENDANCE_HEADERS) + "\n")
        data.write("faculty,E1,Jane Doe,Physics,FALSE,TRUE\n")
        data.seek(0)
        rows = parse_attendance_csv(data)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["category"], "faculty")
        self.assertEqual(rows[0]["student_class"], "Physics")
        self.assertTrue(rows[0]["volunteer"])
        self.assertFalse(rows[0]["absent"])

    def test_parse_student_headers_sets_category(self):
        data = io.StringIO()
        data.write(",".join(STUDENT_ATTENDANCE_HEADERS) + "\n")
        data.write("R1,John Doe,Class A,TRUE,FALSE\n")
        data.seek(0)
        rows = parse_attendance_csv(data)
        self.assertEqual(rows[0]["category"], "student")
        self.assertTrue(rows[0]["absent"])
        self.assertFalse(rows[0]["volunteer"])

    def test_parse_faculty_headers_sets_category(self):
        data = io.StringIO()
        data.write(",".join(FACULTY_ATTENDANCE_HEADERS) + "\n")
        data.write("EMP1,Jane Doe,English,FALSE,FALSE\n")
        data.seek(0)
        rows = parse_attendance_csv(data)
        self.assertEqual(rows[0]["category"], "faculty")
        self.assertEqual(rows[0]["student_class"], "English")

    def test_header_mismatch(self):
        bad = io.StringIO("A,B,C\n1,2,3\n")
        with self.assertRaises(ValueError):
            parse_attendance_csv(bad)
