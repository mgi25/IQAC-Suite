from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from emt.models import EventProposal


class UserDashboardCalendarTests(TestCase):
    def test_past_and_future_events_included(self):
        user = User.objects.create_user(username="user", password="pass")
        past_date = timezone.now() - timezone.timedelta(days=5)
        future_date = timezone.now() + timezone.timedelta(days=5)
        EventProposal.objects.create(
            submitted_by=user,
            event_title="Past",
            status=EventProposal.Status.APPROVED,
            event_datetime=past_date,
        )
        EventProposal.objects.create(
            submitted_by=user,
            event_title="Future",
            status=EventProposal.Status.APPROVED,
            event_datetime=future_date,
        )
        self.client.force_login(user)
        response = self.client.get(reverse("user_dashboard"))
        self.assertEqual(response.status_code, 200)
        events = response.context["calendar_events"]
        dates = {e.get("date") for e in events}
        self.assertIn(past_date.date().isoformat(), dates)
        self.assertIn(future_date.date().isoformat(), dates)

    def test_includes_events_from_other_users(self):
        user = User.objects.create_user(username="user", password="pass")
        other = User.objects.create_user(username="other", password="pass")
        date = timezone.now()
        EventProposal.objects.create(
            submitted_by=other,
            event_title="Other",
            status=EventProposal.Status.APPROVED,
            event_datetime=date,
        )
        self.client.force_login(user)
        response = self.client.get(reverse("user_dashboard"))
        events = response.context["calendar_events"]
        dates = {e.get("date") for e in events}
        self.assertIn(date.date().isoformat(), dates)
