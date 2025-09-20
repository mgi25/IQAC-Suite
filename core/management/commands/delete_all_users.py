from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Delete all user accounts."""

    help = "Remove all users from the database. Use with caution."

    def handle(self, *args, **options):
        User = get_user_model()
        count = User.objects.count()
        User.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} user(s)."))
