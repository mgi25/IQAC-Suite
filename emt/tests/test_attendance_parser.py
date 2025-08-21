import io
from django.test import SimpleTestCase
from emt.utils import parse_attendance_csv, ATTENDANCE_HEADERS


class AttendanceParserTests(SimpleTestCase):
    def test_parse_valid_csv(self):
        data = io.StringIO()
        data.write(",".join(ATTENDANCE_HEADERS) + "\n")
        data.write("R1,John Doe,Class A,TRUE,FALSE\n")
        data.seek(0)
        rows = parse_attendance_csv(data)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["absent"])
        self.assertFalse(rows[0]["volunteer"])

    def test_header_mismatch(self):
        bad = io.StringIO("A,B,C\n1,2,3\n")
        with self.assertRaises(ValueError):
            parse_attendance_csv(bad)
