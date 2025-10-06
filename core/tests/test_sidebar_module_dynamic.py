from django.test import TestCase
from django.contrib.auth.models import User

from core.models import SidebarModule
from core.navigation import get_nav_items


class SidebarModuleDynamicTests(TestCase):
    def setUp(self):
        # Ensure seed data present
        SidebarModule.ensure_seed_data()
        get_nav_items.cache_clear()

    def test_cache_invalidated_on_create(self):
        initial = get_nav_items()
        root_count = len(initial)
        SidebarModule.objects.create(key="custom_root", label="Custom Root")
        # cache should auto-clear via signal
        refreshed = get_nav_items()
        self.assertEqual(len(refreshed), root_count + 1)
        self.assertTrue(any(i["id"] == "custom_root" for i in refreshed))

    def test_cache_invalidated_on_delete(self):
        m = SidebarModule.objects.create(key="temp_root", label="Temp Root")
        get_nav_items.cache_clear()  # ensure it's visible first
        _ = get_nav_items()  # prime cache
        m.delete()  # signal should clear
        after = get_nav_items()
        self.assertFalse(any(i.get("id") == "temp_root" for i in after))

    def test_is_active_false_excluded(self):
        m = SidebarModule.objects.create(key="inactive_root", label="Inactive Root", is_active=False)
        get_nav_items.cache_clear()
        nav = get_nav_items()
        self.assertFalse(any(i.get("id") == "inactive_root" for i in nav))
