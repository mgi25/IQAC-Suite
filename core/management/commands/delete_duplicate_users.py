from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models.functions import Lower


class Command(BaseCommand):
    """Remove duplicate user accounts based on email."""

    help = (
        "Remove duplicate user accounts based on email (case-insensitive). "
        "Keeps the oldest account and deletes the rest."
    )

    def handle(self, *args, **options):
        User = get_user_model()
        duplicates = (
            User.objects.exclude(email__isnull=True)
            .exclude(email__exact="")
            .annotate(email_lower=Lower("email"))
            .values("email_lower")
            .annotate(email_count=Count("id"))
            .filter(email_count__gt=1)
        )

        total_deleted = 0
        for entry in duplicates:
            email = entry["email_lower"]
            users = User.objects.filter(email__iexact=email).order_by("id")
            keeper = users.first()
            to_delete = users[1:]
            count = to_delete.count()
            if count:
                User.objects.filter(
                    id__in=list(to_delete.values_list("id", flat=True))
                ).delete()
                total_deleted += count
                self.stdout.write(
                    self.style.WARNING(
                        f"Deleted {count} duplicate user(s) with email {email}; kept user {keeper.id}."
                    )
                )

        if total_deleted:
            self.stdout.write(
                self.style.SUCCESS(f"Deleted {total_deleted} duplicate user(s).")
            )
        else:
            self.stdout.write(self.style.SUCCESS("No duplicate users found."))
