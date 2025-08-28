from datetime import date
import json
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in

from core.signals import create_or_update_user_profile, assign_role_on_login

from emt.models import EventProposal, EventActivity, EventReport, AttendanceRow
from emt.forms import EventReportForm


class SubmitEventReportViewTests(TestCase):
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
        self.user = User.objects.create_user(username="alice", password="pass")
        self.client.force_login(self.user)
        self.proposal = EventProposal.objects.create(
            submitted_by=self.user,
            event_title="Sample Event",
        )
        EventActivity.objects.create(
            proposal=self.proposal,
            name="Orientation",
            date=date(2024, 1, 1),
        )

    def test_activities_prefilled_in_report_form(self):
        response = self.client.get(
            reverse("emt:submit_event_report", args=[self.proposal.id])
        )
        self.assertEqual(response.status_code, 200)
        # Activity row should be pre-filled
        self.assertContains(
            response,
            'name="activity_name_1" value="Orientation"',
            html=False,
        )
        self.assertContains(
            response,
            'name="activity_date_1" value="2024-01-01"',
            html=False,
        )
        # Hidden count of activities
        self.assertContains(response, 'id="num-activities-modern"', html=False)
        self.assertContains(response, 'name="num_activities"', html=False)
        self.assertContains(response, 'value="1"', html=False)
        # Dynamic editing controls are managed client-side; server renders activity inputs

    def test_can_update_activities_via_report_submission(self):
        url = reverse("emt:submit_event_report", args=[self.proposal.id])
        data = {
            "actual_event_type": "Seminar",
            "report_signed_date": "2024-01-10",
            "num_activities": "2",
            "activity_name_1": "Session 1",
            "activity_date_1": "2024-01-02",
            "activity_name_2": "Session 2",
            "activity_date_2": "2024-01-03",
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        activities = list(EventActivity.objects.filter(proposal=self.proposal).order_by("date"))
        self.assertEqual(len(activities), 2)
        self.assertEqual(activities[0].name, "Session 1")
        self.assertEqual(activities[1].name, "Session 2")

    def test_attendance_counts_displayed(self):
        report = EventReport.objects.create(proposal=self.proposal)
        AttendanceRow.objects.create(
            event_report=report,
            registration_no="R1",
            full_name="Bob",
            student_class="CSE",
            absent=False,
            volunteer=True,
        )
        AttendanceRow.objects.create(
            event_report=report,
            registration_no="R2",
            full_name="Carol",
            student_class="CSE",
            absent=True,
            volunteer=False,
        )
        response = self.client.get(
            reverse("emt:submit_event_report", args=[self.proposal.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'Present: 1, Absent: 1, Volunteers: 1',
            html=False,
        )

    def test_attendance_link_opens_without_preexisting_report(self):
        url = reverse("emt:submit_event_report", args=[self.proposal.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Help text should always instruct click-to-manage
        self.assertContains(
            response, "Click attendance box to manage via CSV", html=False
        )
        self.assertNotContains(response, "data-attendance-url", html=False)

        report = EventReport.objects.create(proposal=self.proposal)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "Click attendance box to manage via CSV", html=False
        )
        attendance_url = reverse("emt:attendance_upload", args=[report.id])
        self.assertContains(
            response,
            f'data-attendance-url="{attendance_url}"',
            html=False,
        )

    def test_attendance_link_updates_after_autosave(self):
        url = reverse("emt:submit_event_report", args=[self.proposal.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "data-attendance-url", html=False)

        autosave_url = reverse("emt:autosave_event_report")
        res = self.client.post(
            autosave_url,
            data=json.dumps({"proposal_id": self.proposal.id}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        report_id = res.json()["report_id"]
        attendance_url = reverse("emt:attendance_upload", args=[report_id])

        # Run a tiny Node script that loads initializeAutosaveIndicators, dispatches
        # autosave:success via $(document).trigger and prints the updated link.
        import tempfile
        import subprocess
        from pathlib import Path

        submit_js = Path(__file__).resolve().parents[1] / "static" / "emt" / "js" / "submit_event_report.js"
        node_script = '''
const fs = require('fs');
const src = fs.readFileSync('__SUBMIT_JS__', 'utf8');
function extract(name){
  const start=src.indexOf('function '+name);
  if(start===-1) throw new Error('not found');
  let idx=src.indexOf('{', start);let depth=1;idx++;
  while(idx<src.length && depth>0){if(src[idx]=='{')depth++;else if(src[idx]=='}')depth--;idx++;}
  return src.slice(start, idx);
}
const initCode = extract('initializeAutosaveIndicators');
const setupCode = extract('setupAttendanceLink');
const handlers={};
const document={};
const docObj={
  on:(ev,fn)=>{(handlers[ev]=handlers[ev]||[]).push(fn);return docObj;},
  trigger:(ev,data)=>{(handlers[ev]||[]).forEach(fn=>fn({type:ev}, data));},
  off:()=>docObj
};
function $(sel){
 if(sel===document) return docObj;
 if(sel==='#attendance-modern') return attendanceEl;
 if(sel==='#autosave-indicator') return indicatorEl;
}
const attendanceEl={attrs:{},dataStore:{},length:1,
  attr:function(n,v){if(v===undefined)return this.attrs[n];this.attrs[n]=v;return this;},
  data:function(n,v){if(v===undefined)return this.dataStore[n];this.dataStore[n]=v;return this;},
  prop:function(){return this;},
  css:function(){return this;}
};
const indicatorEl={removeClass:function(){return this;},addClass:function(){return this;},find:function(){return {text:function(){}};},length:1};
const window={location:{}};
eval(setupCode);
eval(initCode);
initializeAutosaveIndicators();
$(document).trigger('autosave:success', {reportId:__REPORT_ID__});
console.log(attendanceEl.attrs['href']);
'''
        node_script = node_script.replace('__SUBMIT_JS__', str(submit_js)).replace('__REPORT_ID__', str(report_id))
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "run.js"
            script_path.write_text(node_script)
            result = subprocess.run(["node", str(script_path)], capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), attendance_url)

    def test_autosave_indicator_present(self):
        response = self.client.get(
            reverse("emt:submit_event_report", args=[self.proposal.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="autosave-indicator"', html=False)

    def test_preview_event_report(self):
        url = reverse("emt:preview_event_report", args=[self.proposal.id])
        data = {
            "actual_event_type": "Seminar",
            "report_signed_date": "2024-01-10",
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Seminar")

    def test_preview_renders_multiple_sections_data(self):
        url = reverse("emt:preview_event_report", args=[self.proposal.id])
        data = {
            "actual_event_type": "Workshop",
            "summary": "Section summary text",
            "outcomes": "Outcome details",
            "graduate_attributes": ["engineering_knowledge", "problem_analysis"],
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        # Verify fields from multiple sections appear in the preview
        self.assertContains(response, "Workshop")
        self.assertContains(response, "Section summary text")
        self.assertContains(response, "Outcome details")
        # Multi-select values should be preserved in POST data
        self.assertEqual(
            response.context["form"].data.getlist("graduate_attributes"),
            ["engineering_knowledge", "problem_analysis"],
        )

    def test_preview_preserves_checked_and_unchecked_fields(self):
        url = reverse("emt:preview_event_report", args=[self.proposal.id])
        data = {
            "actual_event_type": "Seminar",
            "report_signed_date": "2024-01-10",
            "needs_projector": "yes",  # Simulate checked checkbox
            "needs_permission": "",    # Simulate unchecked checkbox
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["post_data"]["needs_projector"], "yes")
        self.assertEqual(response.context["post_data"]["needs_permission"], "")

    def test_preview_includes_all_form_fields(self):
        url = reverse("emt:preview_event_report", args=[self.proposal.id])
        data = {
            "actual_event_type": "Seminar",
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        form = EventReportForm()
        for field in form.fields.values():
            self.assertContains(
                response, f"<strong>{field.label}:</strong>", html=False
            )

