from datetime import date
import json
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in

from core.signals import create_or_update_user_profile, assign_role_on_login

from emt.models import (
    EventProposal,
    EventActivity,
    EventReport,
    AttendanceRow,
    SpeakerProfile,
)
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
 if(sel==='#num-participants-modern' || sel==='#total-participants-modern') return participantsEl;
 if(sel==='#autosave-indicator') return indicatorEl;
}
const attendanceEl={attrs:{},dataStore:{},length:1,
  attr:function(n,v){if(v===undefined)return this.attrs[n];this.attrs[n]=v;return this;},
  data:function(n,v){if(v===undefined)return this.dataStore[n];this.dataStore[n]=v;return this;},
  prop:function(){return this;},
  css:function(){return this;}
};
const participantsEl={attrs:{},dataStore:{},length:1,
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
console.log(JSON.stringify({att: attendanceEl.attrs['href'], part: participantsEl.attrs['href']}));
'''
        node_script = node_script.replace('__SUBMIT_JS__', str(submit_js)).replace('__REPORT_ID__', str(report_id))
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "run.js"
            script_path.write_text(node_script)
            result = subprocess.run(["node", str(script_path)], capture_output=True, text=True)
        out = json.loads(result.stdout.strip())
        self.assertEqual(out["att"], attendance_url)
        self.assertEqual(out["part"], attendance_url)

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
        import tempfile
        import subprocess
        from pathlib import Path

        submit_js = Path(__file__).resolve().parents[1] / "static" / "emt" / "js" / "submit_event_report.js"
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
  if(start === -1) throw new Error('not found: '+name);
  let i = src.indexOf('{', start); i++; let depth = 1;
  while(i < src.length && depth > 0){
    if(src[i] === '{') depth++;
    else if(src[i] === '}') depth--;
    i++;
  }
  return src.slice(start, i);
}
const loadSectionContent = extract('loadSectionContent');
const populateSpeakersFromProposal = extract('populateSpeakersFromProposal');
const fillOrganizingCommittee = extract('fillOrganizingCommittee');
const fillAttendanceCounts = extract('fillAttendanceCounts');

let domReady = false;
const speakersDisplay = {innerHTML: ''};
const orgEl = {value:'', length:1, val:function(v){ if(v===undefined) return this.value; this.value=v; return this; }, text:function(v){ if(v===undefined) return this.value; this.value=v; return this; }};
const makeField = () => ({value:'', length:1, val:function(v){ if(v===undefined) return this.value; this.value=v; return this; }, text:function(v){ if(v===undefined) return this.value; this.value=v; return this; }});

const elements = {
  'speakers-display': speakersDisplay,
  'attendance-modern': makeField(),
  'num-participants-modern': makeField(),
  'total-participants-modern': makeField(),
  'num-volunteers-modern': makeField(),
  'num-volunteers-hidden': makeField(),
  'student-participants-modern': makeField(),
  'faculty-participants-modern': makeField(),
  'external-participants-modern': makeField(),
};

function $(sel){
  if(sel === '.form-grid') return {html:function(content){ setTimeout(()=>{domReady=true;},0); return this; }};
  if(!domReady) return {length:0, val:function(){}};
  if(sel === '#organizing-committee-modern') return orgEl;
  return {length:0, val:function(){}};
}

global.$ = $;
global.document = {
  readyState: 'complete',
  getElementById: id => {
    if(id === 'speakers-display') return domReady ? elements[id] : null;
    return elements[id] || null;
  }
};
global.window = {
  PROPOSAL_DATA: __PROPOSAL_DATA__,
  EXISTING_SPEAKERS: __EXISTING_SPEAKERS__,
  ATTENDANCE_PRESENT: 10,
  ATTENDANCE_ABSENT: 2,
  ATTENDANCE_VOLUNTEERS: 3,
  ATTENDANCE_COUNTS: { present: 10, absent: 2, volunteers: 3, total: 10, students: 6, faculty: 3, external: 1 }
};

eval(populateSpeakersFromProposal);
eval(fillOrganizingCommittee);
eval(fillAttendanceCounts);
eval(loadSectionContent);

loadSectionContent('participants-information');

setTimeout(()=>{
  console.log(JSON.stringify({
    display: speakersDisplay.innerHTML,
    organizing: orgEl.value,
    total: elements['num-participants-modern'].value,
    volunteers: elements['num-volunteers-modern'].value,
    hiddenVolunteers: elements['num-volunteers-hidden'].value,
    students: elements['student-participants-modern'].value,
    faculty: elements['faculty-participants-modern'].value,
    external: elements['external-participants-modern'].value,
    summary: elements['attendance-modern'].value
  }));
}, 20);
"""
        node_script = (
            node_script.replace("__SUBMIT_JS__", str(submit_js))
            .replace("__PROPOSAL_DATA__", json.dumps(proposal_data))
            .replace("__EXISTING_SPEAKERS__", json.dumps(existing_speakers))
        )
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "run.js"
            script_path.write_text(node_script)
            result = subprocess.run(["node", str(script_path)], capture_output=True, text=True)
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

