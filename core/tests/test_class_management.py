from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Class, Organization, OrganizationType


class ClassManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin", "admin@example.com", "pass")
        ot = OrganizationType.objects.create(name="Dept")
        self.org = Organization.objects.create(name="Math", org_type=ot)
        self.cls = Class.objects.create(
            name="ActiveClass", code="A", organization=self.org
        )

    def test_class_toggle_archives(self):
        self.client.force_login(self.admin)
        url = reverse("admin_org_users_class_toggle", args=[self.org.id, self.cls.id])
        self.assertTrue(self.cls.is_active)
        self.client.post(url)
        self.cls.refresh_from_db()
        self.assertFalse(self.cls.is_active)

    def test_students_view_filters_active_and_archived(self):
        _ = Class.objects.create(
            name="ArchivedClass", code="B", organization=self.org, is_active=False
        )
        self.client.force_login(self.admin)
        url = reverse("admin_org_users_students", args=[self.org.id])
        resp = self.client.get(url)
        self.assertContains(resp, self.cls.name)
        self.assertNotContains(resp, "ArchivedClass")
        resp = self.client.get(url + "?archived=1")
        self.assertContains(resp, "ArchivedClass")
        self.assertNotContains(resp, self.cls.name)

    def test_toggle_redirect_retains_archived_param(self):
        self.client.force_login(self.admin)
        self.cls.is_active = False
        self.cls.save()
        url = (
            reverse("admin_org_users_class_toggle", args=[self.org.id, self.cls.id])
            + "?archived=1"
        )
        resp = self.client.post(url)
        expected = (
            reverse("admin_org_users_students", args=[self.org.id]) + "?archived=1"
        )
        self.assertEqual(resp["Location"], expected)

    def test_user_activate(self):
        user = User.objects.create_user(
            "stud", "stud@example.com", "pass", is_active=False
        )
        self.client.force_login(self.admin)
        url = reverse("admin_user_activate", args=[user.id])
        self.client.post(url, {"next": "/"})
        user.refresh_from_db()
        self.assertTrue(user.is_active)
