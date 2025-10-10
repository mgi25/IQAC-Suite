import logging

from django.core.management.base import BaseCommand
from django.db.models import Q

from core.models import ActivityLog

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Normalize existing ActivityLog descriptions using generate_description()"

    def handle(self, *args, **options):
        patterns = [
            "performed GET",
            "performed POST",
            "performed PUT",
            "performed PATCH",
            "performed DELETE",
        ]
        query = Q()
        for pattern in patterns:
            query |= Q(description__icontains=pattern)

        count = 0
        for log in ActivityLog.objects.filter(query):
            new_desc = log.generate_description()
            if new_desc != log.description:
                log.description = new_desc
                log.save(update_fields=["description"])
                count += 1
        self.stdout.write(
            self.style.SUCCESS(f"Normalized {count} activity logs.")
        )
