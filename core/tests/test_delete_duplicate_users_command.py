from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth import get_user_model


class DeleteDuplicateUsersCommandTests(TestCase):
    def test_duplicates_removed(self):
        User = get_user_model()
        User.objects.create(username="user1", email="dup@example.com")
        User.objects.create(username="user2", email="dup@example.com")
        User.objects.create(username="user3", email="unique@example.com")

        call_command("delete_duplicate_users")

        self.assertEqual(User.objects.filter(email__iexact="dup@example.com").count(), 1)
        self.assertEqual(User.objects.count(), 2)
