import json
from datetime import date
from html.parser import HTMLParser
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.test import TestCase
from django.urls import reverse
from django.utils.formats import date_format
from django.http import QueryDict

from core.models import Organization, OrganizationType, SDGGoal
from core.signals import assign_role_on_login, create_or_update_user_profile
from emt.forms import EventReportForm
from emt.models import (AttendanceRow, CDLSupport, EventActivity, EventProposal,
                        EventReport, SpeakerProfile)


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

    def _build_valid_report_post_data(self, extra=None):
        data = {
            "actual_event_type": "Seminar",
            "report_signed_date": "2024-01-10",
            "num_activities": "1",
            "activity_name_1": "Session 1",
            "activity_date_1": "2024-01-02",
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }
        if extra:
            data.update(extra)
        return data

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
        data = self._build_valid_report_post_data(
            {
                "num_activities": "2",
                "activity_name_2": "Session 2",
                "activity_date_2": "2024-01-03",
            }
        )
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "emt/report_preview.html")
        self.assertNotContains(response, 'id="generate-ai-report"', html=False)
        activities = list(
            EventActivity.objects.filter(proposal=self.proposal).order_by("date")
        )
        self.assertEqual(len(activities), 2)
        self.assertEqual(activities[0].name, "Session 1")
        self.assertEqual(activities[1].name, "Session 2")

    def test_submit_event_report_without_generate_ai_renders_preview(self):
        url = reverse("emt:submit_event_report", args=[self.proposal.id])
        response = self.client.post(url, self._build_valid_report_post_data())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "emt/report_preview.html")
        self.assertNotContains(response, 'id="generate-ai-report"', html=False)
        self.assertContains(response, 'data-preview-continue="iqac"', html=False)

    def test_submit_event_report_with_generate_ai_redirects_to_progress(self):
        url = reverse("emt:submit_event_report", args=[self.proposal.id])
        data = self._build_valid_report_post_data({"generate_ai": "1"})
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        progress_url = reverse("emt:ai_report_progress", args=[self.proposal.id])
        self.assertEqual(response["Location"], progress_url)

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
            "Present: 1, Absent: 1, Volunteers: 1",
            html=False,
        )

    def test_prefill_venue_uses_proposal_when_autosave_blank(self):
        self.proposal.venue = "Innovation Hall"
        self.proposal.save(update_fields=["venue"])

        EventReport.objects.create(
            proposal=self.proposal,
            generated_payload={"venue": ""},
        )

        session = self.client.session
        session.setdefault("event_report_draft", {})[str(self.proposal.id)] = {
            "venue": "",
        }
        session.save()

        response = self.client.get(
            reverse("emt:submit_event_report", args=[self.proposal.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["prefill_venue"], "Innovation Hall")
        html = response.content.decode()
        self.assertIn("Innovation Hall", html)

    def test_attendance_link_opens_without_preexisting_report(self):
        url = reverse("emt:submit_event_report", args=[self.proposal.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Help text should always instruct click-to-manage
        self.assertContains(
            response, "Click attendance box to manage via CSV", html=False
        )
        self.assertNotIn('data-attendance-url="', response.content.decode())

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
        self.assertNotIn('data-attendance-url="', response.content.decode())

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
        import subprocess
        import tempfile
        from pathlib import Path

        submit_js = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "emt"
            / "js"
            / "submit_event_report.js"
        )
        node_script = """
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
 if(sel===attendanceEl || sel==='#attendance-modern') return attendanceEl;
 if(sel===participantsEl || sel==='#num-participants-modern' || sel==='#total-participants-modern') return participantsEl;
 if(typeof sel === 'string' && sel.includes('#attendance-modern') && sel.includes('num-participants-modern')) return combinedFields;
 if(typeof sel === 'string' && sel.includes('num-participants-modern')) return participantsEl;
 if(sel==='#autosave-indicator') return indicatorEl;
}
let combinedFields;
const attendanceEl={attrs:{},dataStore:{},length:1,
  attr:function(n,v){if(v===undefined)return this.attrs[n];this.attrs[n]=v;return this;},
  data:function(n,v){if(v===undefined)return this.dataStore[n];this.dataStore[n]=v;return this;},
  prop:function(){return this;},
  css:function(){return this;},
  add:function(){return combinedFields;}
};
const participantsEl={attrs:{},dataStore:{},length:1,
  attr:function(n,v){if(v===undefined)return this.attrs[n];this.attrs[n]=v;return this;},
  data:function(n,v){if(v===undefined)return this.dataStore[n];this.dataStore[n]=v;return this;},
  prop:function(){return this;},
  css:function(){return this;},
  add:function(){return combinedFields;}
};
combinedFields={
  length:2,
  attr:function(n,v){if(v===undefined)return attendanceEl.attrs[n]||participantsEl.attrs[n];attendanceEl.attr(n,v);participantsEl.attr(n,v);return this;},
  data:function(n,v){if(v===undefined)return attendanceEl.data(n);attendanceEl.data(n,v);participantsEl.data(n,v);return this;},
  prop:function(){return this;},
  css:function(){return this;},
  each:function(cb){[attendanceEl,participantsEl].forEach((el,idx)=>cb.call(el, idx, el));return this;}
};
const indicatorEl={
  removeClass:function(){return this;},
  addClass:function(){return this;},
  find:function(){return {text:function(){}};},
  length:1
};
const window={location:{pathname:'/suite/reports/preview/'}};
global.window = window;
global.document = document;
eval(setupCode);
eval(initCode);
initializeAutosaveIndicators();
$(document).trigger('autosave:success', {reportId: __REPORT_ID__});
console.log(JSON.stringify({
  att: attendanceEl.attrs['href'],
  part: participantsEl.attrs['href'],
}));
"""
        node_script = node_script.replace("__SUBMIT_JS__", str(submit_js)).replace(
            "__REPORT_ID__", str(report_id)
        )
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "run.js"
            script_path.write_text(node_script)
            result = subprocess.run(
                ["node", str(script_path)], capture_output=True, text=True
            )
        out = json.loads(result.stdout.strip())
        self.assertEqual(out["att"], attendance_url)
        self.assertEqual(out["part"], attendance_url)

    def test_attendance_identifiers_populate_on_admin_route(self):
        report = EventReport.objects.create(proposal=self.proposal)

        response = self.client.get(
            reverse("emt:submit_event_report", args=[self.proposal.id])
        )
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn(
            f'data-proposal-id="{self.proposal.id}"',
            html,
        )
        self.assertIn(
            f'data-report-id="{report.id}"',
            html,
        )

        import subprocess
        import tempfile
        from pathlib import Path

        submit_js = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "emt"
            / "js"
            / "submit_event_report.js"
        )

        node_script = """
const fs = require('fs');
const vm = require('vm');
const src = fs.readFileSync('__SUBMIT_JS__', 'utf8');
function extract(name){
  const start = src.indexOf('function ' + name);
  if(start === -1) throw new Error('not found: ' + name);
  let idx = src.indexOf('{', start);
  let depth = 1;
  idx++;
  while(idx < src.length && depth > 0){
    const ch = src[idx];
    if(ch === '{') depth++;
    else if(ch === '}') depth--;
    idx++;
  }
  return src.slice(start, idx);
}
const inferCode = extract('function inferProposalId');
const ensureCode = extract('function ensureReportIdForAttendance');
const context = {
  window: {
    location: { pathname: '__ADMIN_PATH__' },
    PROPOSAL_ID: '',
    REPORT_ID: ''
  },
  document: {
    getElementById: (id) => {
      if (id === 'report-form') {
        return {
          dataset: {
            proposalId: '__PROPOSAL_ID__',
            reportId: '__REPORT_ID__'
          }
        };
      }
      return null;
    }
  },
  console: console
};
context.window.document = context.document;
context.globalThis = context;
context.output = null;
vm.createContext(context);
vm.runInContext(`${inferCode}\n${ensureCode}\noutput = ensureReportIdForAttendance();`, context);
console.log(JSON.stringify({
  proposal: context.output.proposalId,
  report: context.output.reportId,
  windowProposal: context.window.PROPOSAL_ID,
  windowReport: context.window.REPORT_ID
}));
"""

        node_script = node_script.replace("__SUBMIT_JS__", str(submit_js))
        node_script = node_script.replace(
            "__ADMIN_PATH__",
            f"/admin/emt/report/submit/{self.proposal.id}/",
        )
        node_script = node_script.replace("__PROPOSAL_ID__", str(self.proposal.id))
        node_script = node_script.replace("__REPORT_ID__", str(report.id))

        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "check.js"
            script_path.write_text(node_script)
            result = subprocess.run(
                ["node", str(script_path)], capture_output=True, text=True
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout.strip())
        self.assertEqual(payload["proposal"], str(self.proposal.id))
        self.assertEqual(payload["report"], str(report.id))
        self.assertEqual(payload["windowProposal"], str(self.proposal.id))
        self.assertEqual(payload["windowReport"], str(report.id))

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

    def test_preview_event_report_with_show_iqac_flag(self):
        url = reverse("emt:preview_event_report", args=[self.proposal.id])
        data = {
            "actual_event_type": "Seminar",
            "report_signed_date": "2024-01-10",
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "show_iqac": "1",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "emt/iqac_report_preview.html")
        self.assertNotIn("show_iqac", response.context["post_data"])

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

    def test_preview_maps_frontend_field_names(self):
        url = reverse("emt:preview_event_report", args=[self.proposal.id])
        data = {
            "actual_event_type": "Workshop",
            "event_summary": "Frontend summary",
            "event_outcomes": "Frontend outcomes",
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Frontend summary")
        self.assertContains(response, "Frontend outcomes")

    def test_preview_includes_generate_report_link(self):
        url = reverse("emt:preview_event_report", args=[self.proposal.id])
        data = {
            "actual_event_type": "Seminar",
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "show_iqac": "1",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "emt/iqac_report_preview.html")
        ai_url = reverse("emt:ai_generate_report", args=[self.proposal.id])
        self.assertEqual(response.context["ai_report_url"], ai_url)
        self.assertContains(response, 'id="generate-ai-report"', html=False)
        submit_url = reverse("emt:submit_event_report", args=[self.proposal.id])
        self.assertContains(response, 'id="generate-ai-form"', html=False)
        self.assertContains(response, f'action="{submit_url}"', html=False)
        self.assertContains(response, 'name="generate_ai"', html=False)

    def test_preview_shows_selected_sdg_goals(self):
        goal = SDGGoal.objects.create(name="Quality Education")
        self.proposal.sdg_goals.add(goal)

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
        self.assertContains(response, f"SDG {goal.id}: {goal.name}")

        report_fields = response.context["report_fields"]
        self.assertIn(
            ("Aligned SDG Goals", f"SDG {goal.id}: {goal.name}"),
            report_fields,
        )

    def test_preview_uses_posted_sdg_value_systems_mapping(self):
        goal = SDGGoal.objects.create(name="Climate Action")

        url = reverse("emt:preview_event_report", args=[self.proposal.id])
        data = {
            "actual_event_type": "Workshop",
            "sdg_value_systems_mapping": f"SDG {goal.id}: {goal.name}",
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"SDG {goal.id}: {goal.name}")

        report_fields = response.context["report_fields"]
        self.assertIn(
            ("Aligned SDG Goals", f"SDG {goal.id}: {goal.name}"),
            report_fields,
        )

    def test_preview_preserves_checked_and_unchecked_fields(self):
        url = reverse("emt:preview_event_report", args=[self.proposal.id])
        data = {
            "actual_event_type": "Seminar",
            "report_signed_date": "2024-01-10",
            "needs_projector": "yes",  # Simulate checked checkbox
            "needs_permission": "",  # Simulate unchecked checkbox
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["post_data"]["needs_projector"], "yes")
        self.assertEqual(response.context["post_data"]["needs_permission"], "")

    def test_preview_includes_expected_report_fields(self):
        url = reverse("emt:preview_event_report", args=[self.proposal.id])
        data = {
            "department": "Data Science Department",
            "event_title": "Updated Symposium",
            "venue": "Innovation Hall",
            "event_start_date": "2024-02-01",
            "event_end_date": "2024-02-02",
            "academic_year": "2024-2025",
            "actual_event_type": "Seminar",
            "event_summary": "Highlights of the event",
            "event_outcomes": "Outcome details",
            "analysis": "Detailed analysis",
            "participant_feedback": "Great feedback",
            "measurable_outcomes": "Measured results",
            "impact_assessment": "Lasting impact",
            "objective_achievement": "Objectives met",
            "strengths_analysis": "Key strengths",
            "challenges_analysis": "Challenges faced",
            "effectiveness_analysis": "Effectiveness review",
            "lessons_learned": "Lessons captured",
            "pos_pso_mapping": "PO1, PSO1",
            "needs_grad_attr_mapping": "GA1",
            "contemporary_requirements": "Requirement summary",
            "sdg_value_systems_mapping": "SDG1",
            "actual_speakers": "Keynote and panelists",
            "external_contact_details": "",
            "impact_on_stakeholders": "Positive impact on alumni",
            "innovations_best_practices": "Introduced blended format",
            "iqac_feedback": "IQAC shared guidance",
            "beneficiaries_details": "Students and faculty",
            "attendance_notes": "",
            "report_signed_date": "2024-02-05",
            "num_participants": "50",
            "num_student_volunteers": "5",
            "num_student_participants": "30",
            "num_faculty_participants": "10",
            "num_external_participants": "10",
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)

        proposal = response.context["proposal"]
        self.assertEqual(proposal.event_title, "Updated Symposium")
        self.assertEqual(proposal.venue, "Innovation Hall")

        report_fields = response.context["report_fields"]
        labels = [label for label, _ in report_fields]

        manual_pairs = report_fields[:6]
        manual_dict = {label: value for label, value in manual_pairs}
        expected_start = date_format(date(2024, 2, 1), "DATE_FORMAT")
        expected_end = date_format(date(2024, 2, 2), "DATE_FORMAT")

        self.assertEqual(manual_dict.get("Department"), "Data Science Department")
        self.assertEqual(manual_dict.get("Event Title"), "Updated Symposium")
        self.assertEqual(manual_dict.get("Venue"), "Innovation Hall")
        self.assertEqual(manual_dict.get("Event Start Date"), expected_start)
        self.assertEqual(manual_dict.get("Event End Date"), expected_end)
        self.assertEqual(manual_dict.get("Academic Year"), "2024-2025")

        # Ensure representative report fields still render
        self.assertIn("Summary", labels)
        self.assertIn("Participant feedback", labels)

        report_dict = {label: value for label, value in report_fields}
        form = response.context["form"]

        self.assertEqual(
            report_dict.get(form.fields["actual_speakers"].label),
            "Keynote and panelists",
        )
        self.assertEqual(
            report_dict.get(form.fields["external_contact_details"].label),
            "—",
        )
        self.assertEqual(
            report_dict.get(form.fields["impact_on_stakeholders"].label),
            "Positive impact on alumni",
        )
        self.assertEqual(
            report_dict.get(form.fields["innovations_best_practices"].label),
            "Introduced blended format",
        )
        self.assertEqual(
            report_dict.get(form.fields["iqac_feedback"].label),
            "IQAC shared guidance",
        )
        self.assertEqual(
            report_dict.get(form.fields["beneficiaries_details"].label),
            "Students and faculty",
        )
        self.assertEqual(
            report_dict.get(form.fields["attendance_notes"].label),
            "—",
        )
        expected_signed = date_format(date(2024, 2, 5), "DATE_FORMAT")
        self.assertEqual(
            report_dict.get(form.fields["report_signed_date"].label),
            expected_signed,
        )

    def test_preview_initial_json_includes_participant_counts(self):
        EventReport.objects.create(
            proposal=self.proposal,
            num_participants=55,
            num_student_volunteers=12,
        )

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

        payload = json.loads(response.context["initial_report_data"])
        participants = payload.get("participants", {})

        self.assertEqual(participants.get("attendees_count"), "55")
        self.assertEqual(participants.get("participants_count"), "55")
        self.assertEqual(participants.get("student_volunteers"), "12")
        self.assertEqual(
            participants.get("organising_committee", {}).get("student_volunteers_count"),
            "12",
        )

    def test_preview_initial_json_uses_posted_participant_counts(self):
        url = reverse("emt:preview_event_report", args=[self.proposal.id])
        data = {
            "actual_event_type": "Workshop",
            "num_participants": "8",
            "num_student_volunteers": "1",
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)

        payload = json.loads(response.context["initial_report_data"])
        participants = payload.get("participants", {})

        self.assertEqual(participants.get("attendees_count"), "8")
        self.assertEqual(participants.get("participants_count"), "8")
        self.assertEqual(participants.get("student_volunteers"), "1")
        self.assertEqual(
            participants.get("organising_committee", {}).get("student_volunteers_count"),
            "1",
        )

    def test_preview_shows_dynamic_committee_and_speaker_details(self):
        speaker = SpeakerProfile.objects.create(
            proposal=self.proposal,
            full_name="Dr. Ada Lovelace",
            designation="Keynote Speaker",
        )

        url = reverse("emt:preview_event_report", args=[self.proposal.id])
        data = {
            "actual_event_type": "Seminar",
            "report_signed_date": "2024-03-15",
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "committee_member_names[]": ["Alice Johnson", "Bob Smith"],
            "committee_member_roles[]": ["Coordinator", "Volunteer"],
            "committee_member_departments[]": ["CSE", "ECE"],
            "committee_member_contacts[]": ["alice@example.com", ""],
            "speaker_ids[]": [str(speaker.id)],
            "speaker_topics[]": ["AI Trends"],
            "speaker_durations[]": ["45"],
            "speaker_feedback[]": ["Well received session"],
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)

        report_fields = response.context["report_fields"]

        self.assertIn(
            ("Committee Member 1 - Name", "Alice Johnson"), report_fields
        )
        self.assertIn(
            ("Committee Member 1 - Contact", "alice@example.com"), report_fields
        )
        self.assertIn(
            ("Committee Member 2 - Role", "Volunteer"), report_fields
        )
        self.assertIn(
            ("Speaker Session 1 - Speaker", "Dr. Ada Lovelace"), report_fields
        )
        self.assertIn(("Speaker Session 1 - Topic", "AI Trends"), report_fields)
        self.assertIn(
            ("Speaker Session 1 - Duration (minutes)", "45"), report_fields
        )
        self.assertIn(
            ("Speaker Session 1 - Feedback/Comments", "Well received session"),
            report_fields,
        )

    def test_preview_displays_cdl_support_details_and_report_textboxes(self):
        org_type = OrganizationType.objects.create(name="Department")
        org = Organization.objects.create(name="IQAC", org_type=org_type)
        self.proposal.organization = org
        self.proposal.venue = "Main Hall"
        self.proposal.event_start_date = date(2024, 5, 1)
        self.proposal.event_end_date = date(2024, 5, 2)
        self.proposal.academic_year = "2024-2025"
        self.proposal.save(
            update_fields=[
                "organization",
                "venue",
                "event_start_date",
                "event_end_date",
                "academic_year",
            ]
        )

        support = CDLSupport.objects.create(
            proposal=self.proposal,
            needs_support=True,
            poster_required=True,
            poster_choice=CDLSupport.PosterChoice.CDL_CREATE,
            organization_name="IQAC",
            poster_time="10:00 AM",
            poster_date=date(2024, 5, 1),
            poster_venue="Auditorium",
            resource_person_name="Dr. Jane Doe",
            resource_person_designation="Professor",
            poster_event_title="Innovation Day",
            poster_summary="Poster summary text",
            poster_design_link="http://example.com/poster",
            other_services=["photography", "videography"],
            certificates_required=True,
            certificate_help=True,
            certificate_choice=CDLSupport.CertificateChoice.CDL_CREATE,
            certificate_design_link="http://example.com/certificate",
            blog_content="Blog coverage details.",
        )

        url = reverse("emt:preview_event_report", args=[self.proposal.id])
        data = {
            "department": "IQAC",
            "event_title": "Innovation Day",
            "venue": "Main Hall",
            "event_start_date": "2024-05-01",
            "event_end_date": "2024-05-02",
            "academic_year": "2024-2025",
            "actual_event_type": "Symposium",
            "actual_speakers": "Keynotes and panels",
            "external_contact_details": "",
            "impact_on_stakeholders": "Community outreach",
            "innovations_best_practices": "Hybrid delivery",
            "iqac_feedback": "Encouraged mentoring",
            "beneficiaries_details": "200 students",
            "attendance_notes": "",
            "report_signed_date": "2024-05-05",
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)

        proposal_fields = response.context["proposal_fields"]

        expected_poster_date = date_format(date(2024, 5, 1), "DATE_FORMAT")
        self.assertIn(("Poster Choice", support.get_poster_choice_display()), proposal_fields)
        self.assertIn(("Organization Name", "IQAC"), proposal_fields)
        self.assertIn(("Event Time", "10:00 AM"), proposal_fields)
        self.assertIn(("Event Date", expected_poster_date), proposal_fields)
        self.assertIn(("Event Venue", "Auditorium"), proposal_fields)
        self.assertIn(("Resource Person Name", "Dr. Jane Doe"), proposal_fields)
        self.assertIn(("Resource Person Designation", "Professor"), proposal_fields)
        self.assertIn(("Event Title for Poster", "Innovation Day"), proposal_fields)
        self.assertIn(("Event Summary", "Poster summary text"), proposal_fields)

        design_links = [
            value
            for label, value in proposal_fields
            if label == "Design Link/Reference"
        ]
        self.assertIn("http://example.com/poster", design_links)
        self.assertIn("http://example.com/certificate", design_links)

        services_value = next(
            (value for label, value in proposal_fields if label == "Additional Services"),
            "",
        )
        self.assertEqual(services_value, "Event Photography, Event Videography")
        self.assertIn(("Blog Content", "Blog coverage details."), proposal_fields)
        self.assertIn(
            ("Certificate Choice", support.get_certificate_choice_display()),
            proposal_fields,
        )

        report_dict = {label: value for label, value in response.context["report_fields"]}
        form = response.context["form"]

        expected_signed = date_format(date(2024, 5, 5), "DATE_FORMAT")
        self.assertEqual(
            report_dict.get(form.fields["actual_speakers"].label),
            "Keynotes and panels",
        )
        self.assertEqual(
            report_dict.get(form.fields["impact_on_stakeholders"].label),
            "Community outreach",
        )
        self.assertEqual(
            report_dict.get(form.fields["innovations_best_practices"].label),
            "Hybrid delivery",
        )
        self.assertEqual(
            report_dict.get(form.fields["iqac_feedback"].label),
            "Encouraged mentoring",
        )
        self.assertEqual(
            report_dict.get(form.fields["beneficiaries_details"].label),
            "200 students",
        )
        self.assertEqual(
            report_dict.get(form.fields["external_contact_details"].label),
            "—",
        )
        self.assertEqual(
            report_dict.get(form.fields["attendance_notes"].label),
            "—",
        )
        self.assertEqual(
            report_dict.get(form.fields["report_signed_date"].label),
            expected_signed,
        )


    def test_preview_shows_faculty_incharges(self):
        fac = User.objects.create_user(username="facultya")
        self.proposal.faculty_incharges.add(fac)
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
        self.assertContains(response, "facultya")

    def test_preview_shows_inactive_organization_name(self):
        org_type = OrganizationType.objects.create(name="Department")
        archived_org = Organization.objects.create(
            name="Archived Org", org_type=org_type, is_active=False
        )
        self.proposal.organization = archived_org
        self.proposal.save(update_fields=["organization"])

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
        self.assertContains(response, "Archived Org")

    def test_preview_submission_preserves_multi_value_fields(self):
        faculty_one = User.objects.create_user(username="faculty_one")
        faculty_two = User.objects.create_user(username="faculty_two")

        preview_url = reverse("emt:preview_event_report", args=[self.proposal.id])
        multi_values = [str(faculty_one.id), str(faculty_two.id)]
        data = {
            "actual_event_type": "Seminar",
            "report_signed_date": "2024-01-10",
            "faculty_incharges": multi_values,
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }
        preview_response = self.client.post(preview_url, data)
        self.assertEqual(preview_response.status_code, 200)

        class HiddenInputParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.inputs = []

            def handle_starttag(self, tag, attrs):
                if tag.lower() != "input":
                    return
                attr_dict = dict(attrs)
                if attr_dict.get("type") != "hidden":
                    return
                name = attr_dict.get("name")
                if not name:
                    return
                self.inputs.append((name, attr_dict.get("value", "")))

        parser = HiddenInputParser()
        parser.feed(preview_response.content.decode())
        parser.close()

        final_payload = QueryDict("", mutable=True)
        for name, value in parser.inputs:
            final_payload.appendlist(name, value or "")
        final_payload.appendlist("final_submit", "Submit Report")

        self.assertEqual(final_payload.getlist("faculty_incharges"), multi_values)

        submit_url = reverse("emt:submit_event_report", args=[self.proposal.id])
        captured = {}

        def capture_sync(proposal, report, payload):
            captured["faculty_incharges"] = payload.getlist("faculty_incharges")

        encoded_payload = final_payload.urlencode()

        with patch("emt.views._sync_proposal_from_report", side_effect=capture_sync):
            submit_response = self.client.post(
                submit_url,
                encoded_payload,
                content_type="application/x-www-form-urlencoded",
            )

        self.assertEqual(submit_response.status_code, 302)
        self.assertEqual(captured.get("faculty_incharges"), multi_values)

    def test_proposal_speakers_prefilled(self):
        SpeakerProfile.objects.create(
            proposal=self.proposal,
            full_name="Dr. Xavier",
            designation="Prof",
            affiliation="Uni",
            contact_email="x@example.com",
            contact_number="123",
            detailed_profile="Bio",
        )

        # Render the page to ensure speaker data is serialized
        response = self.client.get(
            reverse("emt:submit_event_report", args=[self.proposal.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Dr. Xavier", response.content.decode())

        # Node script to verify client-side population after section load
        import subprocess
        import tempfile
        from pathlib import Path

        submit_js = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "emt"
            / "js"
            / "submit_event_report.js"
        )
        proposal_data = {
            "proposer": "Alice",
            "faculty_incharges": ["Prof. B"],
            "student_coordinators": "Carl",
            "volunteers": ["Dan"],
            "speakers": [{"full_name": "Dr. Xavier", "organization": "Uni"}],
        }
        existing_speakers = [{"full_name": "Dr. Xavier", "organization": "Uni"}]
        node_script = r"""
const fs = require('fs');
const src = fs.readFileSync('__SUBMIT_JS__', 'utf8');
function extract(name){
  const start = src.indexOf('function ' + name);
  if(start === -1) throw new Error('not found: ' + name);
  let i = src.indexOf('{', start); i++; let depth = 1;
  while(i < src.length && depth > 0){
    if(src[i] === '{') depth++;
    else if(src[i] === '}') depth--;
    i++;
  }
  return src.slice(start, i);
}
const fnPopulateSpeakersFromProposal = extract('populateSpeakersFromProposal');
const fnFillOrganizingCommittee = extract('fillOrganizingCommittee');
const fnFillAttendanceCounts = extract('fillAttendanceCounts');

const handlers = {};
let domReady = false;

const makeNode = () => ({
  value: '',
  innerHTML: '',
  attrs: {},
  dataStore: {},
  addEventListener: () => {},
  querySelector: () => null,
  querySelectorAll: () => [],
});

const speakersDisplay = makeNode();
const formGrid = makeNode();

const orgField = Object.assign(makeNode(), {
  val: function(v){
    if(v === undefined) return this.value || '';
    this.value = v;
    return this;
  },
  text: function(v){
    if(v === undefined) return this.value || '';
    this.value = v;
    return this;
  },
});

const elements = {
  'speakers-display': speakersDisplay,
  'organizing-committee-modern': orgField,
  'attendance-modern': makeNode(),
  'num-participants-modern': makeNode(),
  'total-participants-modern': makeNode(),
  'num-volunteers-modern': makeNode(),
  'num-volunteers-hidden': makeNode(),
  'student-participants-modern': makeNode(),
  'faculty-participants-modern': makeNode(),
  'external-participants-modern': makeNode(),
  'proposal-speakers-json': Object.assign(makeNode(), { textContent: '' }),
};

function wrapNodes(nodes){
  const arr = Array.isArray(nodes) ? nodes : [];
  return {
    __targets: arr,
    length: arr.length,
    val: function(v){
      if(v === undefined){
        const first = arr[0];
        if(!first) return undefined;
        if(typeof first.val === 'function') return first.val();
        return first.value;
      }
      arr.forEach(node => {
        if(typeof node.val === 'function') node.val(v);
        else node.value = v;
      });
      return this;
    },
    text: function(v){
      if(v === undefined){
        const first = arr[0];
        if(!first) return undefined;
        if(typeof first.text === 'function') return first.text();
        if('textContent' in first) return first.textContent;
        return first.value;
      }
      arr.forEach(node => {
        if(typeof node.text === 'function') node.text(v);
        else if('textContent' in node) node.textContent = v;
        else node.value = v;
      });
      return this;
    },
    html: function(v){
      if(v === undefined){
        const first = arr[0];
        return first ? first.innerHTML : undefined;
      }
      arr.forEach(node => { node.innerHTML = v; });
      return this;
    },
    append: function(html){
      arr.forEach(node => { node.innerHTML = (node.innerHTML || '') + html; });
      return this;
    },
    empty: function(){
      arr.forEach(node => { node.innerHTML = ''; });
      return this;
    },
    attr: function(name, v){
      if(v === undefined){
        const first = arr[0];
        return first && first.attrs ? first.attrs[name] : undefined;
      }
      arr.forEach(node => {
        node.attrs = node.attrs || {};
        node.attrs[name] = v;
      });
      return this;
    },
    data: function(name, v){
      if(v === undefined){
        const first = arr[0];
        return first && first.dataStore ? first.dataStore[name] : undefined;
      }
      arr.forEach(node => {
        node.dataStore = node.dataStore || {};
        node.dataStore[name] = v;
      });
      return this;
    },
    prop: function(){ return this; },
    css: function(){ return this; },
    addClass: function(){ return this; },
    removeClass: function(){ return this; },
    add: function(other){
      const combined = [...arr];
      if(other && other.__targets) combined.push(...other.__targets);
      return wrapNodes(combined);
    },
    each: function(cb){
      arr.forEach((node, idx) => cb.call(node, idx, node));
      return this;
    },
    on: function(){ return this; },
    off: function(){ return this; },
    trigger: function(){ return this; },
  };
}

const document = {
  readyState: 'complete',
  getElementById: id => elements[id] || null,
  querySelector: () => null,
  querySelectorAll: () => [],
};

function $(sel){
  if(sel === document){
    const jqDoc = {
      on: (ev, fn) => { (handlers[ev] = handlers[ev] || []).push(fn); return jqDoc; },
      trigger: (ev, data) => { (handlers[ev] || []).forEach(fn => fn({ type: ev }, data)); return jqDoc; },
      off: () => jqDoc,
    };
    return jqDoc;
  }
  if(sel === '.form-grid'){
    return {
      length: 1,
      html: function(content){
        if(content !== undefined){
          formGrid.innerHTML = content;
          setTimeout(() => { domReady = true; }, 0);
          return this;
        }
        return formGrid.innerHTML;
      },
      append: function(html){
        formGrid.innerHTML = (formGrid.innerHTML || '') + html;
        return this;
      },
      empty: function(){ formGrid.innerHTML = ''; return this; },
      addClass: function(){ return this; },
      removeClass: function(){ return this; },
      on: function(){ return this; },
      off: function(){ return this; },
      trigger: function(){ return this; },
    };
  }
  if(typeof sel === 'string'){
    const parts = sel.split(',').map(s => s.trim()).filter(Boolean);
    const nodes = parts.map(part => {
      if(part.startsWith('#')){
        const id = part.slice(1);
        return elements[id];
      }
      return null;
    }).filter(Boolean);
    if(!domReady && nodes.length && sel.startsWith('#')){
      return wrapNodes(nodes);
    }
    if(!domReady) return wrapNodes([]);
    return wrapNodes(nodes);
  }
  return wrapNodes([]);
}

global.$ = $;
global.document = document;

const window = {
  PROPOSAL_DATA: __PROPOSAL_DATA__,
  EXISTING_SPEAKERS: __EXISTING_SPEAKERS__,
  ATTENDANCE_PRESENT: 10,
  ATTENDANCE_ABSENT: 2,
  ATTENDANCE_VOLUNTEERS: 3,
  ATTENDANCE_COUNTS: { present: 10, absent: 2, volunteers: 3, total: 10, students: 6, faculty: 3, external: 1 },
  location: { pathname: '/suite/reports/preview/' },
};
global.window = window;

global.renderEditableSpeakerCard = (speaker = {}, index = 0) => {
  const name = speaker.full_name || speaker.name || speaker.title || `Speaker ${index + 1}`;
  const organization = speaker.organization || speaker.affiliation || '';
  const id = speaker.id || speaker.pk || index + 1;
  return `<div class="speaker-card" data-speaker-id="${id}"><div class="speaker-name">${name}</div><div class="speaker-org">${organization}</div></div>`;
};
global.getNoSpeakersMessageHtml = () => '<div class="no-speakers-message">No speakers selected</div>';
global.setupSpeakerCardEditors = () => {};

eval(fnPopulateSpeakersFromProposal);
eval(fnFillOrganizingCommittee);
eval(fnFillAttendanceCounts);

domReady = true;
populateSpeakersFromProposal();
fillOrganizingCommittee();
fillAttendanceCounts();

setTimeout(() => {
  console.log(JSON.stringify({
    display: speakersDisplay.innerHTML,
    organizing: orgField.value,
    total: elements['num-participants-modern'].value,
    volunteers: elements['num-volunteers-modern'].value,
    hiddenVolunteers: elements['num-volunteers-hidden'].value,
    students: elements['student-participants-modern'].value,
    faculty: elements['faculty-participants-modern'].value,
    external: elements['external-participants-modern'].value,
    summary: elements['attendance-modern'].value,
  }));
}, 120);
"""
        node_script = (
            node_script.replace("__SUBMIT_JS__", str(submit_js))
            .replace("__PROPOSAL_DATA__", json.dumps(proposal_data))
            .replace("__EXISTING_SPEAKERS__", json.dumps(existing_speakers))
        )
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "run.js"
            script_path.write_text(node_script)
            result = subprocess.run(
                ["node", str(script_path)], capture_output=True, text=True
            )
        data = json.loads(result.stdout.strip())
        self.assertIn("Dr. Xavier", data["display"])
        self.assertIn("Proposer: Alice", data["organizing"])
        self.assertEqual("10", str(data["total"]))
        self.assertEqual("3", str(data["volunteers"]))
        self.assertEqual("3", str(data["hiddenVolunteers"]))
        self.assertEqual("6", str(data["students"]))
        self.assertEqual("3", str(data["faculty"]))
        self.assertEqual("1", str(data["external"]))
        self.assertIn("Present: 10", data["summary"])
        self.assertIn("Absent: 2", data["summary"])
        self.assertIn("Volunteers: 3", data["summary"])
