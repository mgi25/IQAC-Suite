from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from core.models import Profile, RoleAssignment


class Command(BaseCommand):
    """Backfill roles for all users based on email domain."""

    help = "Assign roles to users and clean up mismatched role assignments"

    def handle(self, *args, **options):
        for user in User.objects.all():
            email = (user.email or "").lower()
            domain = email.split("@")[-1]
            role = "student" if domain.endswith("christuniversity.in") else "faculty"

            profile, _ = Profile.objects.get_or_create(user=user)
            if profile.role != role:
                profile.role = role
                profile.save(update_fields=["role"])
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Updated {user.username} profile role to {role}"
                    )
                )

            removed, _ = (
                RoleAssignment.objects.filter(user=user)
                .exclude(role__name__iexact=role)
                .delete()
            )
            if removed:
                self.stdout.write(
                    f"Removed {removed} RoleAssignment(s) for {user.username}"
                )

        self.stdout.write(self.style.SUCCESS("Backfill complete"))
