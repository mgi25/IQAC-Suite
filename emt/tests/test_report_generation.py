from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Report
from core.signals import assign_role_on_login, create_or_update_user_profile
from emt.models import EventProposal, EventReport


class ReportGenerationViewsTests(TestCase):
    def test_report_form_route_returns_200(self):
        response = self.client.get(reverse("emt:report_form"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "emt/report_generation.html")

    def test_generate_report_pdf_rejects_non_post(self):
        response = self.client.get(reverse("emt:generate_report_pdf"))
        self.assertEqual(response.status_code, 405)

    @patch("emt.views.pdfkit.from_string", return_value=b"%PDF-1.4 test")
    def test_generate_report_pdf_returns_pdf(self, mock_from_string):
        payload = {
            "event_title": "AI Workshop",
            "event_date": "2024-09-01",
        }
        response = self.client.post(reverse("emt:generate_report_pdf"), data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("Event_Report.pdf", response["Content-Disposition"])
        mock_from_string.assert_called_once()


class EventReportWorkflowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        post_save.disconnect(create_or_update_user_profile, sender=User)
        user_logged_in.disconnect(assign_role_on_login)

    @classmethod
    def tearDownClass(cls):
        user_logged_in.connect(assign_role_on_login)
        post_save.connect(create_or_update_user_profile, sender=User)
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user(username="reporter", password="testpass")
        self.client.force_login(self.user)
        self.proposal = EventProposal.objects.create(
            submitted_by=self.user,
            event_title="Campus Meetup",
            event_datetime=timezone.now(),
        )

    def test_generate_report_populates_ai_fields(self):
        response = self.client.get(
            reverse("emt:generate_report", args=[self.proposal.id])
        )
        self.assertEqual(response.status_code, 302)
        report = EventReport.objects.get(proposal=self.proposal)
        self.assertTrue(report.ai_generated_report)
        self.assertTrue(report.summary)

    def test_download_pdf_uses_event_report_fields(self):
        EventReport.objects.create(
            proposal=self.proposal,
            ai_generated_report="Comprehensive AI content",
            summary="Fallback summary",
        )
        response = self.client.get(
            reverse("emt:download_pdf", args=[self.proposal.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn(self.proposal.event_title, response["Content-Disposition"])

    def test_admin_reports_view_handles_event_reports(self):
        EventReport.objects.create(
            proposal=self.proposal,
            ai_generated_report="Admin table content",
            summary="",
        )
        Report.objects.create(title="Submitted Report", report_type="event")
        response = self.client.get(reverse("emt:admin_reports_view"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Campus Meetup")

    def test_generated_reports_links_resolve(self):
        report = EventReport.objects.create(
            proposal=self.proposal,
            ai_generated_report="Detailed AI write-up",
        )
        response = self.client.get(reverse("emt:generated_reports"))
        self.assertEqual(response.status_code, 200)
        view_url = reverse("emt:view_report", args=[report.id])
        download_url = reverse("emt:download_pdf", args=[self.proposal.id])
        self.assertContains(response, view_url)
        self.assertContains(response, download_url)

        view_response = self.client.get(view_url)
        self.assertEqual(view_response.status_code, 200)
        self.assertContains(view_response, "Detailed AI write-up")

        download_response = self.client.get(download_url)
        self.assertEqual(download_response.status_code, 200)

    def test_submit_event_report_prefills_existing_text(self):
        EventReport.objects.create(
            proposal=self.proposal,
            summary="Stored summary text",
            outcomes="Documented outcomes",
        )
        response = self.client.get(
            reverse("emt:submit_event_report", args=[self.proposal.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Stored summary text")
        self.assertContains(response, "Documented outcomes")

    def test_view_report_prefers_ai_text_and_download_link(self):
        report = EventReport.objects.create(
            proposal=self.proposal,
            ai_generated_report="AI generated narrative",
            summary="Concise fallback summary",
        )
        response = self.client.get(reverse("emt:view_report", args=[report.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI generated narrative")
        download_url = reverse("emt:download_pdf", args=[self.proposal.id])
        self.assertContains(response, download_url)
        download_response = self.client.get(download_url)
        self.assertEqual(download_response.status_code, 200)

    def test_view_report_falls_back_to_summary(self):
        report = EventReport.objects.create(
            proposal=self.proposal,
            summary="Only summary available",
        )
        response = self.client.get(reverse("emt:view_report", args=[report.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Only summary available")
