from django.core.management.base import BaseCommand
from core.models import SidebarModule
from core.navigation import get_nav_items


class Command(BaseCommand):
    help = "Rebuild (seed/backfill) sidebar modules from static definition and clear cache"

    def handle(self, *args, **options):
        # Seed/backfill
        SidebarModule.ensure_seed_data()
        # Clear cache
        get_nav_items.cache_clear()
        # Force reload
        nav = get_nav_items()
        count = SidebarModule.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Sidebar rebuilt. {count} DB modules. Current nav root count: {len(nav)}"
        ))
