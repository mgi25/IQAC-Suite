from django.core.management.base import BaseCommand

from core.models import SDG_GOALS, SDGGoal


class Command(BaseCommand):
    """Seed the database with the predefined SDG goals."""

    help = "Populate the SDGGoal table with standard Sustainable Development Goals"

    def handle(self, *args, **options):
        for name in SDG_GOALS:
            _, created = SDGGoal.objects.get_or_create(name=name)
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Added SDG goal '{name}'")
                )
        SDGGoal.objects.exclude(name__in=SDG_GOALS).delete()
        self.stdout.write(self.style.SUCCESS("SDG goals seeding complete."))
