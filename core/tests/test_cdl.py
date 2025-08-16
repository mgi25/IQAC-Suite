from django.test import TestCase
from django.contrib.auth.models import User
from emt.models import EventProposal
from core.models import CDLRequest, CertificateBatch, CertificateEntry
from core.forms import CDLRequestForm
from core.views import run_ai_validation


class CDLModelFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.proposal = EventProposal.objects.create(submitted_by=self.user)

    def test_cdlrequest_one_to_one(self):
        cdl = CDLRequest.objects.create(proposal=self.proposal, wants_cdl=True)
        self.assertEqual(cdl.proposal, self.proposal)

    def test_cdl_form_poster_requires_details(self):
        form = CDLRequestForm(data={"wants_cdl": True, "need_poster": True})
        self.assertFalse(form.is_valid())
        self.assertIn("poster_organization_name", form.errors)

    def test_certificate_ai_validation(self):
        batch = CertificateBatch.objects.create(proposal=self.proposal, csv_file="dummy.csv")
        CertificateEntry.objects.create(batch=batch, name="", role="OTHER")
        run_ai_validation(batch)
        entry = batch.entries.first()
        self.assertFalse(entry.ai_valid)
        self.assertEqual(batch.ai_check_status, CertificateBatch.AIStatus.FAILED)
