# Submit Proposal & Event Report Field Inventory

This document enumerates every field shown (or autosaved behind the scenes) on the Event Proposal submission workflow and the Event Report generation workflow, including their section grouping and any dynamic behaviors.

## Submit Proposal form (`/emt/submit/`)

### Persisted but hidden draft sections
- **Need analysis** – `<textarea id="id_need_analysis" name="need_analysis">` stores the rationale text even though the interactive editor lives in the "Why This Event?" section.【F:emt/templates/emt/submit_proposal.html†L109-L114】
- **Objectives** – `<textarea id="id_objectives" name="objectives">` keeps the objective list.【F:emt/templates/emt/submit_proposal.html†L109-L114】
- **Expected learning outcomes** – `<textarea id="id_learning_outcomes" name="outcomes">` mirrors the outcomes editor.【F:emt/templates/emt/submit_proposal.html†L109-L114】
- **Tentative flow** – hidden `<textarea name="flow">` captures the serialized schedule from the Schedule section.【F:emt/templates/emt/submit_proposal.html†L109-L115】

### Section 1: Basic Info
- **Type of Organisation** – TomSelect dropdown seeded from Django field `organization_type`; choosing a type injects an additional organization selector tied to the chosen label (Department/Club/Association/Center/Cell).【F:emt/templates/emt/submit_proposal.html†L124-L133】【F:emt/static/emt/js/proposal_dashboard.js†L1557-L1645】
- **Organization Name** – dynamically rendered select (`#org-modern-select`) filtered by organization type; syncs to hidden Django `organization` field.【F:emt/static/emt/js/proposal_dashboard.js†L1646-L1707】
- **Committees & Collaborations** – multi-select for internal/external partners, mirrored into the Django `committees_collaborations` text plus `committees_collaborations_ids` hidden helper.【F:emt/templates/emt/submit_proposal.html†L138-L144】【F:emt/static/emt/js/proposal_dashboard.js†L690-L780】
- **Event Title** – text input for the proposal headline.【F:emt/templates/emt/submit_proposal.html†L151-L156】
- **Target Audience** – modal-driven picker storing human-readable text and hidden `target_audience_class_ids` selections.【F:emt/templates/emt/submit_proposal.html†L157-L162】
- **Event Focus Type** – optional focus descriptor.【F:emt/templates/emt/submit_proposal.html†L165-L170】
- **Location** – venue string for the event.【F:emt/templates/emt/submit_proposal.html†L171-L175】
- **Start Date / End Date** – required date pickers for the schedule.【F:emt/templates/emt/submit_proposal.html†L183-L194】
- **Academic Year** – read-only display plus hidden `<input name="academic_year">` kept in sync automatically.【F:emt/templates/emt/submit_proposal.html†L196-L203】【F:emt/static/emt/js/proposal_dashboard.js†L480-L503】
- **POS & PSO Management** – short textarea for programme outcome tags.【F:emt/templates/emt/submit_proposal.html†L205-L210】
- **Aligned SDG Goals** – searchable input tied to an SDG modal and underlying checkbox set from the Django form.【F:emt/templates/emt/submit_proposal.html†L213-L220】【F:emt/static/emt/js/proposal_dashboard.js†L1508-L1554】
- **Number of Activities** – numeric input driving dynamic activity rows (max 50) and syncing back to Django `num_activities`.【F:emt/templates/emt/submit_proposal.html†L223-L238】【F:emt/static/emt/js/proposal_dashboard.js†L520-L613】
- **Student Coordinators** – TomSelect multi-select with rendered chips and autosave support, synced to hidden Django field.【F:emt/templates/emt/submit_proposal.html†L223-L236】【F:emt/static/emt/js/proposal_dashboard.js†L300-L377】
- **Planned Activity Rows** – for each activity count, renders paired fields (`activity_name_n`, `activity_date_n`) with remove buttons and numbering enforcement.【F:emt/static/emt/js/proposal_dashboard.js†L563-L587】
- **Faculty Incharges** – multi-select fed from the faculty API and synced to the Django `faculty_incharges` field.【F:emt/templates/emt/submit_proposal.html†L240-L246】【F:emt/static/emt/js/proposal_dashboard.js†L617-L688】

### Section 2: Why This Event?
- **Need Analysis** – required textarea (`#need-analysis-modern`) with AI assistance button.【F:emt/static/emt/js/proposal_dashboard.js†L1786-L1799】
- **Objectives** – required textarea (`#objectives-modern`) for measurable goals with AI helper.【F:emt/static/emt/js/proposal_dashboard.js†L1801-L1807】
- **Expected Learning Outcomes** – required textarea describing participant takeaways with AI helper.【F:emt/static/emt/js/proposal_dashboard.js†L1810-L1816】

### Section 3: Schedule
- **Event timeline** – dynamic schedule builder storing entries as `datetime-local` + activity text rows; persisted into hidden `schedule-modern` textarea.【F:emt/static/emt/js/proposal_dashboard.js†L1886-L1970】

### Section 4: Speakers
- **Speaker cards** – each speaker form collects: Full Name, Designation, Affiliation, Email, Contact Number, LinkedIn Profile URL, Photo upload, and required Brief Profile/Bio.【F:emt/static/emt/js/proposal_dashboard.js†L2031-L2091】

### Section 5: Expenses
- **Expense rows** – repeatable blocks for Sl. No., Particulars (required), and Amount (required) with autosave and empty-state handling.【F:emt/static/emt/js/proposal_dashboard.js†L2291-L2383】

### Section 6: Income
- **Income rows** – repeatable blocks for Sl. No., Particulars (required), No. of Participants, Rate, auto-calculated Amount (required) plus remove controls.【F:emt/static/emt/js/proposal_dashboard.js†L2386-L2452】

### Section 7: CDL Support (poster/certificate/content assistance)
- **Request CDL Support** – master checkbox `needs_support` that reveals the service cards.【F:emt/templates/emt/cdl_support.html†L25-L44】
- **Poster Support** – toggle `poster_required` plus fields for Poster Choice, Organization Name, Event Time, Event Date, Event Venue, Resource Person Name & Designation, Poster Event Title, Event Summary, and Design Link.【F:emt/templates/emt/cdl_support.html†L46-L110】
- **Certificate Support** – toggle `certificates_required`; optional `certificate_help` reveals Certificate Choice and Design Link fields.【F:emt/templates/emt/cdl_support.html†L118-L156】
- **Other CDL Services** – textarea `other_services` for additional requests.【F:emt/templates/emt/cdl_support.html†L160-L174】
- **Blog Content** – textarea `blog_content` limited to roughly 150 words.【F:emt/templates/emt/cdl_support.html†L177-L191】

### Additional Django-backed fields
The Django `EventProposalForm` also carries finance fields (`fest_fee_*`, `fest_sponsorship_amount`, `conf_fee_*`, `conf_sponsorship_amount`) and raw `student_coordinators` text; these remain in the hidden `#django-forms` container so that legacy data still posts back correctly.【F:emt/forms.py†L69-L121】【F:emt/templates/emt/submit_proposal.html†L262-L284】

## Event Report generation workflow

### Event Report form (`/emt/report/submit/<proposal_id>/`)

#### Hidden persisted blocks
- **Event summary / outcomes / analysis** – hidden textareas mirroring the large editors across sections so the Django form receives values on submit.【F:emt/templates/emt/submit_event_report.html†L95-L100】
- **Attendance notes** – hidden `<textarea id="attendance-data" name="attendance_notes">` used to pass CSV upload remarks.【F:emt/templates/emt/submit_event_report.html†L95-L100】

#### Section 1: Event Information
- Department, Venue/Location, Event Title, Venue (duplicate detail), Start & End Dates, Academic Year (read-only + hidden), Event Type (read-only), Actual Event Location, Blog Link, Attendance summary (with hidden `num_participants`), Student Volunteer count (read-only + hidden), Student/Faculty/External participant counts, Number of Activities, and dynamic activity rows (`activity_name_n`, `activity_date_n`).【F:emt/templates/emt/submit_event_report.html†L105-L260】
- Autosave script renders identical controls when switching sections via `getEventInformationContent`, ensuring consistent labels and autosave mapping.【F:emt/static/emt/js/submit_event_report.js†L960-L1033】

#### Section 2: Participants Information
- Total Participants (required), Student Participants, Faculty Participants, External Participants, Organizing Committee Details (required textarea), and a read-only Speakers reference card drawn from the proposal.【F:emt/static/emt/js/submit_event_report.js†L1036-L1107】

#### Section 3: Summary of Overall Event
- Summary of Overall Event (required, 500 word minimum with AI helper), Key Achievements, Notable Moments plus Save & Continue button.【F:emt/static/emt/js/submit_event_report.js†L1110-L1157】

#### Section 4: Outcomes of the Event
- Learning Outcomes Achieved (required), Participant Feedback (required), Measurable Outcomes (required), Short-term & Long-term Impact assessment (required).【F:emt/static/emt/js/submit_event_report.js†L1162-L1217】

#### Section 5: Analysis
- Achievement of Planned Objectives (required), Strengths and Successes (required), Challenges & Areas for Improvement (required), Overall Effectiveness Analysis (required), Lessons Learned & Future Insights (required, with word counter).【F:emt/static/emt/js/submit_event_report.js†L1226-L1305】

#### Section 6: Relevance of the Event
- PO & PSO Management textarea (required with AI button), Graduate Attributes summary container with "Open GA Editor" control, Contemporary Requirements textarea (required with AI helper), SDG Implementation textarea (required) plus "Select SDG Goals" modal launcher.【F:emt/static/emt/js/submit_event_report.js†L1310-L1383】【F:emt/templates/emt/submit_event_report.html†L300-L347】
- Modal pickers for Graduate Attributes/PO-PSO (`#outcomeModal`) and SDG goals (`#sdgModal`) persist the structured selections into Django hidden fields.【F:emt/templates/emt/submit_event_report.html†L262-L347】

#### Autosave & attachments
- `report_autosave.js` binds every named input/textarea/select for autosave, ensuring even hidden Django-only fields (e.g., `iqac_feedback`, `beneficiaries_details`) stay in sync when the backend exposes them.【F:emt/static/emt/js/report_autosave.js†L1-L123】
- The Django `EventReportForm` still includes additional fields (`actual_speakers`, `external_contact_details`, `impact_on_stakeholders`, `innovations_best_practices`, `iqac_feedback`, `report_signed_date`, `beneficiaries_details`, etc.) and an `EventReportAttachmentForm` (`file`, `caption`) that render inside the hidden `#django-forms` block until bespoke UI is added.【F:emt/forms.py†L348-L415】

### AI report progress page (`/emt/report/progress/<proposal_id>/`)
The progress screen displays live-updating placeholders for:
- Event Title, Date & Time, Venue, Academic Year, Focus/Objective, Target Audience, Organization, and No. of Participants in an info table.【F:emt/templates/emt/ai_report_progress.html†L21-L31】
- Narrative sections for Event Summary, Outcomes, Feedback & Suggestions, Recommendations, and Attachments with streaming AI text fill and associated Edit/Submit buttons.【F:emt/templates/emt/ai_report_progress.html†L33-L52】【F:emt/templates/emt/ai_report_progress.html†L58-L160】

### AI report edit prompt (`/emt/report/edit/<proposal_id>/`)
- **Instructions for regeneration** – textarea `instructions` describing how the AI should revise the draft.【F:emt/templates/emt/ai_report_edit.html†L11-L16】
- **Manual field overrides** – textarea `manual_fields` for direct "Field: Value" edits prior to regeneration.【F:emt/templates/emt/ai_report_edit.html†L17-L21】
- Submit button triggers regeneration; Cancel returns to the progress view.【F:emt/templates/emt/ai_report_edit.html†L19-L22】

