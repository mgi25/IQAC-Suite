from django.core.management.base import BaseCommand
from transcript.models import AcademicYear


class Command(BaseCommand):
    """Delete AcademicYear entries for a specified year."""
    help = "Delete AcademicYear entries matching the given year string."

    def add_arguments(self, parser):
        parser.add_argument("year", help="Year value to delete, e.g., 2025-2026")

    def handle(self, *args, **options):
        year = options["year"]
        deleted, _ = AcademicYear.objects.filter(year=year).delete()
        if deleted:
            self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} AcademicYear(s) with year '{year}'."))
        else:
            self.stdout.write(self.style.WARNING(f"No AcademicYear found with year '{year}'."))
