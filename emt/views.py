import copy
import csv
import json
import logging
import os
import re
from datetime import datetime, timedelta
from operator import attrgetter
from types import SimpleNamespace
from urllib.parse import urlparse

import google.generativeai as genai
import pdfkit
import requests
from bs4 import BeautifulSoup
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator, URLValidator
from django.db.models import Q, Sum
from django.forms import modelformset_factory
from django.http import (
    HttpResponse,
    HttpResponseNotAllowed,
    JsonResponse,
    StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.formats import date_format
from django.utils.timezone import now
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_http_methods, require_POST

from core.models import (SDG_GOALS, Class, Organization,
                         OrganizationMembership, OrganizationType,
                         RoleAssignment, Report, SDGGoal)
from core.models import (
    SDG_GOALS,
    Class,
    Organization,
    OrganizationMembership,
    OrganizationType,
    Report,
    SDGGoal,
    ActivityLog,
)
from core.utils_email import send_notification, resolve_role_emails
from emt.utils import (ATTENDANCE_HEADERS,
                       auto_approve_non_optional_duplicates,
                       build_approval_chain,
                       get_downstream_optional_candidates,
                       parse_attendance_csv, skip_all_downstream_optionals,
                       unlock_optionals_after)
from suite.ai_client import AIError, chat
from transcript.models import get_active_academic_year

from .forms import (NAME_PATTERN, CDLSupportForm, EventProposalForm,
                    EventReportAttachmentForm, EventReportForm,
                    ExpectedOutcomesForm, ExpenseDetailForm, NeedAnalysisForm,
                    ObjectivesForm, SpeakerProfileForm, TentativeFlowForm)
from .models import (ApprovalStep, AttendanceRow, EventActivity,
                     EventExpectedOutcomes, EventNeedAnalysis, EventObjectives,
                     EventProposal, EventReport, EventReportAttachment,
                     ExpenseDetail, IncomeDetail, MediaRequest, SpeakerProfile,
                     Student, TentativeFlow)

FACULTY_ROLE = ApprovalStep.Role.FACULTY.value
DEAN_ROLE = ApprovalStep.Role.DEAN.value
ACADEMIC_COORDINATOR_ROLE = "academic_coordinator"


logger = logging.getLogger(__name__)
NAME_RE = re.compile(NAME_PATTERN)
MAX_ACTIVE_DRAFTS = 5

# Configure Gemini API key from environment variable(s)
# Prefer `GEMINI_API_KEY`; fall back to `GOOGLE_API_KEY`
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)


# ────────────────────────────────────────────────────────────────
#  Review Center (Single Page Workflow)
# ────────────────────────────────────────────────────────────────

def _build_report_initial_data(report: EventReport) -> dict:
    """Builds the initial_data structure used by iqac_report_preview.html from persisted models.
    Keeps preview and PDF export consistent.
    """
    proposal = report.proposal

    def _text(v):
        if v is None:
            return ""
        return str(v)

    def _date(d):
        try:
            return date_format(d, "d M Y") if d else ""
        except Exception:
            return str(d) if d else ""

    def _listify(v):
        if not v:
            return []
        if isinstance(v, (list, tuple, set)):
            return [str(x).strip() for x in v if str(x).strip()]
        import re as _re
        raw = str(v)
        parts = _re.split(r"[\r\n;,]+", raw)
        return [_re.sub(r"^[\-*•\u2022]+\s*", "", p.strip()) for p in parts if p and p.strip()]

    start = _date(proposal.event_start_date)
    end = _date(proposal.event_end_date)
    if start and end:
        event_schedule = start if start == end else f"{start} – {end}"
    else:
        event_schedule = start or end or _text(getattr(proposal, "event_datetime", ""))

    return {
        "event": {
            "title": _text(proposal.event_title),
            "department": _text(getattr(proposal.organization, "name", "")),
            "location": _text(report.location),
            "no_of_activities": _text(proposal.num_activities or ""),
            "date": event_schedule,
            "venue": _text(proposal.venue),
            "academic_year": _text(proposal.academic_year),
            "event_type_focus": _text(proposal.event_focus_type),
            "blog_link": _text(report.blog_link),
        },
        "participants": {
            "target_audience": _text(proposal.target_audience),
            "external_agencies_speakers": _text(report.actual_speakers),
            "external_contacts": _text(report.external_contact_details),
            "organising_committee": {
                "event_coordinators": _listify(report.organizing_committee),
                "student_volunteers_count": _text(report.num_student_volunteers),
            },
            "attendees_count": _text(report.num_participants),
        },
        "narrative": {
            "summary_overall_event": _text(report.summary),
            "social_relevance": _listify(report.impact_assessment),
            "outcomes": _listify(report.outcomes),
        },
        "analysis": {
            "impact_attendees": _text(report.impact_on_stakeholders),
            "impact_schools": _text(report.analysis),
            "impact_volunteers": _text(report.lessons_learned),
        },
        "mapping": {
            "pos_psos": _text(report.pos_pso_mapping or proposal.pos_pso),
            "graduate_attributes_or_needs": _text(report.needs_grad_attr_mapping),
            "contemporary_requirements": _text(report.contemporary_requirements),
            "value_systems": _text(report.sdg_value_systems_mapping),
            "sdg_goal_numbers": [f"SDG {g.id}: {g.name}" for g in proposal.sdg_goals.all().order_by("id")],
            "courses": [],
        },
        "metrics": {"naac_tags": []},
        "iqac": {
            "iqac_suggestions": _listify(report.iqac_feedback),
            "iqac_review_date": _date(report.report_signed_date),
            "sign_head_coordinator": _text(
                proposal.submitted_by.get_full_name() or proposal.submitted_by.username
            ) if proposal.submitted_by_id else "",
            "sign_faculty_coordinator": ", ".join([
                u.get_full_name() or u.username for u in proposal.faculty_incharges.all().order_by("id")
            ]),
            "sign_iqac": "",
        },
        "attachments": {"checklist": {}},
        "annexures": {
            "photos": [],
            "brochure_pages": [],
            "communication": {"subject": "", "date": "", "volunteers": []},
            "worksheets": [],
            "evaluation_sheet": None,
            "feedback_form": None,
        },
    }

def _user_role_stage(request):
    """Derive the review stage for the current user.
    Returns one of EventReport.ReviewStage values.
    """
    # Default to USER
    stage = EventReport.ReviewStage.USER
    roles_lower = [
        (ra.role.name.lower() if ra.role else "") for ra in getattr(request.user, "role_assignments", []).all()
    ] if hasattr(request.user, "role_assignments") else []
    prof_role = getattr(getattr(request.user, "profile", None), "role", "")
    if prof_role:
        roles_lower.append(prof_role.lower())
    role_blob = " ".join(roles_lower)
    if "hod" in role_blob or "head" in role_blob:
        stage = EventReport.ReviewStage.HOD
    if "iqac" in role_blob and ("university" in role_blob or "coord" in role_blob or "admin" in role_blob):
        stage = EventReport.ReviewStage.UIQAC
    elif "iqac" in role_blob:
        stage = EventReport.ReviewStage.DIQAC
    return stage


def _is_admin_override(user) -> bool:
    """Return True if the user should be treated as an admin override.
    Conditions:
    - is_superuser or is_staff
    - OR any assigned role/profile role contains the word 'admin' (case-insensitive)
    """
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return True
    roles_lower = []
    try:
        if hasattr(user, "role_assignments"):
            roles_lower.extend([
                (ra.role.name.lower() if ra.role else "")
                for ra in user.role_assignments.all()
            ])
        prof_role = getattr(getattr(user, "profile", None), "role", "")
        if prof_role:
            roles_lower.append(prof_role.lower())
    except Exception:
        pass
    blob = " ".join(roles_lower)
    return "admin" in blob


def _reports_for_user(request):
    stage = _user_role_stage(request)
    user = request.user
    qs = EventReport.objects.select_related("proposal", "proposal__organization", "proposal__submitted_by")
    if stage == EventReport.ReviewStage.USER:
        return qs.filter(proposal__submitted_by=user)
    if stage == EventReport.ReviewStage.DIQAC:
        # Department IQAC: restrict to user's organizations
        org_ids = list(user.role_assignments.exclude(organization__isnull=True).values_list("organization_id", flat=True)) if hasattr(user, "role_assignments") else []
        return qs.filter(proposal__organization_id__in=org_ids).exclude(review_stage=EventReport.ReviewStage.FINALIZED)
    if stage == EventReport.ReviewStage.HOD:
        org_ids = list(user.role_assignments.exclude(organization__isnull=True).values_list("organization_id", flat=True)) if hasattr(user, "role_assignments") else []
        return qs.filter(proposal__organization_id__in=org_ids).exclude(review_stage=EventReport.ReviewStage.FINALIZED)
    if stage == EventReport.ReviewStage.UIQAC:
        # University IQAC: see all non-finalized
        return qs.exclude(review_stage=EventReport.ReviewStage.FINALIZED)
    return qs.none()


@login_required
def review_center(request):
    stage = _user_role_stage(request)
    admin_override = _is_admin_override(request.user)
    # Gate access: submitters (USER stage) should not access Review Center unless admin override
    if not admin_override and stage == EventReport.ReviewStage.USER:
        return HttpResponse(status=403)
    if admin_override:
        reports = EventReport.objects.select_related("proposal", "proposal__organization", "proposal__submitted_by").exclude(review_stage=EventReport.ReviewStage.FINALIZED).order_by("-updated_at")
        stage_label = "Admin"
    else:
        reports = _reports_for_user(request).order_by("-updated_at")
        stage_label = stage
    # Master/Detail: if a report_id is requested via XHR, return compact JSON for detail pane
    report_id = request.GET.get("report_id")
    if report_id and request.headers.get("X-Requested-With"):
        r = get_object_or_404(reports, id=report_id)
        # Determine if the user can decide on this report, mirroring review_action
        if _is_admin_override(request.user):
            can_decide = r.review_stage != EventReport.ReviewStage.FINALIZED
        else:
            if stage == EventReport.ReviewStage.DIQAC:
                can_decide = r.review_stage in [EventReport.ReviewStage.USER, EventReport.ReviewStage.DIQAC]
            elif stage == EventReport.ReviewStage.HOD:
                can_decide = r.review_stage in [EventReport.ReviewStage.DIQAC, EventReport.ReviewStage.HOD]
            elif stage == EventReport.ReviewStage.UIQAC:
                can_decide = r.review_stage in [EventReport.ReviewStage.HOD, EventReport.ReviewStage.UIQAC]
            else:
                can_decide = False
        data = {
            "id": r.id,
            "title": r.proposal.event_title if r.proposal else "",
            "org": getattr(getattr(r.proposal, "organization", None), "name", ""),
            "submitted_by": getattr(getattr(r.proposal, "submitted_by", None), "get_full_name", lambda: "")() or getattr(getattr(r.proposal, "submitted_by", None), "username", ""),
            "stage_display": r.get_review_stage_display(),
            "event_dates": f"{getattr(r.proposal, 'event_start_date', '')} — {getattr(r.proposal, 'event_end_date', '')}",
            "event_type": r.actual_event_type,
            "participants": r.num_participants,
            "summary": r.summary,
            "can_decide": can_decide,
        }
        return HttpResponse(json.dumps(data), content_type="application/json")
    context = {
        "stage": stage,
        "stage_label": stage_label,
        "reports": reports,
    }
    return render(request, "emt/review_center.html", context)


@login_required
@require_POST
def review_action(request):
    """Approve/Reject an EventReport with mandatory feedback and stage transitions."""
    report_id = request.POST.get("report_id")
    action = request.POST.get("action")  # approve|reject
    feedback = (request.POST.get("feedback") or "").strip()
    if not report_id or action not in {"approve", "reject"}:
        return JsonResponse({"ok": False, "error": "Invalid request"}, status=400)
    if not feedback:
        return JsonResponse({"ok": False, "error": "Feedback is required"}, status=400)

    report = get_object_or_404(EventReport, id=report_id)
    stage = _user_role_stage(request)

    # Determine permissions and transitions
    allowed = False
    # Admin override: treat staff/superuser and role 'admin' users as admins (unless finalized)
    if _is_admin_override(request.user):
        if report.review_stage == EventReport.ReviewStage.FINALIZED:
            return JsonResponse({"ok": False, "error": "Finalized reports cannot be modified"}, status=403)
        allowed = True
        # Compressed transitions: USER/DIQAC -> HOD, HOD -> UIQAC, UIQAC -> FINALIZED
        if report.review_stage in [EventReport.ReviewStage.USER, EventReport.ReviewStage.DIQAC]:
            next_on_approve = EventReport.ReviewStage.HOD
        elif report.review_stage == EventReport.ReviewStage.HOD:
            next_on_approve = EventReport.ReviewStage.UIQAC
        elif report.review_stage == EventReport.ReviewStage.UIQAC:
            next_on_approve = EventReport.ReviewStage.FINALIZED
        else:
            next_on_approve = report.review_stage
        next_on_reject = EventReport.ReviewStage.USER
    else:
        # Role-based path
        if stage == EventReport.ReviewStage.DIQAC and report.review_stage in [EventReport.ReviewStage.USER, EventReport.ReviewStage.DIQAC]:
            allowed = True
            next_on_approve = EventReport.ReviewStage.HOD
            next_on_reject = EventReport.ReviewStage.USER
        elif stage == EventReport.ReviewStage.HOD and report.review_stage in [EventReport.ReviewStage.DIQAC, EventReport.ReviewStage.HOD]:
            allowed = True
            next_on_approve = EventReport.ReviewStage.UIQAC
            next_on_reject = EventReport.ReviewStage.USER
        elif stage == EventReport.ReviewStage.UIQAC and report.review_stage in [EventReport.ReviewStage.HOD, EventReport.ReviewStage.UIQAC]:
            allowed = True
            next_on_approve = EventReport.ReviewStage.FINALIZED
            next_on_reject = EventReport.ReviewStage.USER
        else:
            allowed = False

    if not allowed:
        return JsonResponse({"ok": False, "error": "Not permitted for this stage"}, status=403)

    report.session_feedback = feedback
    # Build a human readable stage mapping for logs / notifications
    stage_label = {
        EventReport.ReviewStage.DIQAC: "Department IQAC",
        EventReport.ReviewStage.HOD: "Head of Department",
        EventReport.ReviewStage.UIQAC: "University IQAC",
        EventReport.ReviewStage.FINALIZED: "Finalized",
        EventReport.ReviewStage.USER: "Submitter",
    }

    if action == "approve":
        report.iqac_feedback = (
            (report.iqac_feedback + "\n\n") if report.iqac_feedback else ""
        ) + feedback
        report.review_stage = next_on_approve
        action_desc = f"Approved and moved to {stage_label.get(next_on_approve, next_on_approve)}"
        log_action = "report_approved"
    else:  # reject
        report.iqac_feedback = (
            (report.iqac_feedback + "\n\n") if report.iqac_feedback else ""
        ) + f"REJECTED: {feedback}"
        report.review_stage = next_on_reject
        action_desc = "Rejected and sent back to submitter"
        log_action = "report_rejected"

    report.save(
        update_fields=[
            "session_feedback",
            "iqac_feedback",
            "review_stage",
            "updated_at",
        ]
    )

    # Activity log for auditing
    try:
        ActivityLog.objects.create(
            user=request.user,
            action=log_action,
            description=f"{action_desc}: {report.proposal.event_title}",
            metadata={
                "report_id": report.id,
                "proposal_id": report.proposal_id,
                "new_stage": report.review_stage,
                "action": action,
            },
        )
    except Exception:  # pragma: no cover
        logger.exception("Failed to create ActivityLog for review action")

    # Lightweight notification strategy: mutate proposal status for submitter visibility on reject
    # Only change proposal status on final rejection back to user; do not override existing status otherwise.
    proposal = report.proposal
    if action == "reject":
        # Provide a status change to surface in notifications CP if model uses status field.
        try:
            if hasattr(proposal, "status"):
                # Set to a generic 'UNDER_REVIEW' -> 'SUBMITTED' cycle or 'REJECTED' if defined
                rejected_value = None
                if hasattr(proposal.__class__, "Status"):
                    for choice, _ in proposal.__class__.Status.choices:  # type: ignore
                        if choice.lower() == "rejected":
                            rejected_value = choice
                            break
                if rejected_value:
                    proposal.status = rejected_value
                    proposal.save(update_fields=["status", "updated_at"]) if hasattr(proposal, "updated_at") else proposal.save(update_fields=["status"])
        except Exception:  # pragma: no cover
            logger.exception("Failed to update proposal status on rejection")

    # Email notifications
    try:
        subj_prefix = f"[IQAC Review] {report.proposal.event_title}"
        if action == "approve":
            if report.review_stage == EventReport.ReviewStage.HOD:
                # Notify HOD for next action
                emails = resolve_role_emails(report.proposal.organization, "hod")
                body = f"The report '{report.proposal.event_title}' is ready for your review.\n\nFeedback: {feedback}"
                send_notification(f"{subj_prefix} → HOD review", body, emails)
            elif report.review_stage == EventReport.ReviewStage.UIQAC:
                emails = resolve_role_emails(report.proposal.organization, "iqac")
                body = f"The report '{report.proposal.event_title}' advanced to University IQAC stage.\n\nFeedback so far: {feedback}"
                send_notification(f"{subj_prefix} → UIQAC review", body, emails)
            elif report.review_stage == EventReport.ReviewStage.FINALIZED:
                # Notify submitter
                submitter_email = getattr(report.proposal.submitted_by, "email", "")
                if submitter_email:
                    body = f"Your report '{report.proposal.event_title}' has been finalized.\n\nReviewer note: {feedback}"
                    send_notification(f"{subj_prefix} finalized", body, submitter_email)
        else:  # reject
            submitter_email = getattr(report.proposal.submitted_by, "email", "")
            if submitter_email:
                body = f"Your report '{report.proposal.event_title}' was sent back with feedback:\n\n{feedback}"
                send_notification(f"{subj_prefix} – Changes Requested", body, submitter_email)
    except Exception:
        logger.exception("Failed to send review action notifications")

    return JsonResponse(
        {
            "ok": True,
            "stage": report.review_stage,
            "message": action_desc,
        }
    )


@login_required
@require_POST
def review_message(request):
    """Post a message to the report communication thread."""
    from .models import EventReportMessage

    report_id = request.POST.get("report_id")
    message = (request.POST.get("message") or "").strip()
    if not report_id or not message:
        return JsonResponse({"ok": False, "error": "Message required"}, status=400)
    report = get_object_or_404(EventReport, id=report_id)
    # Access control: user should at least be in viewable set
    if not _reports_for_user(request).filter(id=report.id).exists():
        return JsonResponse({"ok": False, "error": "Not permitted"}, status=403)
    EventReportMessage.objects.create(report=report, sender=request.user, message=message)
    html = render_to_string("emt/partials/review_messages.html", {"report": report}, request=request)
    return JsonResponse({"ok": True, "html": html})


@login_required
def submit_request_view(request):
    if request.method == "POST":
        media_type = request.POST.get("media_type")
        title = request.POST.get("title")
        description = request.POST.get("description")
        event_date = request.POST.get("event_date")
        media_file = request.FILES.get("media_file")

        MediaRequest.objects.create(
            user=request.user,
            media_type=media_type,
            title=title,
            description=description,
            event_date=event_date,
            media_file=media_file,
        )
        messages.success(request, "Your media request has been submitted.")
        # Optional email notification to CDL team
        try:
            cdl_to = getattr(settings, "CDL_NOTIF_EMAIL", "")
            if cdl_to:
                subj = f"[CDL] New {media_type} request: {title}"
                body = (
                    f"{request.user.get_full_name() or request.user.username} submitted a {media_type} request "
                    f"for {event_date}.\n\n{description}"
                )
                send_notification(subj, body, cdl_to)
        except Exception:
            logger.exception("Failed to send CDL request notification")
        return redirect("cdl_dashboard")

    return render(request, "emt/cdl_submit_request.html")


@login_required
def my_requests_view(request):
    requests = MediaRequest.objects.filter(user=request.user).select_related('user').order_by("-created_at")
    return render(request, "emt/cdl_my_requests.html", {"requests": requests})


# ──────────────────────────────
# REPORT GENERATION
# ──────────────────────────────


def report_form(request):
    return render(request, "emt/report_generation.html")


@csrf_exempt
def generate_report_pdf(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    html = render_to_string("emt/pdf_template.html", {"data": request.POST})
    pdf = pdfkit.from_string(html, False)
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="Event_Report.pdf"'
    return response


# Helper to validate and persist text-based sections for proposals
def _clean_flow_content(content):
    lines = [line.strip() for line in (content or "").splitlines() if line.strip()]
    if not lines:
        raise forms.ValidationError("Schedule is required.")

    cleaned_lines = []
    for idx, line in enumerate(lines, start=1):
        try:
            time_str, activity = line.split("||", 1)
        except ValueError:
            raise forms.ValidationError(f"Line {idx}: invalid format.")
        time_str = time_str.strip()
        activity = activity.strip()
        if not time_str:
            raise forms.ValidationError(f"Line {idx}: date & time is required.")
        if not activity:
            raise forms.ValidationError(f"Line {idx}: activity is required.")
        try:
            datetime.fromisoformat(time_str)
        except ValueError:
            raise forms.ValidationError(f"Line {idx}: invalid date & time.")
        cleaned_lines.append(f"{time_str}||{activity}")
    return "\n".join(cleaned_lines)


def _save_text_sections(proposal, data):
    section_map = {
        "need_analysis": EventNeedAnalysis,
        "objectives": EventObjectives,
        "outcomes": EventExpectedOutcomes,
        "flow": TentativeFlow,
    }
    errors = {}
    for field, model in section_map.items():
        if field in data:
            content = data.get(field) or ""
            if field == "flow":
                content = content.strip()
                if content == "[]":
                    content = ""
                if not content:
                    continue
                try:
                    content = _clean_flow_content(content)
                except forms.ValidationError as e:
                    errors[field] = e.messages
                    continue
            obj, _ = model.objects.get_or_create(proposal=proposal)
            obj.content = content
            obj.save()
    return errors


def _save_activities(proposal, data, form=None):
    pattern = re.compile(r"^activity_(?:name|date)_(\d+)$")
    indices = sorted(
        {int(m.group(1)) for key in data.keys() if (m := pattern.match(key))}
    )
    if not indices:
        return True

    new_activities = []
    has_incomplete = False

    for index in indices:
        name = data.get(f"activity_name_{index}")
        date = data.get(f"activity_date_{index}")
        if name and date:
            # Ensure we persist a proper date object. If parsing fails, treat as incomplete.
            parsed_date = parse_date(str(date)) if date else None
            if parsed_date:
                new_activities.append(
                    EventActivity(proposal=proposal, name=name, date=parsed_date)
                )
            else:
                has_incomplete = True
                msg = f"Activity {index} has an invalid date."
                logger.warning(msg)
                if form is not None:
                    form.add_error(None, msg)
        elif name or date:
            has_incomplete = True
            msg = f"Activity {index} requires both name and date."
            logger.warning(msg)
            if form is not None:
                form.add_error(None, msg)

    if form is None:
        # Autosave: ignore incomplete rows but persist any complete ones
        if new_activities:
            proposal.activities.all().delete()
            EventActivity.objects.bulk_create(new_activities)
        return True

    if has_incomplete:
        return False

    proposal.activities.all().delete()
    EventActivity.objects.bulk_create(new_activities)
    return True


def _save_speakers(proposal, data, files):
    pattern = re.compile(
        r"^speaker_(?:full_name|designation|affiliation|contact_email|"
        r"contact_number|linkedin_url|photo|detailed_profile)_(\d+)$"
    )
    all_keys = list(data.keys()) + list(files.keys())
    indices = sorted({int(m.group(1)) for key in all_keys if (m := pattern.match(key))})
    if not indices:
        return
    proposal.speakers.all().delete()
    for index in indices:
        full_name = data.get(f"speaker_full_name_{index}")
        if full_name:
            SpeakerProfile.objects.create(
                proposal=proposal,
                full_name=full_name,
                designation=data.get(f"speaker_designation_{index}", ""),
                affiliation=data.get(f"speaker_affiliation_{index}", ""),
                contact_email=data.get(f"speaker_contact_email_{index}", ""),
                contact_number=data.get(f"speaker_contact_number_{index}", ""),
                linkedin_url=data.get(f"speaker_linkedin_url_{index}", ""),
                photo=files.get(f"speaker_photo_{index}"),
                detailed_profile=data.get(f"speaker_detailed_profile_{index}", ""),
            )


def _serialize_speaker(speaker: SpeakerProfile) -> dict:
    photo_url = ""
    if speaker.photo:
        try:
            photo_url = speaker.photo.url
        except ValueError:
            photo_url = ""
    return {
        "id": speaker.id,
        "full_name": speaker.full_name,
        "name": speaker.full_name,
        "designation": speaker.designation,
        "affiliation": speaker.affiliation,
        "organization": speaker.affiliation,
        "contact": speaker.contact_email,
        "contact_email": speaker.contact_email,
        "contact_number": speaker.contact_number,
        "linkedin_url": speaker.linkedin_url,
        "linkedin": speaker.linkedin_url,
        "detailed_profile": speaker.detailed_profile,
        "profile": speaker.detailed_profile,
        "bio": speaker.detailed_profile,
        "photo": photo_url,
        "photo_url": photo_url,
    }


def _parse_sdg_text(text: str):
    """Extract SDGGoal IDs from free text like 'SDG3: Good Health, SDG4: Education' or names.
    Returns a queryset of matching SDGGoal objects.
    """
    from core.models import SDGGoal

    if not text:
        return SDGGoal.objects.none()
    ids = set()
    names = []
    for token in re.split(r"[,\n]", text):
        t = token.strip()
        if not t:
            continue
        m = re.search(r"SDG\s*(\d+)", t, re.IGNORECASE)
        if m:
            try:
                ids.add(int(m.group(1)))
                continue
            except Exception:
                pass
        names.append(t)
    qs = SDGGoal.objects.none()
    if ids:
        qs = SDGGoal.objects.filter(id__in=list(ids))
    if names:
        by_name = SDGGoal.objects.filter(name__in=names)
        qs = qs.union(by_name)
    return qs


def _sync_proposal_from_report(proposal, report, payload: dict):
    """Synchronize proposal snapshot fields during report saves.
    - POS/PSO: copy from report.pos_pso_mapping if provided
    - SDGs: parse report.sdg_value_systems_mapping into proposal.sdg_goals
    Only update when corresponding values are present in the payload.
    """
    # POS/PSO
    if "pos_pso_mapping" in payload:
        proposal.pos_pso = payload.get("pos_pso_mapping", "")
        proposal.save(update_fields=["pos_pso"])

    # SDGs from free text mapping
    if "sdg_value_systems_mapping" in payload:
        goals = _parse_sdg_text(payload.get("sdg_value_systems_mapping", ""))
        proposal.sdg_goals.set(list(goals))
        proposal.save()


def _save_expenses(proposal, data):
    pattern = re.compile(r"^expense_(?:sl_no|particulars|amount)_(\d+)$")
    indices = sorted(
        {int(m.group(1)) for key in data.keys() if (m := pattern.match(key))}
    )
    if not indices:
        return
    proposal.expense_details.all().delete()
    for index in indices:
        particulars = data.get(f"expense_particulars_{index}")
        amount = data.get(f"expense_amount_{index}")
        if particulars and amount:
            sl_no = data.get(f"expense_sl_no_{index}") or 0
            ExpenseDetail.objects.create(
                proposal=proposal,
                sl_no=sl_no or 0,
                particulars=particulars,
                amount=amount,
            )


def _save_income(proposal, data):
    pattern = re.compile(
        r"^income_(?:sl_no|particulars|participants|rate|amount)_(\d+)$"
    )
    indices = sorted(
        {int(m.group(1)) for key in data.keys() if (m := pattern.match(key))}
    )
    if not indices:
        return
    proposal.income_details.all().delete()
    for index in indices:
        particulars = data.get(f"income_particulars_{index}")
        participants = data.get(f"income_participants_{index}")
        rate = data.get(f"income_rate_{index}")
        amount = data.get(f"income_amount_{index}")
        # Allow saving when only particulars and amount are provided
        if particulars and amount:
            sl_no = data.get(f"income_sl_no_{index}") or 0
            IncomeDetail.objects.create(
                proposal=proposal,
                sl_no=sl_no or 0,
                particulars=particulars,
                participants=participants or 0,
                rate=rate or 0,
                amount=amount,
            )


# ──────────────────────────────
# PROPOSAL DRAFT MANAGEMENT
# ──────────────────────────────


@login_required
def start_proposal(request):
    active_drafts = EventProposal.objects.filter(
        submitted_by=request.user,
        status=EventProposal.Status.DRAFT,
        is_user_deleted=False,
    ).count()

    if active_drafts >= MAX_ACTIVE_DRAFTS:
        messages.error(
            request,
            f"You can keep up to {MAX_ACTIVE_DRAFTS} drafts. Delete an older draft before creating a new one.",
        )
        return redirect("emt:proposal_drafts")

    active_year = get_active_academic_year()
    academic_year = active_year.year if active_year else ""

    proposal = EventProposal.objects.create(
        submitted_by=request.user,
        status=EventProposal.Status.DRAFT,
        academic_year=academic_year,
        event_title="Untitled Event",
    )

    return redirect("emt:submit_proposal_with_pk", pk=proposal.pk)


@login_required
def proposal_drafts(request):
    base_qs = EventProposal.objects.filter(
        submitted_by=request.user,
        status=EventProposal.Status.DRAFT,
        is_user_deleted=False,
    ).order_by("-updated_at")

    active_ids = list(base_qs.values_list("id", flat=True))

    if len(active_ids) > MAX_ACTIVE_DRAFTS:
        EventProposal.objects.filter(id__in=active_ids[MAX_ACTIVE_DRAFTS:]).update(
            is_user_deleted=True,
            updated_at=timezone.now(),
        )

    drafts_qs = EventProposal.objects.filter(
        submitted_by=request.user,
        status=EventProposal.Status.DRAFT,
        is_user_deleted=False,
    ).order_by("-updated_at")
    active_count = drafts_qs.count()
    drafts = list(drafts_qs[:MAX_ACTIVE_DRAFTS])
    remaining = max(0, MAX_ACTIVE_DRAFTS - active_count)

    context = {
        "drafts": drafts,
        "draft_limit": MAX_ACTIVE_DRAFTS,
        "active_count": active_count,
        "remaining_slots": remaining,
    }
    return render(request, "emt/proposal_drafts.html", context)


@login_required
@require_POST
def delete_proposal_draft(request, proposal_id):
    proposal = get_object_or_404(
        EventProposal,
        id=proposal_id,
        submitted_by=request.user,
        status=EventProposal.Status.DRAFT,
        is_user_deleted=False,
    )

    proposal.is_user_deleted = True
    proposal.save(update_fields=["is_user_deleted", "updated_at"])

    messages.success(request, "Draft removed. Admins can still review it from their dashboard.")

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": True})

    return redirect("emt:proposal_drafts")


# ──────────────────────────────
# PROPOSAL STEP 1: Proposal Submission
# ──────────────────────────────
@login_required
@ensure_csrf_cookie
def submit_proposal(request, pk=None):
    active_year = get_active_academic_year()
    selected_academic_year = active_year.year if active_year else ""

    if not pk:
        return redirect("emt:start_proposal")

    proposal = get_object_or_404(
        EventProposal.objects.prefetch_related(
            "faculty_incharges",
            "activities",
            "speakers",
            "expense_details",
            "income_details",
        ),
        pk=pk,
        submitted_by=request.user,
        is_user_deleted=False,
    )

    next_url = request.GET.get("next")

    if request.method == "POST":
        post_data = request.POST.copy()
        # Ignore client-supplied academic year; enforce server-side value
        post_data["academic_year"] = selected_academic_year
        logger.debug("submit_proposal POST data: %s", post_data)
        logger.debug(
            "Faculty IDs from POST: %s", post_data.getlist("faculty_incharges")
        )
        form = EventProposalForm(
            post_data,
            instance=proposal,
            selected_academic_year=selected_academic_year,
            user=request.user,
        )

        # --------- FACULTY INCHARGES QUERYSET FIX ---------
        faculty_ids = post_data.getlist("faculty_incharges")
        if faculty_ids:
            form.fields["faculty_incharges"].queryset = User.objects.filter(
                Q(role_assignments__role__name=FACULTY_ROLE) | Q(id__in=faculty_ids)
            ).distinct()
        else:
            form.fields["faculty_incharges"].queryset = User.objects.filter(
                role_assignments__role__name=FACULTY_ROLE
            ).distinct()
        # --------------------------------------------------

    else:
        # Only pre-populate form with existing data if it's still a draft
        form_instance = proposal if (proposal and proposal.status == "draft") else None

        form = EventProposalForm(
            instance=form_instance,
            selected_academic_year=selected_academic_year,
            user=request.user,
        )
        # Populate all faculty as available choices for JS search/select on GET.
        # Include already assigned faculty so their selections remain visible.
        fac_ids = (
            list(proposal.faculty_incharges.all().values_list("id", flat=True))
            if proposal
            else []
        )
        form.fields["faculty_incharges"].queryset = User.objects.filter(
            Q(role_assignments__role__name=FACULTY_ROLE) | Q(id__in=fac_ids)
        ).distinct()

    # Utility to get the display name from ID
    def get_name(model, value):
        try:
            if value:
                return model.objects.get(id=value).name
        except model.DoesNotExist:
            return ""
        return ""

    need_analysis = (
        EventNeedAnalysis.objects.filter(proposal=proposal).first()
        if proposal
        else None
    )
    objectives = (
        EventObjectives.objects.filter(proposal=proposal).first() if proposal else None
    )
    outcomes = (
        EventExpectedOutcomes.objects.filter(proposal=proposal).first()
        if proposal
        else None
    )
    flow = TentativeFlow.objects.filter(proposal=proposal).first() if proposal else None
    activities = list(proposal.activities.values("name", "date")) if proposal else []
    for act in activities:
        if act.get("date"):
            act["date"] = act["date"].isoformat()

    speakers = (
        [_serialize_speaker(sp) for sp in proposal.speakers.all()] if proposal else []
    )
    expenses = (
        list(proposal.expense_details.values("sl_no", "particulars", "amount"))
        if proposal
        else []
    )
    for ex in expenses:
        if ex.get("amount") is not None:
            ex["amount"] = float(ex["amount"])

    income = (
        list(
            proposal.income_details.values(
                "sl_no", "particulars", "participants", "rate", "amount"
            )
        )
        if proposal
        else []
    )
    for inc in income:
        for fld in ("rate", "amount"):
            if inc.get(fld) is not None:
                inc[fld] = float(inc[fld])

    ctx = {
        "form": form,
        "proposal": proposal,
        "org_types": OrganizationType.objects.filter(is_active=True).order_by("name"),
        "need_analysis": need_analysis,
        "objectives": objectives,
        "outcomes": outcomes,
        "flow": flow,
        "sdg_goals_list": json.dumps(
            list(SDGGoal.objects.filter(name__in=SDG_GOALS).values("id", "name"))
        ),
        "activities_json": json.dumps(activities),
        "speakers_json": json.dumps(speakers),
        "expenses_json": json.dumps(expenses),
        "income_json": json.dumps(income),
    }

    if request.method == "POST" and form.is_valid():
        proposal = form.save(commit=False)
        proposal.academic_year = selected_academic_year
        proposal.submitted_by = request.user
        is_final = "final_submit" in request.POST
        is_review = "review_submit" in request.POST
        if is_final:
            proposal.status = "submitted"
            proposal.submitted_at = timezone.now()
        else:
            proposal.status = "draft"
        proposal.save()
        form.save_m2m()
        _save_text_sections(proposal, request.POST)
        if not _save_activities(proposal, request.POST, form):
            ctx["form"] = form
            ctx["proposal"] = proposal
            return render(request, "emt/submit_proposal.html", ctx)
        if any(key.startswith("speaker_") for key in request.POST.keys()):
            _save_speakers(proposal, request.POST, request.FILES)
        if any(key.startswith("expense_") for key in request.POST.keys()):
            _save_expenses(proposal, request.POST)
        if any(key.startswith("income_") for key in request.POST.keys()):
            _save_income(proposal, request.POST)
        logger.debug(
            "Proposal %s saved with faculty %s",
            proposal.id,
            list(proposal.faculty_incharges.values_list("id", flat=True)),
        )
        if is_final:
            build_approval_chain(proposal)
            # Notifications: submitter and DIQAC
            try:
                subj = f"[IQAC] Proposal submitted: {proposal.event_title}"
                submitter_email = getattr(proposal.submitted_by, "email", "")
                if submitter_email:
                    send_notification(subj, "Your proposal was submitted and is under review.", submitter_email)
                diqac_emails = resolve_role_emails(proposal.organization, "iqac") or resolve_role_emails(proposal.organization, "diqac")
                if diqac_emails:
                    body = f"A new proposal has been submitted in {proposal.organization.name if proposal.organization else 'an organization'}: {proposal.event_title}."
                    send_notification(subj, body, diqac_emails)
            except Exception:
                logger.exception("Failed to send submission notifications")
            messages.success(
                request,
                f"Proposal '{proposal.event_title}' submitted.",
            )
            return redirect("emt:proposal_status_detail", proposal_id=proposal.id)
        if next_url:
            return redirect(next_url)
        if is_review:
            return redirect("emt:review_proposal", proposal_id=proposal.id)
        return redirect("emt:submit_need_analysis", proposal_id=proposal.id)

    return render(request, "emt/submit_proposal.html", ctx)


# ──────────────────────────────────────────────────────────────
#  Review proposal before final submit
# ──────────────────────────────────────────────────────────────
@login_required
@ensure_csrf_cookie
def review_proposal(request, proposal_id):
    proposal_qs = (
        EventProposal.objects.select_related(
            "need_analysis",
            "objectives",
            "expected_outcomes",
            "tentative_flow",
            "cdl_support",
        )
        .prefetch_related(
            "speakers",
            "expense_details",
            "income_details",
        )
        .filter(is_user_deleted=False)
    )
    # Prefetch speaker and expense details for efficient rendering
    proposal = get_object_or_404(
        proposal_qs,
        pk=proposal_id,
        submitted_by=request.user,
    )

    need_analysis = getattr(proposal, "need_analysis", None)
    objectives = getattr(proposal, "objectives", None)
    outcomes = getattr(proposal, "expected_outcomes", None)
    flow = getattr(proposal, "tentative_flow", None)
    speakers = list(proposal.speakers.all())
    expenses = list(proposal.expense_details.all())
    income = list(proposal.income_details.all())
    support = getattr(proposal, "cdl_support", None)

    if request.method == "POST" and "final_submit" in request.POST:
        proposal.status = "submitted"
        proposal.submitted_at = timezone.now()
        proposal.save()
        build_approval_chain(proposal)
        # Notifications: submitter and DIQAC
        try:
            subj = f"[IQAC] Proposal submitted: {proposal.event_title}"
            submitter_email = getattr(proposal.submitted_by, "email", "")
            if submitter_email:
                send_notification(subj, "Your proposal was submitted and is under review.", submitter_email)
            diqac_emails = resolve_role_emails(proposal.organization, "iqac") or resolve_role_emails(proposal.organization, "diqac")
            if diqac_emails:
                body = f"A new proposal has been submitted in {proposal.organization.name if proposal.organization else 'an organization'}: {proposal.event_title}."
                send_notification(subj, body, diqac_emails)
        except Exception:
            logger.exception("Failed to send submission notifications")
        messages.success(
            request,
            f"Proposal '{proposal.event_title}' submitted.",
        )
        return redirect("emt:proposal_status_detail", proposal_id=proposal.id)
    else:
        if proposal.status != EventProposal.Status.SUBMITTED:
            proposal.status = EventProposal.Status.DRAFT
            proposal.save(update_fields=["status"])

    ctx = {
        "proposal": proposal,
        "need_analysis": need_analysis,
        "objectives": objectives,
        "outcomes": outcomes,
        "flow": flow,
        "speakers": speakers,
        "expenses": expenses,
        "income": income,
        "cdl_support": support,
    }
    return render(request, "emt/review_proposal.html", ctx)


# ──────────────────────────────────────────────────────────────
#  Autosave draft (XHR from JS)
# ──────────────────────────────────────────────────────────────
@login_required
def autosave_proposal(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)
    errors = {}
    if request.content_type and request.content_type.startswith("multipart/form-data"):
        data = {}
        multi_fields = {"faculty_incharges", "sdg_goals"}
        for key in request.POST:
            values = request.POST.getlist(key)
            if key in multi_fields:
                data[key] = values
            else:
                data[key] = values if len(values) > 1 else values[0]
    else:
        try:
            raw = request.body.decode("utf-8")
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            logger.debug("autosave_proposal invalid json: %s", raw)
            return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    logger.debug("autosave_proposal payload: %s", data)

    # Replace department logic with generic organization
    org_type_val = data.get("organization_type")
    org_name_val = data.get("organization")
    if org_type_val and org_name_val and not str(org_name_val).isdigit():
        from core.models import Organization, OrganizationType

        org_type_obj = OrganizationType.objects.filter(name=org_type_val).first()
        if not org_type_obj:
            errors["organization_type"] = ["Organization type not found"]
        else:
            existing = Organization.objects.filter(
                org_type=org_type_obj, name__iexact=str(org_name_val).strip()
            ).first()
            if existing:
                data["organization"] = str(existing.id)
            else:
                errors["organization"] = ["Organization not found"]

    active_year = get_active_academic_year()
    selected_academic_year = active_year.year if active_year else ""

    existing_proposal = None
    proposal = None
    if pid := data.get("proposal_id"):
        existing_proposal = EventProposal.objects.filter(
            id=pid,
            submitted_by=request.user,
            is_user_deleted=False,
        ).first()

        # Don't autosave if proposal is already submitted
        if existing_proposal and existing_proposal.status != "draft":
            return JsonResponse(
                {"success": False, "error": "Cannot modify submitted proposal"}
            )

    # If payload only has text sections, skip full form validation
    text_keys = {"need_analysis", "objectives", "outcomes", "flow"}
    if existing_proposal and set(data.keys()).issubset(text_keys | {"proposal_id"}):
        text_errors = _save_text_sections(existing_proposal, data)
        if text_errors:
            logger.debug("autosave_proposal text errors: %s", text_errors)
            return JsonResponse(
                {
                    "success": False,
                    "proposal_id": existing_proposal.id,
                    "errors": text_errors,
                }
            )
        return JsonResponse({"success": True, "proposal_id": existing_proposal.id})

    if existing_proposal and existing_proposal.academic_year:
        data["academic_year"] = existing_proposal.academic_year
    elif selected_academic_year:
        data["academic_year"] = selected_academic_year

    form = EventProposalForm(
        data,
        instance=existing_proposal,
        user=request.user,
        selected_academic_year=selected_academic_year,
    )
    form = EventProposalForm(data, instance=proposal, user=request.user)
    faculty_ids = data.get("faculty_incharges") or []
    if faculty_ids:
        form.fields["faculty_incharges"].queryset = User.objects.filter(
            Q(role_assignments__role__name=FACULTY_ROLE) | Q(id__in=faculty_ids)
        ).distinct()
    else:
        form.fields["faculty_incharges"].queryset = User.objects.filter(
            role_assignments__role__name=FACULTY_ROLE
        ).distinct()

    creating_new = existing_proposal is None

    if creating_new:
        active_drafts = EventProposal.objects.filter(
            submitted_by=request.user,
            status=EventProposal.Status.DRAFT,
            is_user_deleted=False,
        ).count()
        if active_drafts >= MAX_ACTIVE_DRAFTS:
            message = (
                "You have reached the maximum number of saved drafts. "
                "Delete an existing draft to continue."
            )
            return JsonResponse(
                {
                    "success": False,
                    "errors": {"draft_limit": [message]},
                    "limit": MAX_ACTIVE_DRAFTS,
                }
            )

    is_valid = form.is_valid()
    if not is_valid:
        logger.debug("autosave_proposal form errors: %s", form.errors)

    # Persist any cleaned fields even if the form has validation errors
    proposal = form.instance
    proposal.is_user_deleted = False
    for field, value in form.cleaned_data.items():
        if isinstance(form.fields.get(field), forms.ModelMultipleChoiceField):
            continue
        setattr(proposal, field, value)
    proposal.submitted_by = request.user
    proposal.status = "draft"
    proposal.save()

    for field, value in form.cleaned_data.items():
        if isinstance(form.fields.get(field), forms.ModelMultipleChoiceField):
            getattr(proposal, field).set(value)

    text_errors = _save_text_sections(proposal, data)

    if not is_valid:
        errors.update(form.errors)
    if text_errors:
        errors.update(text_errors)

    # Validate activities
    act_errors = {}
    idx = 1
    while any(key in data for key in [f"activity_name_{idx}", f"activity_date_{idx}"]):
        name = data.get(f"activity_name_{idx}")
        date = data.get(f"activity_date_{idx}")
        missing = {}
        if name or date:
            if not name:
                missing["name"] = "This field is required."
            if not date:
                missing["date"] = "This field is required."
            else:
                parsed = parse_date(str(date))
                if not parsed:
                    missing["date"] = "Enter a valid date."
                else:
                    data[f"activity_date_{idx}"] = parsed.isoformat()
        if missing:
            act_errors[idx] = missing
        idx += 1
    if act_errors:
        errors["activities"] = act_errors

    # Validate speakers
    sp_errors = {}
    sp_idx = 0
    sp_fields = [
        "full_name",
        "designation",
        "affiliation",
        "contact_email",
        "detailed_profile",
    ]
    email_validator = EmailValidator()
    url_validator = URLValidator()
    while any(
        f"speaker_{field}_{sp_idx}" in data
        for field in sp_fields + ["contact_number", "linkedin_url", "photo"]
    ):
        missing = {}
        has_any = False
        for field in sp_fields:
            value = data.get(f"speaker_{field}_{sp_idx}")
            if value:
                has_any = True
                if field == "full_name" and not NAME_RE.fullmatch(value):
                    missing[field] = "Enter a valid name (letters, spaces, .'- only)."
                elif field == "contact_email":
                    try:
                        email_validator(value)
                    except ValidationError:
                        missing[field] = "Enter a valid email address."
            else:
                missing[field] = "This field is required."

        linkedin = data.get(f"speaker_linkedin_url_{sp_idx}")
        if linkedin:
            try:
                url_validator(linkedin)
            except ValidationError:
                missing["linkedin_url"] = "Enter a valid URL."

        if has_any and missing:
            sp_errors[sp_idx] = missing
        sp_idx += 1
    if sp_errors:
        errors["speakers"] = sp_errors

    # Validate expenses
    ex_errors = {}
    ex_idx = 0
    while any(
        f"expense_{field}_{ex_idx}" in data
        for field in ["sl_no", "particulars", "amount"]
    ):
        particulars = data.get(f"expense_particulars_{ex_idx}")
        amount = data.get(f"expense_amount_{ex_idx}")
        missing = {}
        if particulars or amount:
            if not particulars:
                missing["particulars"] = "This field is required."
            if not amount:
                missing["amount"] = "This field is required."
        if missing:
            ex_errors[ex_idx] = missing
        ex_idx += 1
    if ex_errors:
        errors["expenses"] = ex_errors

    # Validate income
    in_errors = {}
    in_idx = 0
    while any(
        f"income_{field}_{in_idx}" in data
        for field in ["particulars", "participants", "rate", "amount"]
    ):
        particulars = data.get(f"income_particulars_{in_idx}")
        participants = data.get(f"income_participants_{in_idx}")
        rate = data.get(f"income_rate_{in_idx}")
        amount = data.get(f"income_amount_{in_idx}")
        missing = {}
        # Only require particulars and amount; participants and rate are optional
        if any([particulars, participants, rate, amount]):
            if not particulars:
                missing["particulars"] = "This field is required."
            if not amount:
                missing["amount"] = "This field is required."
        if missing:
            in_errors[in_idx] = missing
        in_idx += 1
    if in_errors:
        errors["income"] = in_errors

    _save_activities(proposal, data)
    _save_speakers(proposal, data, request.FILES)
    _save_expenses(proposal, data)
    _save_income(proposal, data)

    if errors:
        logger.debug("autosave_proposal dynamic errors: %s", errors)

    logger.debug(
        "Autosaved proposal %s with faculty %s",
        proposal.id,
        list(proposal.faculty_incharges.values_list("id", flat=True)),
    )

    # Indicate overall success based on whether any validation errors were
    # encountered. Drafts are still persisted even when ``success`` is False so
    # the frontend can surface issues without clearing the user's progress.
    success = not errors
    response = {"success": success, "proposal_id": proposal.id}
    if errors:
        response["errors"] = errors
    return JsonResponse(response)


@login_required
def proposal_live_state(request, proposal_id):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    proposal = get_object_or_404(
        EventProposal.objects.select_related(
            "need_analysis",
            "objectives",
            "expected_outcomes",
            "tentative_flow",
            "organization__org_type",
        ).prefetch_related(
            "activities",
            "speakers",
            "expense_details",
            "income_details",
            "sdg_goals",
            "faculty_incharges",
        ),
        pk=proposal_id,
        submitted_by=request.user,
    )

    updated_at = proposal.updated_at
    since_param = request.GET.get("since")
    if since_param:
        since_dt = parse_datetime(since_param)
        if since_dt is not None and timezone.is_naive(since_dt):
            since_dt = timezone.make_aware(since_dt, timezone.get_current_timezone())
        if since_dt and updated_at and updated_at <= since_dt:
            return JsonResponse(
                {
                    "changed": False,
                    "updated_at": updated_at.isoformat() if updated_at else None,
                }
            )

    def _serialize_date(value):
        return value.isoformat() if value else ""

    basic_fields = {
        "event_title": proposal.event_title or "",
        "target_audience": proposal.target_audience or "",
        "event_focus_type": proposal.event_focus_type or "",
        "venue": proposal.venue or "",
        "event_start_date": _serialize_date(proposal.event_start_date),
        "event_end_date": _serialize_date(proposal.event_end_date),
        "academic_year": proposal.academic_year or "",
        "num_activities": proposal.num_activities or "",
        "pos_pso": proposal.pos_pso or "",
        "student_coordinators": proposal.student_coordinators or "",
        "committees_collaborations": proposal.committees_collaborations or "",
    }

    if proposal.organization_id:
        basic_fields.update(
            {
                "organization": str(proposal.organization_id),
                "organization_name": proposal.organization.name,
            }
        )
        if proposal.organization and proposal.organization.org_type_id:
            basic_fields.update(
                {
                    "organization_type": str(proposal.organization.org_type_id),
                    "organization_type_name": proposal.organization.org_type.name,
                }
            )
    else:
        basic_fields.update({"organization": "", "organization_type": ""})

    text_sections = {
        "need_analysis": getattr(proposal.need_analysis, "content", ""),
        "objectives": getattr(proposal.objectives, "content", ""),
        "outcomes": getattr(proposal.expected_outcomes, "content", ""),
        "flow": getattr(proposal.tentative_flow, "content", ""),
    }

    activities = [
        {
            "name": activity.name,
            "date": activity.date.isoformat() if activity.date else "",
        }
        for activity in proposal.activities.all()
    ]

    speakers = [_serialize_speaker(speaker) for speaker in proposal.speakers.all()]

    expenses = []
    for expense in proposal.expense_details.all():
        expenses.append(
            {
                "sl_no": expense.sl_no,
                "particulars": expense.particulars,
                "amount": float(expense.amount) if expense.amount is not None else None,
            }
        )

    income = []
    for item in proposal.income_details.all():
        income.append(
            {
                "sl_no": item.sl_no,
                "particulars": item.particulars,
                "participants": item.participants,
                "rate": float(item.rate) if item.rate is not None else None,
                "amount": float(item.amount) if item.amount is not None else None,
            }
        )

    payload = {
        "fields": basic_fields,
        "text_sections": text_sections,
        "activities": activities,
        "speakers": speakers,
        "expenses": expenses,
        "income": income,
        "sdg_goals": list(proposal.sdg_goals.values("id", "name")),
        "faculty_incharges": list(
            proposal.faculty_incharges.values("id", "first_name", "last_name")
        ),
    }

    return JsonResponse(
        {
            "changed": True,
            "updated_at": updated_at.isoformat() if updated_at else None,
            "payload": payload,
        }
    )


@login_required
@require_POST
def reset_proposal_draft(request):
    """Delete the current draft proposal and its related data."""
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    pid = data.get("proposal_id")
    if not pid:
        return JsonResponse(
            {"success": False, "error": "proposal_id required"}, status=400
        )

    proposal = EventProposal.objects.filter(
        id=pid,
        submitted_by=request.user,
        status=EventProposal.Status.DRAFT,
        is_user_deleted=False,
    ).first()
    if not proposal:
        return JsonResponse({"success": False, "error": "Draft not found"}, status=404)

    proposal.is_user_deleted = True
    proposal.save(update_fields=["is_user_deleted", "updated_at"])
    return JsonResponse({"success": True})


# ──────────────────────────────────────────────────────────────
#  Remaining steps (unchanged)
# ──────────────────────────────────────────────────────────────
@login_required
def submit_need_analysis(request, proposal_id):
    proposal = get_object_or_404(
        EventProposal,
        id=proposal_id,
        submitted_by=request.user,
        is_user_deleted=False,
    )
    instance = EventNeedAnalysis.objects.filter(proposal=proposal).first()
    next_url = request.GET.get("next")

    if request.method == "POST":
        form = NeedAnalysisForm(request.POST, instance=instance)
        logger.debug("NeedAnalysis POST data: %s", request.POST)
        if form.is_valid():
            need = form.save(commit=False)
            need.proposal = proposal
            need.save()
            logger.debug("NeedAnalysis saved for proposal %s", proposal.id)
            if next_url:
                return redirect(next_url)
            return redirect("emt:submit_objectives", proposal_id=proposal.id)
    else:
        form = NeedAnalysisForm(instance=instance)

    return render(
        request, "emt/need_analysis.html", {"form": form, "proposal": proposal}
    )


@login_required
def submit_objectives(request, proposal_id):
    proposal = get_object_or_404(
        EventProposal,
        id=proposal_id,
        submitted_by=request.user,
        is_user_deleted=False,
    )
    instance = EventObjectives.objects.filter(proposal=proposal).first()
    next_url = request.GET.get("next")

    if request.method == "POST":
        form = ObjectivesForm(request.POST, instance=instance)
        logger.debug("Objectives POST data: %s", request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.proposal = proposal
            obj.save()
            logger.debug("Objectives saved for proposal %s", proposal.id)
            if next_url:
                return redirect(next_url)
            return redirect("emt:submit_expected_outcomes", proposal_id=proposal.id)
    else:
        form = ObjectivesForm(instance=instance)

    return render(request, "emt/objectives.html", {"form": form, "proposal": proposal})


@login_required
def submit_expected_outcomes(request, proposal_id):
    proposal = get_object_or_404(
        EventProposal,
        id=proposal_id,
        submitted_by=request.user,
        is_user_deleted=False,
    )
    instance = EventExpectedOutcomes.objects.filter(proposal=proposal).first()
    next_url = request.GET.get("next")

    if request.method == "POST":
        form = ExpectedOutcomesForm(request.POST, instance=instance)
        logger.debug("ExpectedOutcomes POST data: %s", request.POST)
        if form.is_valid():
            outcome = form.save(commit=False)
            outcome.proposal = proposal
            outcome.save()
            logger.debug("ExpectedOutcomes saved for proposal %s", proposal.id)
            if next_url:
                return redirect(next_url)
            return redirect("emt:submit_tentative_flow", proposal_id=proposal.id)
    else:
        form = ExpectedOutcomesForm(instance=instance)

    return render(
        request,
        "emt/submit_expected_outcomes.html",
        {"form": form, "proposal": proposal},
    )


@login_required
def submit_tentative_flow(request, proposal_id):
    proposal = get_object_or_404(
        EventProposal,
        id=proposal_id,
        submitted_by=request.user,
        is_user_deleted=False,
    )
    instance = TentativeFlow.objects.filter(proposal=proposal).first()
    next_url = request.GET.get("next")

    if request.method == "POST":
        form = TentativeFlowForm(request.POST, instance=instance)
        logger.debug("TentativeFlow POST data: %s", request.POST)
        if form.is_valid():
            flow = form.save(commit=False)
            flow.proposal = proposal
            flow.save()
            logger.debug("TentativeFlow saved for proposal %s", proposal.id)
            if next_url:
                return redirect(next_url)
            return redirect("emt:submit_speaker_profile", proposal_id=proposal.id)
    else:
        form = TentativeFlowForm(instance=instance)

    return render(
        request, "emt/tentative_flow.html", {"form": form, "proposal": proposal}
    )


# ──────────────────────────────
# PROPOSAL STEP 6: Speaker Profile
# ──────────────────────────────
@login_required
def submit_speaker_profile(request, proposal_id):
    proposal = get_object_or_404(
        EventProposal,
        id=proposal_id,
        submitted_by=request.user,
        is_user_deleted=False,
    )
    # Track wizard progress for breadcrumbs/UI
    request.session["proposal_step"] = "speaker_profile"
    SpeakerFS = modelformset_factory(
        SpeakerProfile, form=SpeakerProfileForm, extra=1, can_delete=True
    )
    next_url = request.GET.get("next")

    if request.method == "POST":
        formset = SpeakerFS(
            request.POST,
            request.FILES,
            queryset=SpeakerProfile.objects.filter(proposal=proposal),
        )
        if formset.is_valid():
            objs = formset.save(commit=False)
            for obj in objs:
                obj.proposal = proposal
                obj.save()
            for obj in formset.deleted_objects:
                obj.delete()
            if next_url:
                return redirect(next_url)
            return redirect("emt:submit_expense_details", proposal_id=proposal.id)
    else:
        formset = SpeakerFS(queryset=SpeakerProfile.objects.filter(proposal=proposal))

    return render(
        request, "emt/speaker_profile.html", {"formset": formset, "proposal": proposal}
    )


# ──────────────────────────────
# PROPOSAL STEP 7: Expense Details
# ──────────────────────────────
@login_required
def submit_expense_details(request, proposal_id):
    proposal = get_object_or_404(
        EventProposal, id=proposal_id, submitted_by=request.user
    )
    # Track wizard state for breadcrumb/progress UI
    request.session["proposal_step"] = "expense_details"
    ExpenseFS = modelformset_factory(
        ExpenseDetail, form=ExpenseDetailForm, extra=1, can_delete=True
    )
    next_url = request.GET.get("next")

    if request.method == "POST":
        formset = ExpenseFS(
            request.POST, queryset=ExpenseDetail.objects.filter(proposal=proposal)
        )
        if formset.is_valid():
            objs = formset.save(commit=False)
            for obj in objs:
                obj.proposal = proposal
                obj.save()
            for obj in formset.deleted_objects:
                obj.delete()
            if next_url:
                return redirect(next_url)
            # Move wizard to CDL support step and notify user
            request.session["proposal_step"] = "cdl_support"
            messages.info(request, "Expense details saved. Proceed to CDL Support.")
            return redirect("emt:submit_cdl_support", proposal_id=proposal.id)
    else:
        formset = ExpenseFS(queryset=ExpenseDetail.objects.filter(proposal=proposal))

    return render(
        request, "emt/expense_details.html", {"proposal": proposal, "formset": formset}
    )


# ──────────────────────────────
# PROPOSAL STEP 8: CDL Support
# ──────────────────────────────
@login_required
@ensure_csrf_cookie
def submit_cdl_support(request, proposal_id):
    proposal = get_object_or_404(
        EventProposal, id=proposal_id, submitted_by=request.user
    )
    # Ensure wizard/breadcrumb reflects final step
    request.session["proposal_step"] = "cdl_support"
    instance = getattr(proposal, "cdl_support", None)
    next_url = request.GET.get("next")

    if request.method == "POST":
        form = CDLSupportForm(request.POST, instance=instance)
        if form.is_valid():
            support = form.save(commit=False)
            support.proposal = proposal
            support.other_services = form.cleaned_data.get("other_services", [])
            support.save()

            proposal.status = "draft"
            proposal.save()

            if "review_submit" in request.POST:
                return redirect("emt:review_proposal", proposal_id=proposal.id)
            if next_url:
                return redirect(next_url)

            messages.success(request, "CDL support saved.")
            return redirect("emt:submit_cdl_support", proposal_id=proposal.id)
    else:
        initial = {}
        if instance:
            initial["other_services"] = instance.other_services
        form = CDLSupportForm(instance=instance, initial=initial)

    return render(request, "emt/cdl_support.html", {"form": form, "proposal": proposal})


# ──────────────────────────────
# Event Management Suite Dashboard
# ──────────────────────────────
@login_required
def proposal_status_detail(request, proposal_id):
    proposal = get_object_or_404(
        EventProposal.objects.select_related(
            "organization", "submitted_by"
        ).prefetch_related("sdg_goals", "faculty_incharges"),
        id=proposal_id,
        submitted_by=request.user,
    )

    if request.method == "POST":
        action = request.POST.get(
            "action"
        )  # Assuming you get 'approve' or 'reject' from a form

        if action == "approve":
            proposal.status = "Approved"  # Use your actual status value

            # Add the logging statement for approval
            logger.info(
                f"User '{request.user.username}' APPROVED proposal '{proposal.title}' (ID: {proposal.id})."
            )

            proposal.save()

        elif action == "reject":
            proposal.status = "Rejected"  # Use your actual status value
            rejection_reason = request.POST.get("reason", "No reason provided")

            # Add the logging statement for rejection
            logger.warning(
                f"User '{request.user.username}' REJECTED proposal '{proposal.title}' (ID: {proposal.id}). "
                f"Reason: {rejection_reason}"
            )

            proposal.save()

        return redirect("some-success-url")

    # Get approval steps
    all_steps = ApprovalStep.objects.filter(proposal=proposal).order_by("order_index")
    visible_steps = all_steps.visible_for_ui()

    # Total budget calculation
    budget_total = (
        ExpenseDetail.objects.filter(proposal=proposal).aggregate(total=Sum("amount"))[
            "total"
        ]
        or 0
    )

    # Dynamically assign statuses.
    db_status = (proposal.status or "").strip().lower()

    if db_status == "rejected":
        statuses = ["draft", "submitted", "under_review", "rejected"]
    else:
        statuses = ["draft", "submitted", "under_review", "finalized"]

    status_index = statuses.index(db_status) if db_status in statuses else 0
    # Progress should start at 0% for the initial status
    if len(statuses) > 1:
        progress_percent = int(status_index * 100 / (len(statuses) - 1))
    else:
        progress_percent = 100
    current_label = statuses[status_index].replace("_", " ").capitalize()

    return render(
        request,
        "emt/proposal_status_detail.html",
        {
            "proposal": proposal,
            "steps": visible_steps,
            "all_steps": all_steps,
            "budget_total": budget_total,
            "statuses": statuses,
            "status_index": status_index,
            "progress_percent": progress_percent,
            "current_label": current_label,
        },
    )


# ──────────────────────────────
# PENDING REPORTS, GENERATION, SUCCESS
# ──────────────────────────────


@login_required
def pending_reports(request):
    # Base: proposals approved/finalized that still need an initial report
    # OPTIMIZED: Added organization and submitted_by to select_related
    base_qs = EventProposal.objects.filter(
        submitted_by=request.user,
        status__in=["approved", "finalized"],
        report_generated=False,
    ).select_related("report_assigned_to", "organization", "submitted_by")

    # OPTIMIZED: Added deeper proposal relations to select_related
    sent_back_reports = (
        EventReport.objects.select_related(
            "proposal",
            "proposal__report_assigned_to",
            "proposal__organization",
            "proposal__submitted_by",
        )
        .filter(proposal__submitted_by=request.user, review_stage=EventReport.ReviewStage.USER)
    )

    # Merge unique proposals and annotate sent_back flag for template rendering
    proposals_by_id = {p.id: p for p in base_qs}
    for r in sent_back_reports:
        p = r.proposal
        if p is None:
            continue
        proposals_by_id[p.id] = p
        try:
            setattr(p, "sent_back", True)
            # Optionally surface last feedback snippet (not displayed by default template)
            setattr(p, "last_feedback", (r.session_feedback or r.iqac_feedback or "").strip())
        except Exception:
            pass

    proposals = list(proposals_by_id.values())
    # Ensure every proposal has last_feedback attribute to simplify template logic
    for p in proposals:
        if not hasattr(p, "last_feedback"):
            setattr(p, "last_feedback", "")
    return render(request, "emt/pending_reports.html", {"proposals": proposals})


@login_required
def pending_report_feedback(request, proposal_id: int):
    """Display full feedback history for a proposal's event report to the submitter (or assigned faculty).

    Shows concatenated iqac_feedback plus the latest session_feedback.
    """
    proposal = get_object_or_404(EventProposal.objects.prefetch_related('faculty_incharges'), id=proposal_id)
    # Permission: submitter or faculty incharges (or superuser/staff)
    if not (
        request.user == proposal.submitted_by
        or request.user.is_superuser
        or request.user.is_staff
        or proposal.faculty_incharges.filter(id=request.user.id).exists()
    ):
        return HttpResponse(status=403)

    report = EventReport.objects.filter(proposal=proposal).first()
    iqac_feedback = (report.iqac_feedback or "") if report else ""
    session_feedback = (report.session_feedback or "") if report else ""
    # Build structured sections for template (split by blank lines)
    def _split_chunks(txt: str):
        import re
        raw = (txt or "").strip()
        if not raw:
            return []
        parts = re.split(r"\n{2,}", raw)
        return [p.strip() for p in parts if p.strip()]

    iqac_chunks = _split_chunks(iqac_feedback)
    latest_feedback = session_feedback.strip() if session_feedback.strip() and session_feedback not in iqac_feedback else ""

    context = {
        "proposal": proposal,
        "report": report,
        "iqac_feedback": iqac_feedback,
        "iqac_chunks": iqac_chunks,
        "latest_feedback": latest_feedback,
    }
    return render(request, "emt/pending_report_feedback.html", context)


@login_required
@require_http_methods(["GET"])
def api_event_participants(request, proposal_id):
    """API endpoint to search for eligible assignees for a specific event"""
    try:
        proposal = get_object_or_404(EventProposal, id=proposal_id)

        # Check if user has permission to view this proposal
        if (
            proposal.submitted_by != request.user
            and request.user not in proposal.faculty_incharges.all()
        ):
            return JsonResponse({"error": "Permission denied"}, status=403)

        query = request.GET.get("q", "").strip().lower()

        # Collect all eligible users
        participants = set()

        # Members of the event's organization
        if proposal.organization:
            memberships = OrganizationMembership.objects.filter(
                organization=proposal.organization
            )

            # Filter by target audience roles if specified
            if proposal.target_audience:
                target_roles = [
                    r.strip().lower() for r in proposal.target_audience.split(",")
                ]
                memberships = memberships.filter(role__in=target_roles)

            for membership in memberships.select_related("user"):
                participants.add(membership.user)

        # Always include submitter and faculty incharges
        participants.add(proposal.submitted_by)
        for faculty in proposal.faculty_incharges.all():
            participants.add(faculty)

        # Apply search filter
        if query:
            filtered_participants = [
                user
                for user in participants
                if query in (user.get_full_name() or "").lower()
                or query in user.username.lower()
                or query in (user.email or "").lower()
            ]
        else:
            filtered_participants = list(participants)

        results = []
        for user in filtered_participants:
            # Determine role to display
            if user == proposal.submitted_by:
                role = "Submitter"
            elif user in proposal.faculty_incharges.all():
                role = "Faculty Incharge"
            else:
                membership = OrganizationMembership.objects.filter(
                    user=user, organization=proposal.organization
                ).first()
                role = membership.role.capitalize() if membership else "Member"

            results.append(
                {
                    "id": user.id,
                    "name": user.get_full_name() or user.username,
                    "email": user.email,
                    "role": role,
                    "username": user.username,
                }
            )

        return JsonResponse({"participants": results})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def assign_report_task(request, proposal_id):
    """API endpoint to assign report generation task to a user"""
    try:
        proposal = get_object_or_404(EventProposal, id=proposal_id)

        # Check if user has permission to assign (only submitter can assign)
        if proposal.submitted_by != request.user:
            return JsonResponse(
                {"error": "Only the event submitter can assign report tasks"},
                status=403,
            )

        data = json.loads(request.body)
        assigned_user_id = data.get("assigned_user_id")

        if not assigned_user_id:
            return JsonResponse({"error": "assigned_user_id is required"}, status=400)

        # Verify the assigned user is eligible for assignment
        assigned_user = get_object_or_404(User, id=assigned_user_id)

        if (
            assigned_user != proposal.submitted_by
            and assigned_user not in proposal.faculty_incharges.all()
        ):

            membership_qs = OrganizationMembership.objects.filter(
                user=assigned_user,
                organization=proposal.organization,
            )

            if proposal.target_audience:
                target_roles = [
                    r.strip().lower() for r in proposal.target_audience.split(",")
                ]
                membership_qs = membership_qs.filter(role__in=target_roles)

            if not membership_qs.exists():
                return JsonResponse(
                    {
                        "error": "Can only assign to event organization members or target audience"
                    },
                    status=400,
                )

        # Update assignment
        proposal.report_assigned_to = assigned_user
        proposal.report_assigned_at = timezone.now()
        proposal.save()

        return JsonResponse(
            {
                "success": True,
                "assigned_to": {
                    "id": assigned_user.id,
                    "name": assigned_user.get_full_name() or assigned_user.username,
                    "email": assigned_user.email,
                },
                "assigned_at": proposal.report_assigned_at.isoformat(),
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def unassign_report_task(request, proposal_id):
    """API endpoint to remove report generation assignment"""
    try:
        proposal = get_object_or_404(EventProposal, id=proposal_id)

        # Check if user has permission to unassign (only submitter can unassign)
        if proposal.submitted_by != request.user:
            return JsonResponse(
                {"error": "Only the event submitter can unassign report tasks"},
                status=403,
            )

        # Remove assignment
        proposal.report_assigned_to = None
        proposal.report_assigned_at = None
        proposal.save()

        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def generate_report(request, proposal_id):
    proposal = get_object_or_404(
        EventProposal, id=proposal_id, submitted_by=request.user
    )

    # Create report instance if not exists
    report, created = EventReport.objects.get_or_create(proposal=proposal)

    # Generate report content - replace with your actual generation logic
    # This is just a placeholder - you should integrate with your AI service
    generated_content = f"Report for {proposal.event_title}\n\nGenerated on {timezone.now().strftime('%Y-%m-%d')}"

    # Save to database
    report.ai_generated_report = generated_content
    if not report.summary:
        report.summary = generated_content
    report.save()

    # Add logging
    logger.info(
        f"User '{request.user.username}' generated report for proposal '{proposal.event_title}' (ID: {proposal.id})"
    )

    proposal.report_generated = True
    proposal.save()

    return redirect("emt:report_success", proposal_id=proposal.id)


@login_required
def report_success(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id)
    return render(request, "emt/report_success.html", {"proposal": proposal})


@login_required
def generated_reports(request):
    reports = (
        EventReport.objects.select_related("proposal", "proposal__organization")
        .filter(proposal__submitted_by=request.user)
        .order_by("-created_at")
    )
    return render(
        request,
        "emt/generated_reports.html",
        {"reports": reports},
    )


@login_required
def view_report(request, report_id):
    """
    Displays the details of a single event report.
    The report_id here should correspond to the EventReport's ID.
    """
    # Get the report object, ensuring the user has access via the proposal
    report = get_object_or_404(
        EventReport.objects.select_related("proposal"),
        id=report_id,
        proposal__submitted_by=request.user,
    )

    # Add the logging statement here
    logger.info(
        f"User '{request.user.username}' viewed the report for event "
        f"'{report.proposal.event_title}' (Report ID: {report.id})."
    )

    # Render the template with the report and its proposal
    context = {
        "report": report,
        "proposal": report.proposal,  # Pass the proposal for more context
    }
    return render(request, "emt/view_report.html", context)


# ──────────────────────────────
# FILE DOWNLOAD (PLACEHOLDER)
# ──────────────────────────────


@login_required
def download_pdf(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id)
    report = get_object_or_404(EventReport, proposal=proposal)

    response = HttpResponse(content_type="application/pdf")
    safe_title = (proposal.event_title or "event-report").replace("\n", " ")
    response["Content-Disposition"] = (
        f'attachment; filename="{safe_title}_report.pdf"'
    )

    from html import escape
    from io import BytesIO

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=1 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CenteredTitle",
            parent=styles["Heading1"],
            alignment=TA_CENTER,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            fontSize=14,
            leading=18,
            spaceBefore=18,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyTextTight",
            parent=styles["BodyText"],
            leading=14,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Muted",
            parent=styles["BodyText"],
            textColor=colors.grey,
            leading=12,
            spaceAfter=8,
        )
    )

    def _paragraph(text: str | None):
        if not text or not str(text).strip():
            return Paragraph("Not provided.", styles["Muted"])
        html = escape(str(text)).replace("\n", "<br/>")
        return Paragraph(html, styles["BodyTextTight"])

    def _bullet_paragraph(items: list[str] | None):
        if not items:
            return Paragraph("Not provided.", styles["Muted"])
        cleaned = [escape(str(item)) for item in items if str(item).strip()]
        if not cleaned:
            return Paragraph("Not provided.", styles["Muted"])
        html = "<br/>".join(f"• {item}" for item in cleaned)
        return Paragraph(html, styles["BodyTextTight"])

    data = _build_report_initial_data(report)

    elements = [
        Paragraph("Event Report", styles["CenteredTitle"]),
        Paragraph(escape(data["event"]["title"]) or "Untitled Event", styles["Heading2"]),
        Spacer(1, 12),
    ]

    meta_rows = [
        ["Organization", data["event"]["department"] or "-"],
        ["Event Schedule", data["event"]["date"] or "-"],
        ["Venue", data["event"]["venue"] or "-"],
        ["Generated On", timezone.now().strftime("%d %b %Y")],
    ]

    if data["participants"]["attendees_count"]:
        meta_rows.append(["Total Participants", data["participants"]["attendees_count"]])
    if data["participants"]["organising_committee"]["student_volunteers_count"]:
        meta_rows.append([
            "Student Volunteers",
            data["participants"]["organising_committee"]["student_volunteers_count"],
        ])

    meta_table = Table(meta_rows, colWidths=[1.8 * inch, doc.width - 1.8 * inch])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.lightgrey),
                ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.lightgrey),
                ("LINEBEFORE", (0, 0), (0, -1), 0.5, colors.lightgrey),
                ("LINEAFTER", (-1, 0), (-1, -1), 0.5, colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(meta_table)

    def _section(title: str, content):
        elements.append(Paragraph(title, styles["SectionHeading"]))
        if isinstance(content, list):
            elements.append(_bullet_paragraph(content))
        else:
            elements.append(_paragraph(content))

    narrative = data.get("narrative", {})
    analysis = data.get("analysis", {})
    mapping = data.get("mapping", {})
    iqac = data.get("iqac", {})

    primary_narrative = report.ai_generated_report or report.summary
    if primary_narrative:
        _section("Narrative Overview", primary_narrative)

    _section("Event Summary", narrative.get("summary_overall_event"))
    _section("Key Outcomes", narrative.get("outcomes", []))
    _section("Social Relevance", narrative.get("social_relevance", []))
    _section("Impact on Stakeholders", analysis.get("impact_attendees"))
    _section("Lessons Learned", analysis.get("impact_volunteers"))
    _section("POS/PSO Mapping", mapping.get("pos_psos"))
    _section("Contemporary Requirements", mapping.get("contemporary_requirements"))
    _section("IQAC Suggestions", iqac.get("iqac_suggestions", []))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response


@login_required
def download_report_pdf(request, report_id: int):
    """Download a simplified PDF of a report by its id, for Review Center."""
    report = get_object_or_404(EventReport.objects.select_related("proposal"), id=report_id)
    proposal = report.proposal

    response = HttpResponse(content_type="application/pdf")
    safe_title = (proposal.event_title or f"report-{report_id}").replace("\n", " ")
    response["Content-Disposition"] = f'attachment; filename="{safe_title}_report.pdf"'

    from io import BytesIO
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    data = _build_report_initial_data(report)
    # Header
    p.setFont("Helvetica-Bold", 14)
    p.drawString(72, 800, "Event Report")
    p.setFont("Helvetica", 11)
    p.drawString(72, 782, f"Title: {data['event']['title']}")
    p.drawString(72, 766, f"Department: {data['event']['department']}")
    p.drawString(72, 750, f"Date: {data['event']['date']}")
    p.drawString(72, 734, f"Venue: {data['event']['venue']}")
    p.drawString(72, 718, f"Generated on: {timezone.now().strftime('%Y-%m-%d')}")

    # Narrative sections
    y = 700
    def _wrap(text: str, width=90):
        import textwrap
        return textwrap.wrap(text or "", width=width)

    def _draw_paragraph(label: str, text: str, yy: int) -> int:
        nonlocal p
        p.setFont("Helvetica-Bold", 11)
        p.drawString(72, yy, label)
        yy -= 14
        p.setFont("Helvetica", 10)
        for line in _wrap(text, 95):
            p.drawString(72, yy, line)
            yy -= 14
            if yy < 60:
                p.showPage(); yy = 800
        return yy - 8

    y = _draw_paragraph("Summary:", data["narrative"]["summary_overall_event"], y)
    y = _draw_paragraph("Outcomes:", "; ".join(data["narrative"]["outcomes"]), y)
    y = _draw_paragraph("Social Relevance:", "; ".join(data["narrative"]["social_relevance"]), y)
    y = _draw_paragraph("Impact on Attendees:", data["analysis"]["impact_attendees"], y)
    y = _draw_paragraph("Lessons Learned:", data["analysis"]["impact_volunteers"], y)

    # IQAC Suggestions
    suggestions = data["iqac"]["iqac_suggestions"]
    if suggestions:
        y = _draw_paragraph("IQAC Suggestions:", "; ".join(suggestions), y)
    p.showPage()
    p.save()

    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response


@login_required
def download_word(request, proposal_id):
    # TODO: Implement actual Word generation and return the file
    return HttpResponse(
        f"Word download for Proposal {proposal_id}",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


# ──────────────────────────────
# AUTOSAVE Need Analysis (if you use autosave)
# ──────────────────────────────
@csrf_exempt
@login_required
def autosave_need_analysis(request):
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        proposal_id = data.get("proposal_id")
        content = data.get("content", "")
        proposal = EventProposal.objects.get(id=proposal_id, submitted_by=request.user)
        na, created = EventNeedAnalysis.objects.get_or_create(proposal=proposal)
        na.content = content
        na.save()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False}, status=400)


@csrf_exempt
@login_required
def autosave_event_report(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    try:
        raw = request.body.decode("utf-8")
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        logger.debug("autosave_event_report invalid json: %s", raw)
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    # Preserve the original payload so we can persist it without being mutated
    # by the transformations that follow (e.g., flattening list fields).
    payload_snapshot = copy.deepcopy(data)

    proposal_id = data.get("proposal_id")
    report_id = data.get("report_id")

    proposal = EventProposal.objects.filter(id=proposal_id).first()
    if not proposal or not (
        proposal.submitted_by == request.user
        or request.user.has_perm("emt.change_eventreport")
    ):
        return JsonResponse({"success": False, "error": "Invalid proposal"}, status=400)

    report = None
    if report_id:
        report = EventReport.objects.filter(id=report_id, proposal=proposal).first()
    if not report:
        report, _ = EventReport.objects.get_or_create(proposal=proposal)

    # Map section fields to model fields
    summary_content = data.pop("event_summary", None)
    outcomes_content = data.pop("event_outcomes", None)
    analysis_content = data.pop("analysis", None)

    # Flatten any list values (e.g., multi-select fields) into comma-separated strings
    for key, value in list(data.items()):
        if isinstance(value, list):
            data[key] = ", ".join(value)

    form = EventReportForm(data, instance=report)
    # For autosave, allow partial payloads and do NOT overwrite unspecified fields
    for f in form.fields.values():
        f.required = False
    form.fields.get("report_signed_date").required = False
    if not form.is_valid():
        logger.debug("autosave_event_report form errors: %s", form.errors)
        return JsonResponse({"success": False, "errors": form.errors})

    # Apply only the submitted fields to the existing instance
    for name in form.fields.keys():
        if name in data:
            cleaned_value = form.cleaned_data.get(name)
            if name == "report_signed_date" and cleaned_value in (None, ""):
                # Leave the existing value intact when autosave payload omits a date.
                # The model field does not accept null values, so attempting to set
                # ``None`` triggers an integrity error which in turn breaks flows like
                # opening the attendance modal from a fresh report. Skipping assignment
                # preserves either the default or any previously saved date while still
                # allowing the client to update it once a real value is provided.
                continue
            try:
                setattr(report, name, cleaned_value)
            except Exception:
                pass
    if summary_content is not None:
        report.summary = summary_content
    if outcomes_content is not None:
        report.outcomes = outcomes_content
    if analysis_content is not None and hasattr(report, "analysis"):
        report.analysis = analysis_content
    if payload_snapshot:
        report.generated_payload = payload_snapshot
    report.save()

    _save_activities(proposal, data)

    return JsonResponse({"success": True, "report_id": report.id})


@login_required
@require_http_methods(["POST"])
def api_update_speaker(request, proposal_id, speaker_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id)
    if not (
        proposal.submitted_by == request.user
        or request.user.has_perm("emt.change_eventreport")
        or request.user.has_perm("emt.change_speakerprofile")
    ):
        return JsonResponse({"success": False, "error": "Forbidden"}, status=403)

    speaker = get_object_or_404(SpeakerProfile, id=speaker_id, proposal=proposal)

    content_type = request.content_type or ""
    if content_type.startswith("multipart/form-data") or content_type.startswith(
        "application/x-www-form-urlencoded"
    ):
        data = request.POST.copy()
        files = request.FILES
    else:
        try:
            raw = request.body.decode("utf-8")
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            logger.debug("api_update_speaker invalid json: %s", raw)
            return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
        files = None

    if hasattr(data, "copy"):
        data = data.copy()

    remove_flag = str(data.pop("remove_photo", "")).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    has_new_photo = bool(files and files.get("photo"))

    form = SpeakerProfileForm(data or None, files, instance=speaker)
    if not form.is_valid():
        return JsonResponse({"success": False, "errors": form.errors}, status=400)

    updated = form.save(commit=False)
    if remove_flag and not has_new_photo:
        if updated.photo:
            updated.photo.delete(save=False)
        updated.photo = None
    updated.save()

    return JsonResponse({"success": True, "speaker": _serialize_speaker(updated)})


@login_required
def api_organizations(request):
    q = request.GET.get("q", "").strip()
    org_type = request.GET.get(
        "org_type", ""
    ).strip()  # e.g., "Department", "Club", etc.
    exclude = [e for e in request.GET.get("exclude", "").split(",") if e.isdigit()]
    orgs = Organization.objects.filter(name__icontains=q, is_active=True)
    if org_type:
        orgs = orgs.filter(org_type__name=org_type)
    if exclude:
        orgs = orgs.exclude(id__in=exclude)
    orgs = orgs.order_by("name")[:20]
    return JsonResponse([{"id": o.id, "text": o.name} for o in orgs], safe=False)


@login_required
def api_faculty(request):
    q = request.GET.get("q", "").strip()
    org_id = request.GET.get("org_id")
    ids_param = request.GET.get("ids")

    users = User.objects.filter(role_assignments__role__name__icontains="faculty")
    if org_id:
        users = users.filter(role_assignments__organization_id=org_id)

    if ids_param:
        ids = [i for i in ids_param.split(",") if i.isdigit()]
        users = users.filter(id__in=ids)
    else:
        users = (
            users.prefetch_related("role_assignments__organization")
            .filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(email__icontains=q)
            )
            .distinct()
            .order_by("role_assignments__organization__name", "first_name")[:20]
        )

    data = []
    for u in users:
        assignment = (
            u.role_assignments.filter(
                role__name__icontains="faculty", organization__isnull=False
            )
            .select_related("organization")
            .first()
        )
        dept = assignment.organization.name if assignment else ""
        full_name = u.get_full_name() or u.username
        data.append(
            {
                "id": u.id,
                "name": full_name,
                "department": dept,
                "text": f"{full_name} ({u.email})",
            }
        )

    return JsonResponse(data, safe=False)


@login_required
@require_http_methods(["GET"])
def api_students(request):
    """Return users with a student membership matching the search query."""
    q = request.GET.get("q", "").strip()
    org_id = request.GET.get("org_id")
    org_ids = request.GET.get("org_ids")

    users = User.objects.filter(org_memberships__role="student")
    if org_ids:
        ids = [int(i) for i in org_ids.split(",") if i.strip().isdigit()]
        if ids:
            users = users.filter(org_memberships__organization_id__in=ids)
    elif org_id:
        users = users.filter(org_memberships__organization_id=org_id)

    if q:
        users = users.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
        )

    users = users.distinct().order_by("first_name")[:20]
    data = [{"id": u.id, "text": u.get_full_name() or u.username} for u in users]
    return JsonResponse(data, safe=False)


@login_required
@require_http_methods(["GET"])
def api_classes(request, org_id):
    """Return classes and their students for an organization."""
    q = request.GET.get("q", "").strip()

    try:
        classes = (
            Class.objects.filter(organization_id=org_id, is_active=True)
            .prefetch_related("students__user")
            .order_by("name")
        )
        if q:
            classes = classes.filter(name__icontains=q)
        data = []
        for cls in classes:
            students = [
                {
                    "id": s.user.id,
                    "name": s.user.get_full_name() or s.user.username,
                }
                for s in cls.students.all()
            ]
            data.append(
                {
                    "id": cls.id,
                    "name": cls.name,
                    "code": cls.code,
                    "students": students,
                }
            )
        return JsonResponse({"success": True, "classes": data})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def fetch_linkedin_profile(request):
    """Fetch and parse a public LinkedIn profile."""
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (TypeError, ValueError):
        data = {}
    url = data.get("url", "")
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    if ":" in netloc:
        netloc = netloc.split(":", 1)[0]
    if parsed.scheme not in ("http", "https") or not netloc.endswith("linkedin.com"):
        return JsonResponse({"error": "Invalid LinkedIn URL"}, status=400)
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; IQACSuite/1.0)"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception:
        return JsonResponse({"error": "Unable to fetch profile"}, status=500)
    profile = _parse_public_li(response.text)
    return JsonResponse(profile)


# Temporary safe parser stub (prevent NameError if real parser not implemented)
def _parse_public_li(html: str):  # pragma: no cover
    """Parse minimal data from a public LinkedIn profile page.

    Uses Open Graph meta tags available on public profiles to extract
    the name, headline/description, and profile image. Returns a
    dictionary suitable for JSON serialization. The parsing intentionally
    avoids any advanced scraping that would require authentication.
    """
    soup = BeautifulSoup(html or "", "html.parser")

    def _meta(prop):
        tag = soup.find("meta", property=prop)
        return tag.get("content", "").strip() if tag and tag.get("content") else ""

    name = _meta("og:title")
    description = _meta("og:description")
    image = _meta("og:image")

    designation = ""
    affiliation = ""
    if description:
        main_desc = description.split("|")[0].strip()
        if " at " in main_desc:
            designation, affiliation = [p.strip() for p in main_desc.split(" at ", 1)]
        else:
            designation = main_desc

    return {
        "headline": description or None,
        "name": name or None,
        "about": None,
        "image": image or None,
        "designation": designation or None,
        "affiliation": affiliation or None,
    }


@login_required
def api_outcomes(request, org_id):
    """Return Program Outcomes and Program Specific Outcomes for an organization."""
    from core.models import (Organization, Program, ProgramOutcome,
                             ProgramSpecificOutcome)

    try:
        org = Organization.objects.get(id=org_id)
    except Organization.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Organization not found"}, status=404
        )

    programs = Program.objects.filter(organization=org)
    pos = []
    psos = []
    if programs.exists():
        program = programs.first()
        pos = list(
            ProgramOutcome.objects.filter(program=program).values("id", "description")
        )
        psos = list(
            ProgramSpecificOutcome.objects.filter(program=program).values(
                "id", "description"
            )
        )

    return JsonResponse({"success": True, "pos": pos, "psos": psos})


@login_required
def my_approvals(request):
    pending_steps = (
        ApprovalStep.objects.filter(
            assigned_to=request.user,
            status=ApprovalStep.Status.PENDING,
        )
        .filter(Q(is_optional=False) | Q(optional_unlocked=True))
        .select_related("proposal")
        .order_by("order_index")
    )
    return render(request, "emt/my_approvals.html", {"pending_steps": pending_steps})


@login_required
@user_passes_test(
    lambda u: getattr(getattr(u, "profile", None), "role", "") != "student"
)
def review_approval_step(request, step_id):
    step = get_object_or_404(ApprovalStep, id=step_id)

    # Fetch the proposal along with all related details in one go.
    proposal = (
        EventProposal.objects.select_related(
            "need_analysis",
            "objectives",
            "expected_outcomes",
            "tentative_flow",
        )
        .prefetch_related(
            "speakers",
            "expense_details",
            "income_details",
            "faculty_incharges",
            "sdg_goals",
        )
        .get(pk=step.proposal_id)
    )

    # Fetch related sections gracefully; some proposals may not have
    # completed every part yet, so the related objects could be missing.
    try:
        need_analysis = proposal.need_analysis
    except EventNeedAnalysis.DoesNotExist:
        need_analysis = None

    try:
        objectives = proposal.objectives
    except EventObjectives.DoesNotExist:
        objectives = None

    try:
        outcomes = proposal.expected_outcomes
    except EventExpectedOutcomes.DoesNotExist:
        outcomes = None

    try:
        flow = proposal.tentative_flow
    except TentativeFlow.DoesNotExist:
        flow = None

    speakers = proposal.speakers.all()
    expenses = proposal.expense_details.all()
    income = proposal.income_details.all()
    logger.debug(
        "Reviewing proposal %s: faculty %s, objectives=%s, outcomes=%s, flow=%s",
        proposal.id,
        list(proposal.faculty_incharges.values_list("id", flat=True)),
        getattr(objectives, "content", None),
        getattr(outcomes, "content", None),
        getattr(flow, "content", None),
    )

    optional_candidates = []
    show_optional_picker = False
    if (
        step.assigned_to_id == request.user.id
        and step.status == ApprovalStep.Status.PENDING
    ):
        optional_candidates = list(get_downstream_optional_candidates(step))
        show_optional_picker = len(optional_candidates) > 0

    history_steps = proposal.approval_steps.visible_for_ui().order_by("order_index")

    if request.method == "POST":
        action = request.POST.get("action")
        comment = request.POST.get("comment", "")
        forward_flag = bool(request.POST.get("forward_to_optionals"))
        selected_optionals = request.POST.getlist("optional_step_ids")

        if action == "approve":
            step.status = ApprovalStep.Status.APPROVED
            step.approved_by = request.user
            step.approved_at = timezone.now()
            step.decided_by = request.user
            step.decided_at = step.approved_at
            step.comment = comment
            step.save()

            auto_approve_non_optional_duplicates(
                step.proposal, request.user, request.user
            )

            if forward_flag and selected_optionals:
                unlock_optionals_after(step, selected_optionals)
            else:
                skip_all_downstream_optionals(step)

            def activate_next(current_order):
                next_step = (
                    ApprovalStep.objects.filter(
                        proposal=proposal,
                        order_index__gt=current_order,
                    )
                    .order_by("order_index")
                    .first()
                )
                if not next_step:
                    return
                if next_step.status == "waiting":
                    next_step.status = "pending"
                    next_step.save()
                else:
                    activate_next(next_step.order_index)

            activate_next(step.order_index)

            if ApprovalStep.objects.filter(
                proposal=proposal, status="pending"
            ).exists():
                proposal.status = "under_review"
            else:
                proposal.status = "finalized"
            proposal.save()
            messages.success(request, "Proposal approved.")
            return redirect("emt:my_approvals")

        elif action == "reject":
            if not comment.strip():
                messages.error(request, "Comment is required to reject the proposal.")
            else:
                step.status = ApprovalStep.Status.REJECTED
                step.comment = comment
                step.approved_by = request.user
                step.approved_at = timezone.now()
                step.decided_by = request.user
                step.decided_at = step.approved_at
                proposal.status = "rejected"
                proposal.save()
                step.save()
                messages.error(request, "Proposal rejected.")
                return redirect("emt:my_approvals")
        else:
            return redirect("emt:my_approvals")

    return render(
        request,
        "emt/review_approval_step.html",
        {
            "step": step,
            "proposal": proposal,
            "need_analysis": need_analysis,
            "objectives": objectives,
            "outcomes": outcomes,
            "flow": flow,
            "speakers": speakers,
            "expenses": expenses,
            "income": income,
            "optional_candidates": optional_candidates,
            "show_optional_picker": show_optional_picker,
            "history_steps": history_steps,
        },
    )


@login_required
def submit_event_report(request, proposal_id):
    proposal = get_object_or_404(
        EventProposal,
        id=proposal_id,
        submitted_by=request.user,
    )

    report = EventReport.objects.filter(proposal=proposal).first()
    AttachmentFormSet = modelformset_factory(
        EventReportAttachment, form=EventReportAttachmentForm, extra=2, can_delete=True
    )

    drafts = request.session.setdefault("event_report_draft", {})
    draft = drafts.get(str(proposal_id), {})

    if request.method == "POST":
        trigger_ai = str(request.POST.get("generate_ai", "")).lower() in {
            "1",
            "true",
            "on",
            "yes",
        }
        drafts[str(proposal_id)] = {
            key: (
                request.POST.getlist(key)
                if len(request.POST.getlist(key)) > 1
                else request.POST.get(key)
            )
            for key in request.POST.keys()
            if key != "generate_ai"
        }
        request.session.modified = True

        post_data = request.POST.copy()
        # Map front-end field names to model fields
        if "event_summary" in post_data and "summary" not in post_data:
            post_data["summary"] = post_data.pop("event_summary")
        if "event_outcomes" in post_data and "outcomes" not in post_data:
            post_data["outcomes"] = post_data.pop("event_outcomes")

        form = EventReportForm(post_data, instance=report)
        attachments_qs = (
            report.attachments.all() if report else EventReportAttachment.objects.none()
        )
        formset = AttachmentFormSet(post_data, request.FILES, queryset=attachments_qs)
        if (
            form.is_valid()
            and formset.is_valid()
            and _save_activities(proposal, post_data, form)
        ):
            report = form.save(commit=False)
            report.proposal = proposal
            report.save()
            form.save_m2m()

            # Sync proposal snapshot fields based on final report edits
            _sync_proposal_from_report(proposal, report, post_data)

            instances = formset.save(commit=False)
            for obj in instances:
                obj.report = report
                obj.save()
            for obj in formset.deleted_objects:
                obj.delete()

            drafts.pop(str(proposal_id), None)
            request.session.modified = True

            if trigger_ai:
                messages.success(
                    request,
                    "Report submitted successfully! Starting AI generation...",
                )
                return redirect("emt:ai_report_progress", proposal_id=proposal.id)

            messages.success(
                request,
                "Report saved successfully. Review the preview before generating the AI report.",
            )
            return preview_event_report(request, proposal.id)
    else:
        form = EventReportForm(initial=draft, instance=report)
        attachments_qs = (
            report.attachments.all() if report else EventReportAttachment.objects.none()
        )
        formset = AttachmentFormSet(queryset=attachments_qs)

    activities_qs = EventActivity.objects.filter(proposal=proposal)
    proposal_activities = [
        {
            "activity_name": a.name,
            "activity_date": a.date.strftime("%Y-%m-%d") if a.date else "",
        }
        for a in activities_qs
    ]
    if draft:
        num_act = int(draft.get("num_activities", 0) or 0)
        session_acts = []
        for i in range(1, num_act + 1):
            session_acts.append(
                {
                    "activity_name": draft.get(f"activity_name_{i}", ""),
                    "activity_date": draft.get(f"activity_date_{i}", ""),
                }
            )
        if session_acts:
            proposal_activities = session_acts

    # Fetch speakers data for editing
    speakers_qs = SpeakerProfile.objects.filter(proposal=proposal)
    speakers_json = [_serialize_speaker(speaker) for speaker in speakers_qs]

    # Get or create content sections for the report
    event_summary = None
    if report and report.summary:
        event_summary = SimpleNamespace(content=report.summary)
    if draft.get("event_summary"):
        event_summary = SimpleNamespace(content=draft.get("event_summary"))

    event_outcomes = None
    if report and report.outcomes:
        event_outcomes = SimpleNamespace(content=report.outcomes)
    if draft.get("event_outcomes"):
        event_outcomes = SimpleNamespace(content=draft.get("event_outcomes"))

    analysis = None
    if report and report.analysis:
        analysis = SimpleNamespace(content=report.analysis)
    if draft.get("analysis"):
        analysis = SimpleNamespace(content=draft.get("analysis"))

    attendance_qs = (
        report.attendance_rows.all() if report else AttendanceRow.objects.none()
    )
    attendance_present = attendance_qs.filter(absent=False).count()
    attendance_absent = attendance_qs.filter(absent=True).count()
    attendance_volunteers = attendance_qs.filter(volunteer=True).count()
    volunteer_names = list(
        attendance_qs.filter(volunteer=True).values_list("full_name", flat=True)
    )
    faculty_names = [
        f.get_full_name() or f.username for f in proposal.faculty_incharges.all()
    ]

    def _normalise_numeric(value):
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return value

    def _field_value(field_name):
        return _normalise_numeric(form[field_name].value()) if form else None

    form_total = _field_value("num_participants")
    if form_total is not None:
        total_count = form_total
    elif report and report.num_participants is not None:
        total_count = report.num_participants
    else:
        total_count = _normalise_numeric(attendance_present)

    form_volunteers = _field_value("num_student_volunteers")
    if form_volunteers is not None:
        volunteers_count = form_volunteers
    elif report and report.num_student_volunteers is not None:
        volunteers_count = report.num_student_volunteers
    else:
        volunteers_count = _normalise_numeric(attendance_volunteers)

    form_students = _field_value("num_student_participants")
    if form_students is not None:
        student_count = form_students
    elif report and report.num_student_participants is not None:
        student_count = report.num_student_participants
    else:
        student_count = None

    form_faculty = _field_value("num_faculty_participants")
    if form_faculty is not None:
        faculty_count = form_faculty
    elif report and report.num_faculty_participants is not None:
        faculty_count = report.num_faculty_participants
    else:
        faculty_count = None

    form_external = _field_value("num_external_participants")
    if form_external is not None:
        external_count = form_external
    elif report and report.num_external_participants is not None:
        external_count = report.num_external_participants
    else:
        external_count = None

    attendance_counts = {
        "present": _normalise_numeric(attendance_present),
        "absent": _normalise_numeric(attendance_absent),
        "volunteers": volunteers_count,
        "total": total_count,
        "students": student_count,
        "faculty": faculty_count,
        "external": external_count,
    }

    generated_payload = (
        report.generated_payload
        if report and isinstance(report.generated_payload, dict)
        else {}
    )

    def _coalesce_prefill(key, *fallbacks):
        """Return the first meaningful value for a report field.

        Preference order:
        1. Session draft (captures the latest POST even if validation failed)
        2. Bound form data (covers immediate re-renders on validation errors)
        3. Autosaved payload stored on the report instance
        4. Explicit fallbacks passed by the caller (e.g., report/proposal fields)
        """

        def _normalise_candidate(value):
            if isinstance(value, (list, tuple)):
                return value[0] if value else ""
            return value

        candidates = []

        if draft:
            draft_value = _normalise_candidate(draft.get(key))
            if draft_value is not None:
                candidates.append(draft_value)

        if form and hasattr(form, "data") and key in form.data:
            form_value = _normalise_candidate(form.data.get(key))
            if form_value is not None:
                candidates.append(form_value)

        if generated_payload:
            payload_value = _normalise_candidate(generated_payload.get(key))
            if payload_value is not None:
                candidates.append(payload_value)

        candidates.extend(fallbacks)

        for candidate in candidates:
            if candidate is None:
                continue
            if isinstance(candidate, str):
                stripped = candidate.strip()
                if stripped:
                    return stripped
                if candidate == "":
                    return ""
                continue
            if isinstance(candidate, (int, float)):
                return str(candidate)
            return str(candidate)

        return ""

    prefill_venue = _coalesce_prefill("venue", getattr(proposal, "venue", ""))
    prefill_location = _coalesce_prefill(
        "location",
        getattr(report, "location", None),
        getattr(proposal, "venue", ""),
    )
    prefill_event_type = _coalesce_prefill(
        "actual_event_type",
        getattr(report, "actual_event_type", None),
        getattr(proposal, "event_focus_type", ""),
    )

    # Prepare SDG goal data for modal and proposal prefill
    sdg_goals_list = [
        {"id": goal.id, "title": goal.name} for goal in SDGGoal.objects.all()
    ]
    proposal_sdg_goals = ", ".join(
        f"SDG{goal.id}: {goal.name}" for goal in proposal.sdg_goals.all()
    )

    # Pre-fill context with proposal info for readonly/preview display
    context = {
        "proposal": proposal,
        "form": form,
        "formset": formset,
        "proposal_activities": proposal_activities,
        "proposal_activities_json": json.dumps(proposal_activities),
        "speakers_json": json.dumps(speakers_json),
        "sdg_goals_list": sdg_goals_list,
        "proposal_sdg_goals": proposal_sdg_goals,
        "event_summary": event_summary,
        "event_outcomes": event_outcomes,
        "analysis": analysis,
        "report": report,
        "attendance_present": attendance_present,
        "attendance_absent": attendance_absent,
        "attendance_volunteers": attendance_volunteers,
        "attendance_counts": attendance_counts,
        "attendance_counts_json": json.dumps(attendance_counts),
        "faculty_names_json": json.dumps(faculty_names),
        "volunteer_names_json": json.dumps(volunteer_names),
        "prefill_venue": prefill_venue,
        "prefill_location": prefill_location,
        "prefill_event_type": prefill_event_type,
    }
    context["can_autosave"] = (
        proposal.submitted_by == request.user
        or request.user.has_perm("emt.change_eventreport")
    )
    return render(request, "emt/submit_event_report.html", context)


@login_required
def preview_event_report(request, proposal_id):
    """Display a summary of the event report before final submission."""
    proposal = get_object_or_404(
        EventProposal,
        id=proposal_id,
        submitted_by=request.user,
    )

    if request.method != "POST":
        return redirect("emt:submit_event_report", proposal_id=proposal.id)

    post_data = request.POST.copy()
    show_iqac_flag = str(post_data.get("show_iqac", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if "show_iqac" in post_data:
        post_data.pop("show_iqac")
    report = EventReport.objects.filter(proposal=proposal).first()

    def _coerce_date(value):
        if not value:
            return None
        parsed = parse_date(value)
        return parsed or value

    def _display_date(value):
        if not value:
            return None
        if hasattr(value, "isoformat"):
            try:
                return date_format(value, "DATE_FORMAT")
            except Exception:  # pragma: no cover - fallback for unexpected types
                return str(value)
        parsed = parse_date(value) if isinstance(value, str) else None
        if parsed:
            return date_format(parsed, "DATE_FORMAT")
        return value

    def _format_display(value):
        """Normalise values for preview output, collapsing blanks to em dash."""

        if isinstance(value, str):
            value = value.strip()
            return value or "—"

        if isinstance(value, (list, tuple, set)):
            parts = []
            for item in value:
                if isinstance(item, str):
                    item = item.strip()
                if item in (None, ""):
                    continue
                parts.append(str(item))
            return ", ".join(parts) if parts else "—"

        if value in (None, ""):
            return "—"

        return str(value)

    # Update proposal snapshot values with any edits coming from the report form so
    # that the preview reflects the latest user-provided data instead of the
    # original submission only.
    updated_title = (post_data.get("event_title") or "").strip()
    if updated_title:
        proposal.event_title = updated_title

    updated_venue = (post_data.get("venue") or post_data.get("venue_detail") or "").strip()
    if updated_venue:
        proposal.venue = updated_venue

    start_value = _coerce_date(post_data.get("event_start_date"))
    if start_value:
        proposal.event_start_date = start_value

    end_value = _coerce_date(post_data.get("event_end_date"))
    if end_value:
        proposal.event_end_date = end_value

    academic_year_override = (post_data.get("academic_year") or "").strip()
    if academic_year_override:
        proposal.academic_year = academic_year_override

    # Front-end uses event_summary/event_outcomes; map them to model fields
    if "event_summary" in post_data and "summary" not in post_data:
        post_data["summary"] = post_data.pop("event_summary")
    if "event_outcomes" in post_data and "outcomes" not in post_data:
        post_data["outcomes"] = post_data.pop("event_outcomes")

    form = EventReportForm(post_data)
    form_is_valid = form.is_valid()
    if not form_is_valid:
        logger.debug(
            "Preview form invalid for proposal %s: %s", proposal.id, form.errors
        )

    # Prepare proposal fields for display in preview
    proposal_form = EventProposalForm(instance=proposal)
    proposal_fields = []
    # Exclude finance-only fields that are not part of the current submit_proposal UI
    excluded_proposal_fields = {
        "fest_fee_participants",
        "fest_fee_rate",
        "fest_fee_amount",
        "fest_sponsorship_amount",
        "conf_fee_participants",
        "conf_fee_rate",
        "conf_fee_amount",
        "conf_sponsorship_amount",
    }
    for name, field in proposal_form.fields.items():
        if name in excluded_proposal_fields:
            continue
        bound_field = proposal_form[name]
        raw_value = bound_field.value()
        field_def = bound_field.field
        if isinstance(field_def, forms.ModelMultipleChoiceField):
            objs = []
            if raw_value:
                if field_def.queryset.exists():
                    objs = list(field_def.queryset.filter(pk__in=raw_value))
                if not objs and hasattr(proposal, name):
                    objs = list(getattr(proposal, name).all())
            elif hasattr(proposal, name):
                objs = list(getattr(proposal, name).all())
            display = ", ".join(str(obj) for obj in objs) or "—"
        elif isinstance(field_def, forms.ModelChoiceField):
            obj = None
            if raw_value:
                if field_def.queryset.exists():
                    obj = field_def.queryset.filter(pk=raw_value).first()
                if not obj and hasattr(proposal, name):
                    obj = getattr(proposal, name)
            elif hasattr(proposal, name):
                obj = getattr(proposal, name)
            display = str(obj) if obj else "—"
        else:
            display = raw_value or "—"
        proposal_fields.append((bound_field.label, display))

    # Add related proposal data not covered by EventProposalForm
    need = getattr(proposal, "need_analysis", None)
    proposal_fields.append(
        (
            'Rationale / "Why is this event necessary?"',
            getattr(need, "content", "") or "—",
        )
    )
    objectives = getattr(proposal, "objectives", None)
    proposal_fields.append(("Objectives", getattr(objectives, "content", "") or "—"))
    outcomes = getattr(proposal, "expected_outcomes", None)
    proposal_fields.append(
        (
            "Expected Learning Outcomes",
            getattr(outcomes, "content", "") or "—",
        )
    )

    flow = getattr(proposal, "tentative_flow", None)
    if flow and flow.content:
        lines = [line.strip() for line in flow.content.splitlines() if line.strip()]
        for idx, line in enumerate(lines, 1):
            try:
                dt_str, activity = line.split("||", 1)
            except ValueError:
                dt_str, activity = line, ""
            proposal_fields.append(
                (f"Schedule Item {idx} - Date & Time", dt_str.strip())
            )
            proposal_fields.append(
                (f"Schedule Item {idx} - Activity", activity.strip())
            )

    # Include planned activities captured as structured rows on the proposal
    planned_activities = list(proposal.activities.all().order_by("date", "id"))
    for idx, act in enumerate(planned_activities, 1):
        proposal_fields.append((f"Planned Activity {idx} - Name", act.name or "—"))
        proposal_fields.append(
            (f"Planned Activity {idx} - Date", getattr(act, "date", "") or "—")
        )

    for idx, speaker in enumerate(proposal.speakers.all(), 1):
        proposal_fields.extend(
            [
                (f"Speaker {idx}: Full Name", speaker.full_name or "—"),
                (f"Speaker {idx}: Designation", speaker.designation or "—"),
                (f"Speaker {idx}: Organization", speaker.affiliation or "—"),
                (f"Speaker {idx}: Email", speaker.contact_email or "—"),
                (f"Speaker {idx}: Contact Number", speaker.contact_number or "—"),
                (
                    f"Speaker {idx}: LinkedIn Profile",
                    speaker.linkedin_url or "—",
                ),
                (
                    f"Speaker {idx}: Photo",
                    speaker.photo.url if speaker.photo else "—",
                ),
                (f"Speaker {idx}: Bio", speaker.detailed_profile or "—"),
            ]
        )

    for idx, expense in enumerate(proposal.expense_details.all(), 1):
        proposal_fields.extend(
            [
                (f"Expense Item {idx}: SL No", getattr(expense, "sl_no", "") or "—"),
                (f"Expense Item {idx}: Particulars", expense.particulars or "—"),
                (f"Expense Item {idx}: Amount", expense.amount or "—"),
            ]
        )

    for idx, income in enumerate(proposal.income_details.all(), 1):
        proposal_fields.extend(
            [
                (f"Income Item {idx}: Item", income.sl_no or "—"),
                (f"Income Item {idx}: Particulars", income.particulars or "—"),
                (
                    f"Income Item {idx}: No. of Participants",
                    income.participants or "—",
                ),
                (f"Income Item {idx}: Rate", income.rate or "—"),
                (f"Income Item {idx}: Amount", income.amount or "—"),
            ]
        )

    support = getattr(proposal, "cdl_support", None)
    if support and getattr(support, "needs_support", False):
        other_service_labels = dict(
            CDLSupportForm.base_fields["other_services"].choices
        )

        def _append_cdl(label, value, *, is_date=False):
            if is_date:
                value = _display_date(value)
            proposal_fields.append((label, _format_display(value)))

        if support.poster_required:
            _append_cdl("Poster Choice", support.get_poster_choice_display())
            _append_cdl("Organization Name", support.organization_name)
            _append_cdl("Event Time", support.poster_time)
            _append_cdl("Event Date", support.poster_date, is_date=True)
            _append_cdl("Event Venue", support.poster_venue)
            _append_cdl("Resource Person Name", support.resource_person_name)
            _append_cdl(
                "Resource Person Designation", support.resource_person_designation
            )
            _append_cdl("Event Title for Poster", support.poster_event_title)
            _append_cdl("Event Summary", support.poster_summary)
            _append_cdl("Design Link/Reference", support.poster_design_link)

        if support.certificates_required and support.certificate_help:
            _append_cdl(
                "Certificate Choice", support.get_certificate_choice_display()
            )
            _append_cdl(
                "Design Link/Reference", support.certificate_design_link
            )

        services = [
            other_service_labels.get(item, item)
            for item in (support.other_services or [])
            if item not in (None, "")
        ]
        _append_cdl("Additional Services", services)
        _append_cdl("Blog Content", support.blog_content)

    # Prepare report form fields for preview
    report_fields = []

    manual_report_fields = [
        ("Department", (post_data.get("department") or getattr(proposal.organization, "name", "")).strip()),
        ("Event Title", proposal.event_title),
        ("Venue", proposal.venue),
        ("Event Start Date", _display_date(start_value or proposal.event_start_date)),
        ("Event End Date", _display_date(end_value or proposal.event_end_date)),
        ("Academic Year", proposal.academic_year),
    ]

    for label, raw in manual_report_fields:
        report_fields.append((label, _format_display(raw)))

    for name, field in form.fields.items():
        values = post_data.getlist(name)
        if name == "report_signed_date":
            display_value = None
            for raw in values:
                if isinstance(raw, str):
                    raw = raw.strip()
                if raw:
                    display_value = _display_date(raw)
                    break
            report_fields.append((field.label, _format_display(display_value)))
            continue

        cleaned_values = []
        for raw in values:
            if isinstance(raw, str):
                raw = raw.strip()
            if raw in (None, ""):
                continue
            cleaned_values.append(raw)

        if not cleaned_values:
            display = "—"
        elif len(cleaned_values) == 1:
            display = _format_display(cleaned_values[0])
        else:
            display = _format_display(cleaned_values)
        report_fields.append((field.label, display))

    # Include dynamic activities submitted with the report
    import re as _re

    idx_pattern = _re.compile(r"^activity_(?:name|date)_(\d+)$")
    indices = sorted(
        {int(m.group(1)) for key in post_data.keys() if (m := idx_pattern.match(key))}
    )
    for idx in indices:
        a_name = post_data.get(f"activity_name_{idx}")
        a_date = post_data.get(f"activity_date_{idx}")
        if a_name or a_date:
            report_fields.append((f"Activity {idx} - Name", a_name or "—"))
            report_fields.append((f"Activity {idx} - Date", a_date or "—"))

    num_activities = post_data.get("num_activities")
    if num_activities:
        report_fields.append(
            ("Number of Activities Conducted", _format_display(num_activities))
        )

    # Include dynamic organizing committee details captured on the participants section
    committee_names = post_data.getlist("committee_member_names[]")
    committee_roles = post_data.getlist("committee_member_roles[]")
    committee_departments = post_data.getlist("committee_member_departments[]")
    committee_contacts = post_data.getlist("committee_member_contacts[]")

    def _combine(values, idx):
        try:
            return values[idx]
        except IndexError:
            return None

    for idx in range(
        max(
            len(committee_names),
            len(committee_roles),
            len(committee_departments),
            len(committee_contacts),
        )
    ):
        name = (committee_names[idx] if idx < len(committee_names) else "") or ""
        role = _combine(committee_roles, idx)
        dept = _combine(committee_departments, idx)
        contact = _combine(committee_contacts, idx)
        if not any([name, role, dept, contact]):
            continue

        label_prefix = f"Committee Member {idx + 1}"
        report_fields.extend(
            [
                (f"{label_prefix} - Name", _format_display(name)),
                (f"{label_prefix} - Role", _format_display(role)),
                (
                    f"{label_prefix} - Department/Organization",
                    _format_display(dept),
                ),
                (f"{label_prefix} - Contact", _format_display(contact)),
            ]
        )

    # Include per-speaker session details captured in the participants section
    speaker_topics = post_data.getlist("speaker_topics[]")
    speaker_durations = post_data.getlist("speaker_durations[]")
    speaker_feedback = post_data.getlist("speaker_feedback[]")
    speaker_ids = post_data.getlist("speaker_ids[]")

    speaker_lookup = {
        str(speaker.id): speaker for speaker in proposal.speakers.all()
    }

    for idx in range(
        max(
            len(speaker_topics),
            len(speaker_durations),
            len(speaker_feedback),
            len(speaker_ids),
        )
    ):
        topic = _combine(speaker_topics, idx)
        duration = _combine(speaker_durations, idx)
        feedback = _combine(speaker_feedback, idx)
        speaker_id = _combine(speaker_ids, idx)

        if not any([topic, duration, feedback, speaker_id]):
            continue

        label_prefix = f"Speaker Session {idx + 1}"
        display_values = []

        if speaker_id:
            speaker_obj = speaker_lookup.get(str(speaker_id))
            speaker_name = getattr(speaker_obj, "full_name", None) if speaker_obj else None
            display_values.append(
                (
                    f"{label_prefix} - Speaker",
                    _format_display(speaker_name or speaker_id),
                )
            )

        display_values.extend(
            [
                (f"{label_prefix} - Topic", _format_display(topic)),
                (
                    f"{label_prefix} - Duration (minutes)",
                    _format_display(duration),
                ),
                (
                    f"{label_prefix} - Feedback/Comments",
                    _format_display(feedback),
                ),
            ]
        )

        report_fields.extend(display_values)

    def _is_blank(value):
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ""
        if isinstance(value, (list, tuple, set)):
            return all(_is_blank(item) for item in value)
        if isinstance(value, dict):
            return all(_is_blank(item) for item in value.values())
        return False

    def _text(value):
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (int, float)):
            return str(value)
        if hasattr(value, "isoformat"):
            try:
                return date_format(value, "DATE_FORMAT")
            except Exception:  # pragma: no cover - fallback for unexpected types
                return str(value)
        return str(value)

    def _listify(value):
        if not value and value != 0:
            return []
        if isinstance(value, (list, tuple, set)):
            items = []
            for entry in value:
                cleaned = _text(entry)
                if cleaned:
                    items.append(cleaned)
            return items
        text = _text(value)
        if not text:
            return []
        raw_items = re.split(r"[\r\n;,]+", text)
        cleaned = []
        for item in raw_items:
            stripped = re.sub(r"^[\-*•\u2022]+\s*", "", item.strip())
            if stripped:
                cleaned.append(stripped)
        return cleaned

    def _first_value(*values, default=""):
        for entry in values:
            if not _is_blank(entry):
                return entry
        return default

    def _committee_members():
        names = [n.strip() for n in post_data.getlist("committee_member_names[]") if isinstance(n, str)]
        roles = [r.strip() for r in post_data.getlist("committee_member_roles[]") if isinstance(r, str)]
        depts = [d.strip() for d in post_data.getlist("committee_member_departments[]") if isinstance(d, str)]
        contacts = [c.strip() for c in post_data.getlist("committee_member_contacts[]") if isinstance(c, str)]
        max_len = max(len(names), len(roles), len(depts), len(contacts))
        entries: list[str] = []
        for idx in range(max_len):
            name = names[idx] if idx < len(names) else ""
            role = roles[idx] if idx < len(roles) else ""
            dept = depts[idx] if idx < len(depts) else ""
            contact = contacts[idx] if idx < len(contacts) else ""
            if not any([name, role, dept, contact]):
                continue
            details = [part for part in [role, dept, contact] if part]
            if name and details:
                entries.append(f"{name} – {', '.join(details)}")
            elif name:
                entries.append(name)
            elif details:
                entries.append(", ".join(details))
        if entries:
            return entries
        fallback = _first_value(
            post_data.get("organizing_committee"),
            getattr(report, "organizing_committee", None),
        )
        return _listify(fallback)

    def _format_chip(value):
        text = _text(value)
        if not text:
            return ""
        return text.replace("_", " ").replace("-", " ").title()

    def _bool_from_post(key):
        raw = post_data.get(key)
        if raw is None:
            return False
        if isinstance(raw, str):
            return raw.strip().lower() in {"1", "true", "yes", "on", "checked"}
        return bool(raw)

    department_value = _text(
        _first_value(post_data.get("department"), getattr(proposal.organization, "name", None))
    )
    location_value = _text(
        _first_value(post_data.get("location"), getattr(report, "location", None), proposal.venue)
    )
    num_activities_value = _text(_first_value(post_data.get("num_activities"), proposal.num_activities))

    start_display = _text(_display_date(proposal.event_start_date))
    end_display = _text(_display_date(proposal.event_end_date))
    if start_display and end_display:
        event_date_value = start_display if start_display == end_display else f"{start_display} – {end_display}"
    elif start_display:
        event_date_value = start_display
    elif end_display:
        event_date_value = end_display
    else:
        event_date_value = ""
        if getattr(proposal, "event_datetime", None):
            try:
                event_date_value = date_format(proposal.event_datetime, "DATETIME_FORMAT")
            except Exception:  # pragma: no cover - fallback for unexpected types
                event_date_value = str(proposal.event_datetime)
        if not event_date_value:
            event_date_value = _text(_display_date(post_data.get("event_start_date")))

    academic_year_value = _text(
        _first_value(post_data.get("academic_year"), proposal.academic_year)
    )
    event_type_value = _text(
        _first_value(post_data.get("actual_event_type"), proposal.event_focus_type)
    )
    blog_link_value = _text(
        _first_value(post_data.get("blog_link"), getattr(report, "blog_link", None))
    )

    target_audience_value = _text(
        _first_value(post_data.get("target_audience"), proposal.target_audience)
    )
    external_agencies_value = _text(
        _first_value(post_data.get("actual_speakers"), getattr(report, "actual_speakers", None))
    )
    external_contacts_value = _text(
        _first_value(
            post_data.get("external_contact_details"),
            getattr(report, "external_contact_details", None),
        )
    )
    committee_entries = _committee_members()
    student_volunteers_value = _text(
        _first_value(
            post_data.get("num_student_volunteers"),
            getattr(report, "num_student_volunteers", None),
        )
    )
    attendees_count_value = _text(
        _first_value(post_data.get("num_participants"), getattr(report, "num_participants", None))
    )

    summary_value = _text(
        _first_value(post_data.get("summary"), getattr(report, "summary", None))
    )
    social_relevance_list = _listify(
        _first_value(post_data.get("impact_assessment"), getattr(report, "impact_assessment", None))
    )
    outcomes_list = _listify(
        _first_value(post_data.get("outcomes"), getattr(report, "outcomes", None))
    )

    analysis_attendees_value = _text(
        _first_value(
            post_data.get("impact_on_stakeholders"),
            getattr(report, "impact_on_stakeholders", None),
        )
    )
    analysis_schools_value = _text(
        _first_value(post_data.get("analysis"), getattr(report, "analysis", None))
    )
    analysis_volunteers_value = _text(
        _first_value(post_data.get("lessons_learned"), getattr(report, "lessons_learned", None))
    )

    mapping_pos_value = _text(
        _first_value(
            post_data.get("pos_pso_mapping"),
            getattr(report, "pos_pso_mapping", None),
            proposal.pos_pso,
        )
    )
    mapping_grad_value = _text(
        _first_value(
            post_data.get("needs_grad_attr_mapping"),
            getattr(report, "needs_grad_attr_mapping", None),
        )
    )
    mapping_contemporary_value = _text(
        _first_value(
            post_data.get("contemporary_requirements"),
            getattr(report, "contemporary_requirements", None),
        )
    )
    mapping_value_systems_value = _text(
        _first_value(
            post_data.get("sdg_value_systems_mapping"),
            getattr(report, "sdg_value_systems_mapping", None),
        )
    )
    sdg_goal_numbers = [
        f"SDG {goal.id}: {goal.name}"
        for goal in proposal.sdg_goals.all().order_by("id")
    ]

    naac_tags = [
        formatted
        for formatted in (_format_chip(value) for value in post_data.getlist("graduate_attributes"))
        if formatted
    ]

    iqac_suggestions = _listify(
        _first_value(post_data.get("iqac_feedback"), getattr(report, "iqac_feedback", None))
    )
    review_date_value = _first_value(
        post_data.get("report_signed_date"), getattr(report, "report_signed_date", None)
    )
    iqac_review_date_value = _text(_display_date(review_date_value)) if review_date_value else ""

    head_name = ""
    if proposal.submitted_by_id:
        head_name = proposal.submitted_by.get_full_name() or proposal.submitted_by.username
    faculty_names = [
        user.get_full_name() or user.username
        for user in proposal.faculty_incharges.all().order_by("id")
    ]
    faculty_signature = ", ".join(name for name in faculty_names if name)

    checklist_keys = [
        "facing_sheet_present",
        "summary_outcomes_sheet_present",
        "suggestions_sheet_present",
        "department_seal_sign_each_page",
        "detailed_report_or_blog_printout_present",
        "participant_list_present",
        "feedback_forms_present",
        "photos_present",
    ]
    attachments_checklist = {key: _bool_from_post(key) for key in checklist_keys}

    annexure_photos = []
    if report:
        for attachment in report.attachments.all():
            file_field = getattr(attachment, "file", None)
            if not file_field:
                continue
            try:
                file_url = file_field.url
            except ValueError:
                continue
            if not file_url:
                continue
            lower_url = file_url.lower()
            if not lower_url.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                continue
            annexure_photos.append(
                {
                    "src": file_url,
                    "caption": _text(attachment.caption),
                }
            )

    initial_data = {
        "event": {
            "title": _text(proposal.event_title),
            "department": department_value,
            "location": location_value,
            "no_of_activities": num_activities_value,
            "date": event_date_value,
            "venue": _text(proposal.venue),
            "academic_year": academic_year_value,
            "event_type_focus": event_type_value,
            "blog_link": blog_link_value,
        },
        "participants": {
            "target_audience": target_audience_value,
            "external_agencies_speakers": external_agencies_value,
            "external_contacts": external_contacts_value,
            "organising_committee": {
                "event_coordinators": committee_entries,
                "student_volunteers_count": student_volunteers_value,
            },
            "attendees_count": attendees_count_value,
        },
        "narrative": {
            "summary_overall_event": summary_value,
            "social_relevance": social_relevance_list,
            "outcomes": outcomes_list,
        },
        "analysis": {
            "impact_attendees": analysis_attendees_value,
            "impact_schools": analysis_schools_value,
            "impact_volunteers": analysis_volunteers_value,
        },
        "mapping": {
            "pos_psos": mapping_pos_value,
            "graduate_attributes_or_needs": mapping_grad_value,
            "contemporary_requirements": mapping_contemporary_value,
            "value_systems": mapping_value_systems_value,
            "sdg_goal_numbers": sdg_goal_numbers,
            "courses": [],
        },
        "metrics": {
            "naac_tags": naac_tags,
        },
        "iqac": {
            "iqac_suggestions": iqac_suggestions,
            "iqac_review_date": iqac_review_date_value,
            "sign_head_coordinator": _text(head_name),
            "sign_faculty_coordinator": _text(faculty_signature),
            "sign_iqac": "",
        },
        "attachments": {
            "checklist": attachments_checklist,
        },
        "annexures": {
            "photos": annexure_photos,
            "brochure_pages": [],
            "communication": {
                "subject": "",
                "date": "",
                "volunteers": [],
            },
            "worksheets": [],
            "evaluation_sheet": None,
            "feedback_form": None,
        },
    }

    post_data_items = list(post_data.lists())

    context = {
        "proposal": proposal,
        "report": report,
        "post_data": post_data,
        "post_data_items": post_data_items,
        "proposal_fields": proposal_fields,
        "report_fields": report_fields,
        "form": form,
        "form_is_valid": form_is_valid,
        "initial_report_data": json.dumps(initial_data, ensure_ascii=False),
        "ai_report_url": reverse("emt:ai_generate_report", args=[proposal.id]),
        "show_iqac": show_iqac_flag,
    }
    template_name = (
        "emt/iqac_report_preview.html"
        if show_iqac_flag
        else "emt/report_preview.html"
    )
    return render(request, template_name, context)


@login_required
@xframe_options_sameorigin
def review_full_report(request, report_id: int):
    """Render a full-page readonly IQAC preview for reviewers using persisted data.

    This lets reviewers see the complete two-page style report and, at the end,
    provide mandatory feedback to approve/reject. It reuses the iqac_report_preview
    template by passing initial_report_data assembled from saved Proposal/EventReport.
    """
    # Gate access: Only reviewers/admins can view full review page
    stage = _user_role_stage(request)
    admin_override = _is_admin_override(request.user)
    if not admin_override and stage == EventReport.ReviewStage.USER:
        return HttpResponse(status=403)

    report = get_object_or_404(EventReport.objects.select_related("proposal", "proposal__organization"), id=report_id)
    proposal = report.proposal

    initial_data = _build_report_initial_data(report)

    context = {
        "proposal": proposal,
        "report": report,
        "initial_report_data": json.dumps(initial_data, ensure_ascii=False),
        # Enable a footer form in template for approve/reject when linked from Review Center
        "review_action_url": reverse("emt:review_action"),
        "show_iqac": True,
        "review_mode": True,
        "generated_on": timezone.localdate(),
    }
    # Default to IQAC print-style view; allow switching to simplified view via ?style=simple
    template = "emt/iqac_report_preview.html"
    if request.GET.get("style") == "simple":
        template = "emt/review_simple_report.html"
    return render(request, template, context)


@login_required
def download_audience_csv(request, proposal_id):
    """Provide CSV templates for marking attendance separately for students and faculty."""
    proposal = get_object_or_404(
        EventProposal, id=proposal_id, submitted_by=request.user
    )

    audience_type = request.GET.get("type", "students").lower()
    names = [n.strip() for n in proposal.target_audience.split(",") if n.strip()]

    response = HttpResponse(content_type="text/csv")
    if audience_type == "faculty":
        filename = f"faculty_audience_{proposal_id}.csv"
        headers = [
            "Employee No",
            "Full Name",
            "Department",
            "Absent",
            "Student Volunteer",
        ]
    else:
        filename = f"student_audience_{proposal_id}.csv"
        headers = [
            "Registration No",
            "Full Name",
            "Class",
            "Absent",
            "Student Volunteer",
        ]
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(headers)

    if audience_type == "faculty":
        # Faculty template remains a simple blank form
        for name in names:
            writer.writerow(["", name, "", "", ""])
    else:
        # Pre-fill student registration numbers and classes when available
        students = {
            (s.user.get_full_name() or s.user.username).strip().lower(): s
            for s in Student.objects.select_related("user")
        }
        for name in names:
            reg_no = ""
            class_name = ""
            student = students.get(name.lower())
            if student:
                reg_no = student.registration_number or getattr(
                    getattr(student.user, "profile", None), "register_no", ""
                )
                cls = student.classes.filter(is_active=True).first()
                if cls:
                    class_name = cls.code or cls.name
            writer.writerow([reg_no, name, class_name, "", ""])

    logger.info("Generated %s audience CSV for proposal %s", audience_type, proposal_id)
    return response


def _group_attendance_rows(rows):
    """Categorise rows for students, faculty and guests while grouping them."""

    def _normalise_identifier(value: str) -> str:
        return re.sub(r"\s+", "", (value or "").strip()).lower()

    reg_nos = [
        (r.get("registration_no") or "").strip()
        for r in rows
        if r.get("registration_no")
    ]

    student_map = {
        s.registration_number: s
        for s in Student.objects.filter(registration_number__in=reg_nos)
    }

    faculty_memberships: dict[str, dict[str, str]] = {}

    def _register_membership(member: OrganizationMembership) -> dict[str, str]:
        organization_name = member.organization.name if member.organization else ""
        organization_name = (organization_name or "").strip()
        display_name = member.user.get_full_name() or member.user.username or ""
        display_name = display_name.strip()
        normalized_display = _normalise_identifier(display_name)
        membership_data = {
            "organization": organization_name,
            "display_name": display_name,
            "normalized_display": normalized_display,
        }
        username = (member.user.username or "").strip()
        if username:
            faculty_memberships[username] = membership_data
        profile_reg_no = getattr(
            getattr(member.user, "profile", None), "register_no", ""
        )
        profile_reg_no = (profile_reg_no or "").strip()
        if profile_reg_no:
            faculty_memberships[profile_reg_no] = membership_data
        if normalized_display:
            faculty_memberships.setdefault(normalized_display, membership_data)
        return membership_data

    memberships = list(
        OrganizationMembership.objects.filter(
            Q(user__username__in=reg_nos) | Q(user__profile__register_no__in=reg_nos),
            role="faculty",
        ).select_related("organization", "user__profile")
    )

    processed_membership_ids: set[int] = set()
    for membership in memberships:
        processed_membership_ids.add(membership.pk)
        _register_membership(membership)

    missing_name_identifiers = {
        _normalise_identifier((row.get("full_name") or ""))
        for row in rows
        if not (row.get("registration_no") or "").strip()
        and (row.get("full_name") or "").strip()
    }
    missing_name_identifiers.discard("")
    existing_normalized_keys = {
        data.get("normalized_display")
        for data in faculty_memberships.values()
        if data.get("normalized_display")
    }
    missing_name_identifiers -= existing_normalized_keys

    if missing_name_identifiers:
        extra_memberships = (
            OrganizationMembership.objects.filter(role="faculty")
            .exclude(id__in=processed_membership_ids)
            .select_related("organization", "user__profile")
        )
        for membership in extra_memberships:
            normalized_display = _normalise_identifier(
                membership.user.get_full_name() or membership.user.username or ""
            )
            if (
                not normalized_display
                or normalized_display not in missing_name_identifiers
            ):
                continue
            processed_membership_ids.add(membership.pk)
            _register_membership(membership)
            missing_name_identifiers.discard(normalized_display)
            if not missing_name_identifiers:
                break

    students_by_class: dict[str, list[str]] = {}
    faculty_by_org: dict[str, list[str]] = {}

    for row in rows:
        reg_no = (row.get("registration_no") or "").strip()
        full_name = (row.get("full_name") or "").strip()
        cls = (row.get("student_class") or "").strip()
        explicit_category = (row.get("category") or "").strip().lower()

        normalized_full_name = _normalise_identifier(full_name)

        membership_info = faculty_memberships.get(reg_no)
        matched_by_name = False
        if not membership_info and normalized_full_name:
            membership_info = faculty_memberships.get(normalized_full_name)
            if (
                membership_info
                and not reg_no
                and membership_info.get("normalized_display")
                and membership_info["normalized_display"] == normalized_full_name
            ):
                matched_by_name = True

        membership_org = (membership_info or {}).get("organization", "")
        membership_name = ((membership_info or {}).get("display_name") or "").strip()
        if matched_by_name:
            explicit_category = AttendanceRow.Category.FACULTY
            if membership_org:
                cls = membership_org
                row["student_class"] = cls
            row["affiliation"] = membership_org or row.get("affiliation") or ""

        if explicit_category in AttendanceRow.Category.values:
            category = explicit_category
            label = (
                row.get("affiliation")
                or cls
                or (
                    membership_org if category == AttendanceRow.Category.FACULTY else ""
                )
                or "Guests"
            )
            if (
                category == AttendanceRow.Category.STUDENT
                and reg_no
                and membership_info
                and reg_no not in student_map
            ):
                category = AttendanceRow.Category.FACULTY
                label = membership_org or label or "Unknown"
        elif cls or reg_no in student_map:
            category = AttendanceRow.Category.STUDENT
            label = cls or "Unknown"
        elif membership_info:
            category = AttendanceRow.Category.FACULTY
            label = membership_org or "Unknown"
        else:
            category = AttendanceRow.Category.EXTERNAL
            label = row.get("affiliation") or cls or "Guests"

        if category == AttendanceRow.Category.FACULTY:
            if matched_by_name and membership_org:
                label = membership_org
            else:
                label = label or membership_org or "Unknown"
        elif category == AttendanceRow.Category.STUDENT:
            label = label or "Unknown"
        else:
            label = label or "Guests"

        if category == AttendanceRow.Category.STUDENT:
            students_by_class.setdefault(label or "Unknown", []).append(full_name)
        elif category == AttendanceRow.Category.FACULTY:
            if membership_name:
                name_matches_reg_no = False
                if reg_no and full_name:
                    name_matches_reg_no = _normalise_identifier(
                        full_name
                    ) == _normalise_identifier(reg_no)
                if matched_by_name or not full_name or name_matches_reg_no:
                    full_name = membership_name
            if matched_by_name and label:
                row["student_class"] = label
            row["full_name"] = full_name
            faculty_by_org.setdefault(label or "Unknown", []).append(full_name)

        row["category"] = category
        row["affiliation"] = label or ""
        row["full_name"] = full_name

        # Ensure faculty rows capture their organisation even if student_class is blank
        if category == AttendanceRow.Category.FACULTY and not cls:
            row.setdefault("student_class", label)

    return students_by_class, faculty_by_org


@login_required
def upload_attendance_csv(request, report_id):
    """Upload and preview attendance CSV for an event report."""
    report = get_object_or_404(
        EventReport, id=report_id, proposal__submitted_by=request.user
    )

    rows = []
    error = None
    if request.method == "POST" and "csv_file" in request.FILES:
        try:
            rows = parse_attendance_csv(request.FILES["csv_file"])
        except ValueError as exc:
            error = str(exc)

    try:
        page = int(request.GET.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    if page < 1:
        page = 1
    per_page = 100

    if rows:
        counts = {
            "total": len(rows),
            "present": len([r for r in rows if not r.get("absent")]),
            "absent": len([r for r in rows if r.get("absent")]),
            "volunteers": len([r for r in rows if r.get("volunteer")]),
        }
        student_groups, faculty_groups = _group_attendance_rows(rows)
        full_rows = rows
    else:
        saved_rows = [
            {
                "registration_no": r.registration_no,
                "full_name": r.full_name,
                "student_class": r.student_class,
                "absent": r.absent,
                "volunteer": r.volunteer,
                "category": r.category,
                "affiliation": r.student_class,
            }
            for r in report.attendance_rows.all()
        ]
        counts = {
            "total": report.attendance_rows.count(),
            "present": report.attendance_rows.filter(absent=False).count(),
            "absent": report.attendance_rows.filter(absent=True).count(),
            "volunteers": report.attendance_rows.filter(volunteer=True).count(),
        }
        student_groups, faculty_groups = _group_attendance_rows(saved_rows)
        full_rows = saved_rows

    total_rows = len(full_rows)
    if total_rows:
        total_pages = (total_rows + per_page - 1) // per_page
        if page > total_pages:
            page = total_pages
    else:
        page = 1
        total_pages = 1

    context = {
        "report": report,
        # When a CSV is uploaded we want to preview the entire dataset so that
        # faculty rows are not hidden behind the initial 100 row slice.
        # The frontend already paginates the full list on the client side, so
        # pass the complete set of rows instead of just the first page.
        "rows_json": json.dumps(full_rows),
        "students_group_json": json.dumps(student_groups),
        "faculty_group_json": json.dumps(faculty_groups),
        "error": error,
        "page": page,
        "has_prev": total_rows > 0 and page > 1,
        "has_next": total_rows > 0 and page < total_pages,
        "counts": counts,
    }
    return render(request, "emt/attendance_upload.html", context)


@login_required
def graduate_attributes_edit(request, report_id):
    """Render Graduate Attributes editor page for an event report."""
    report = get_object_or_404(
        EventReport, id=report_id, proposal__submitted_by=request.user
    )
    context = {
        "report": report,
    }
    return render(request, "emt/graduate_attributes_edit.html", context)


@login_required
@require_POST
def graduate_attributes_save(request, report_id):
    """Save Graduate Attributes selections into the report and redirect back to the form."""
    report = get_object_or_404(
        EventReport, id=report_id, proposal__submitted_by=request.user
    )
    # Accept either a combined string or a list of categories
    # The GA editor posts multiple checkboxes named exactly 'needs_grad_attr_mapping'
    items = request.POST.getlist("needs_grad_attr_mapping")
    if items:
        mapping_text = ", ".join(items)
    else:
        mapping_text = request.POST.get("needs_grad_attr_mapping", "")

    report.needs_grad_attr_mapping = mapping_text
    # Optional: contemporary requirements and sdg text from editor page
    if "contemporary_requirements" in request.POST:
        report.contemporary_requirements = request.POST.get(
            "contemporary_requirements", ""
        )
    if "sdg_value_systems_mapping" in request.POST:
        report.sdg_value_systems_mapping = request.POST.get(
            "sdg_value_systems_mapping", ""
        )
    report.save()

    messages.success(request, "Graduate Attributes updated.")
    # Preserve return to Event Relevance section
    response = redirect("emt:submit_event_report", proposal_id=report.proposal.id)
    # Return to section 6 (event-relevance) and mark source as GA editor
    response["Location"] += "?section=event-relevance&from=ga"
    return response


@login_required
@require_http_methods(["GET"])
def attendance_data(request, report_id):
    """Return attendance rows and counts for a report."""
    report = get_object_or_404(
        EventReport, id=report_id, proposal__submitted_by=request.user
    )
    proposal = report.proposal
    rows = [
        {
            "registration_no": r.registration_no,
            "full_name": r.full_name,
            "student_class": r.student_class,
            "absent": r.absent,
            "volunteer": r.volunteer,
            "category": r.category,
            "affiliation": r.student_class,
        }
        for r in report.attendance_rows.all()
    ]

    had_saved_rows = len(rows) > 0

    def _normalise_reg(value: str) -> str:
        return (value or "").strip().lower()

    def _normalise_name(value: str) -> str:
        return re.sub(r"\s+", "", (value or "").strip()).lower()

    existing_registrations = {
        norm
        for norm in (_normalise_reg(r.get("registration_no")) for r in rows)
        if norm
    }
    existing_names = {
        norm for norm in (_normalise_name(r.get("full_name")) for r in rows) if norm
    }

    def add_row_if_missing(row: dict) -> None:
        reg_norm = _normalise_reg(row.get("registration_no"))
        name_norm = _normalise_name(row.get("full_name"))
        if reg_norm and reg_norm in existing_registrations:
            return
        if not reg_norm and name_norm and name_norm in existing_names:
            return
        rows.append(row)
        if reg_norm:
            existing_registrations.add(reg_norm)
        if name_norm:
            existing_names.add(name_norm)

    def _normalise_lookup(value: str) -> str:
        """Return a lookup friendly token ignoring whitespace and punctuation."""

        return re.sub(r"[^a-z0-9]", "", (value or "").lower())

    names = [
        n.strip() for n in (proposal.target_audience or "").split(",") if n.strip()
    ]

    def _build_faculty_entry(user, organization_name: str = "") -> dict[str, str]:
        profile = getattr(user, "profile", None)
        reg_no = (getattr(profile, "register_no", "") or user.username or "").strip()
        full_name = (user.get_full_name() or user.username or "").strip()
        return {
            "registration_no": reg_no,
            "full_name": full_name,
            "organization": (organization_name or "").strip(),
        }

    faculty_lookup: dict[str, dict[str, str]] = {}

    def _register_faculty_lookup(user, organization_name: str = "") -> None:
        if not user:
            return
        entry = _build_faculty_entry(user, organization_name)
        lookup_values = {
            entry["registration_no"],
            entry["full_name"],
            user.username,
            f"{user.first_name} {user.last_name}".strip(),
        }
        for value in list(lookup_values):
            if value:
                lookup_values.add(value.replace(" ", ""))
        for value in lookup_values:
            token = _normalise_lookup(value)
            if token:
                existing = faculty_lookup.get(token)
                if existing and existing.get("organization") and not entry["organization"]:
                    continue
                faculty_lookup[token] = entry

    membership_qs = (
        OrganizationMembership.objects.filter(role="faculty")
        .select_related("user__profile", "organization")
        .order_by("id")
    )
    membership_org_by_user: dict[int, str] = {}
    for membership in membership_qs:
        organization_name = (
            membership.organization.name if membership.organization else ""
        )
        _register_faculty_lookup(membership.user, organization_name)
        if membership.user_id and organization_name:
            membership_org_by_user.setdefault(membership.user_id, organization_name)

    role_assignment_qs = (
        RoleAssignment.objects.filter(role__name__icontains="faculty")
        .select_related("user__profile", "organization", "role")
        .order_by("id")
    )
    for assignment in role_assignment_qs:
        organization_name = (
            assignment.organization.name if assignment.organization else ""
        )
        _register_faculty_lookup(assignment.user, organization_name)
        if assignment.user_id and organization_name:
            membership_org_by_user.setdefault(assignment.user_id, organization_name)

    for faculty_user in proposal.faculty_incharges.all().select_related("profile"):
        organization_name = membership_org_by_user.get(faculty_user.id, "")
        _register_faculty_lookup(faculty_user, organization_name)
    if names:
        students = {
            (s.user.get_full_name() or s.user.username).strip().lower(): s
            for s in Student.objects.select_related("user")
        }

        from core.models import \
            Class  # local import to avoid circulars at module import time

        def add_rows_for_class(cls_obj):
            for stu in cls_obj.students.select_related("user").all():
                full_name = (stu.user.get_full_name() or stu.user.username).strip()
                reg_no = stu.registration_number or getattr(
                    getattr(stu.user, "profile", None), "register_no", ""
                )
                add_row_if_missing(
                    {
                        "registration_no": reg_no,
                        "full_name": full_name,
                        "student_class": cls_obj.code or cls_obj.name,
                        "absent": False,
                        "volunteer": False,
                        "category": AttendanceRow.Category.STUDENT,
                        "affiliation": cls_obj.code or cls_obj.name,
                    }
                )

        for name in names:
            student = students.get(name.lower())
            if student:
                reg_no = student.registration_number or getattr(
                    getattr(student.user, "profile", None), "register_no", ""
                )
                cls = student.classes.filter(is_active=True).first()
                add_row_if_missing(
                    {
                        "registration_no": reg_no,
                        "full_name": (
                            student.user.get_full_name() or student.user.username
                        ).strip(),
                        "student_class": (
                            cls.code if cls and cls.code else (cls.name if cls else "")
                        ),
                        "absent": False,
                        "volunteer": False,
                        "category": AttendanceRow.Category.STUDENT,
                        "affiliation": (
                            cls.code if cls and cls.code else (cls.name if cls else "")
                        ),
                    }
                )
                continue

            class_name = name
            org_name = None
            if "(" in name and ")" in name:
                try:
                    class_name = name.split("(")[0].strip()
                    org_name = name[name.index("(") + 1 : name.rindex(")")].strip()
                except Exception:
                    class_name = name.strip()
                    org_name = None

            cls_obj = None
            if not had_saved_rows:
                cls_qs = Class.objects.filter(name__iexact=class_name)
                if org_name:
                    cls_qs = cls_qs.filter(organization__name__iexact=org_name)

                cls_obj = cls_qs.first()
                if not cls_obj:
                    cls_obj = Class.objects.filter(code__iexact=class_name).first()

            if cls_obj:
                add_rows_for_class(cls_obj)
                continue

            faculty_entry = None
            lookup_candidates = filter(None, [name, class_name, org_name])
            for candidate in lookup_candidates:
                token = _normalise_lookup(candidate)
                if not token:
                    continue
                faculty_entry = faculty_lookup.get(token)
                if faculty_entry:
                    break

            if faculty_entry:
                add_row_if_missing(
                    {
                        "registration_no": faculty_entry["registration_no"],
                        "full_name": faculty_entry["full_name"],
                        "student_class": faculty_entry["organization"],
                        "absent": False,
                        "volunteer": False,
                        "category": AttendanceRow.Category.FACULTY,
                        "affiliation": faculty_entry["organization"],
                    }
                )
                continue

            # Skip adding placeholder "guest" rows for unmatched audience entries.
            # These are often department names (e.g. "Data Science") that should
            # not appear as attendees until a CSV upload provides concrete data.
            continue

    faculty_users = list(proposal.faculty_incharges.all().select_related("profile"))
    for user in faculty_users:
        profile = getattr(user, "profile", None)
        reg_no = (getattr(profile, "register_no", "") or user.username or "").strip()
        full_name = (user.get_full_name() or user.username or "").strip()
        if not full_name and not reg_no:
            continue
        add_row_if_missing(
            {
                "registration_no": reg_no,
                "full_name": full_name,
                "student_class": "",
                "absent": False,
                "volunteer": False,
                "category": AttendanceRow.Category.FACULTY,
                "affiliation": "",
            }
        )

    counts = {
        "total": len(rows),
        "present": len([r for r in rows if not r.get("absent")]),
        "absent": len([r for r in rows if r.get("absent")]),
        "volunteers": len([r for r in rows if r.get("volunteer")]),
    }
    student_groups, faculty_groups = _group_attendance_rows(rows)
    logger.info("Fetched attendance data for report %s", report_id)
    return JsonResponse(
        {
            "rows": rows,
            "counts": counts,
            "students": student_groups,
            "faculty": faculty_groups,
        }
    )


@login_required
@require_POST
def save_attendance_rows(request, report_id):
    """Persist attendance rows to database and update report counts."""
    report = get_object_or_404(
        EventReport, id=report_id, proposal__submitted_by=request.user
    )
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    rows = payload.get("rows", [])
    _group_attendance_rows(rows)
    AttendanceRow.objects.filter(event_report=report).delete()
    objs = [
        AttendanceRow(
            event_report=report,
            registration_no=r.get("registration_no", ""),
            full_name=r.get("full_name", ""),
            student_class=r.get("student_class", ""),
            absent=bool(r.get("absent")),
            volunteer=bool(r.get("volunteer")),
            category=(
                (r.get("category") or AttendanceRow.Category.STUDENT)
                if (r.get("category") in AttendanceRow.Category.values)
                else AttendanceRow.Category.STUDENT
            ),
        )
        for r in rows
    ]
    AttendanceRow.objects.bulk_create(objs)

    total = len(rows)
    absent = len([r for r in rows if r.get("absent")])
    volunteers = len([r for r in rows if r.get("volunteer")])
    present_rows = [r for r in rows if not r.get("absent")]
    present = len(present_rows)

    student_count = sum(
        1
        for r in present_rows
        if (r.get("category") or AttendanceRow.Category.STUDENT)
        == AttendanceRow.Category.STUDENT
    )
    faculty_count = sum(
        1
        for r in present_rows
        if (r.get("category") or "").lower() == AttendanceRow.Category.FACULTY
    )
    external_count = present - student_count - faculty_count

    report.num_participants = present
    report.num_student_volunteers = volunteers
    report.num_student_participants = student_count
    report.num_faculty_participants = faculty_count
    report.num_external_participants = external_count
    report.save(
        update_fields=[
            "num_participants",
            "num_student_volunteers",
            "num_student_participants",
            "num_faculty_participants",
            "num_external_participants",
        ]
    )

    # Persist counts in session draft so the report form shows updated values
    drafts = request.session.setdefault("event_report_draft", {})
    key = str(report.proposal_id)
    draft = drafts.get(key, {})
    draft.update(
        {
            "num_participants": present,
            "num_student_volunteers": volunteers,
            "num_student_participants": student_count,
            "num_faculty_participants": faculty_count,
            "num_external_participants": external_count,
        }
    )
    drafts[key] = draft
    request.session.modified = True

    return JsonResponse(
        {
            "total": total,
            "present": present,
            "absent": absent,
            "volunteers": volunteers,
            "students": student_count,
            "faculty": faculty_count,
            "external": external_count,
        }
    )


@login_required
@require_POST
def download_attendance_csv(request, report_id):
    """Download current attendance rows as CSV."""
    report = get_object_or_404(
        EventReport, id=report_id, proposal__submitted_by=request.user
    )
    try:
        payload = json.loads(request.body.decode("utf-8"))
        rows = payload.get("rows")
    except json.JSONDecodeError:
        rows = None

    if rows is None:
        rows = [
            {
                "registration_no": r.registration_no,
                "full_name": r.full_name,
                "student_class": r.student_class,
                "absent": r.absent,
                "volunteer": r.volunteer,
                "category": r.category,
            }
            for r in report.attendance_rows.all()
        ]

    response = HttpResponse(content_type="text/csv")
    filename = f"attendance_{report_id}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(ATTENDANCE_HEADERS)
    for r in rows:
        writer.writerow(
            [
                (r.get("category") or AttendanceRow.Category.STUDENT),
                r.get("registration_no", ""),
                r.get("full_name", ""),
                r.get("student_class", ""),
                "TRUE" if r.get("absent") else "FALSE",
                "TRUE" if r.get("volunteer") else "FALSE",
            ]
        )

    return response


@login_required
def suite_dashboard(request):
    """
    Show current user's proposals excluding finalized ones older than 2 days.
    Compute per-proposal progress for display in dashboard.html.
    """
    # 1) Get proposals excluding finalized + 2-day-old ones
    user_proposals = (
        EventProposal.objects.filter(
            submitted_by=request.user,
            is_user_deleted=False,
        )
        .exclude(status="finalized", updated_at__lt=now() - timedelta(days=2))
        .prefetch_related("approval_steps")
        .order_by("-updated_at")
    )

    # 2) Prepare statuses and UI fields
    for p in user_proposals:
        db_status = (p.status or "").strip().lower()

        if db_status == "rejected":
            p.statuses = ["draft", "submitted", "under_review", "rejected"]
        else:
            p.statuses = ["draft", "submitted", "under_review", "finalized"]

        p.status_index = p.statuses.index(db_status) if db_status in p.statuses else 0
        p.progress_percent = (
            int(p.status_index * 100 / (len(p.statuses) - 1))
            if len(p.statuses) > 1
            else 100
        )
        p.current_label = p.statuses[p.status_index].replace("_", " ").capitalize()

    # 3) Approvals card visibility
    is_student = (
        getattr(getattr(request.user, "profile", None), "role", "") == "student"
    )
    show_approvals_card = not is_student

    # 4) Return dashboard with user_proposals
    return render(
        request,
        "dashboard.html",
        {
            "user_proposals": user_proposals,
            "show_approvals_card": show_approvals_card,
        },
    )


@login_required
def ai_generate_report(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id)
    report, created = EventReport.objects.get_or_create(proposal=proposal)

    # This should be replaced with actual AI generation logic
    context = {
        "proposal": proposal,
        "report": report,
        "ai_content": "This is a placeholder for AI-generated content. Integrate with your AI service here.",
    }
    return render(request, "emt/ai_generate_report.html", context)


@csrf_exempt
def generate_ai_report(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            prompt = f"""
            You are an expert in academic event reporting for university IQAC documentation.
            Generate a detailed, formal, and highly structured IQAC-style event report using the following data.
            **Follow the given format strictly**. Use professional, concise,
            academic language. Format all sections as shown, and fill any
            missing info sensibly if needed.

            ---
            # EVENT INFORMATION
            | Field                 | Value                                |
            |----------------------|-------------------------------|
            | Department           | {data.get('department', '')} |
            | Location             | {data.get('location', '')} |
            | Event Title          | {data.get('event_title', '')} |
            | No of Activities     | {data.get('no_of_activities', '1')} |
            | Date and Time        | {data.get('event_datetime', '')} |
            | Venue                | {data.get('venue', '')} |
            | Academic Year        | {data.get('academic_year', '')} |
            | Event Type (Focus)   | {data.get('event_focus_type', '')} |

            # PARTICIPANTS INFORMATION
            | Field                   | Value                                |
            |-------------------------|----------------------------|
            | Target Audience         | {data.get('target_audience', '')} |
            | Organising Committee    | {data.get('organising_committee_details', '')} |
            | No of Student Volunteers| {data.get('no_of_volunteers', '')} |
            | No of Attendees         | {data.get('no_of_attendees', '')} |

            # SUMMARY OF THE OVERALL EVENT
            {data.get(
                'summary',
                (
                    'Please write a 2-3 paragraph formal summary of the event. '
                    'Cover objectives, flow, engagement, and outcomes.'
                ),
            )}

            # OUTCOMES OF THE EVENT
            {data.get('outcomes', '- List 3-5 major outcomes, in bullets.')}

            # ANALYSIS
            - Impact on Attendees: {data.get('impact_on_attendees', '')}
            - Impact on Schools: {data.get('impact_on_schools', '')}
            - Impact on Volunteers: {data.get('impact_on_volunteers', '')}

            # RELEVANCE OF THE EVENT
            | Criteria                | Description                         |
            |-------------------------|-----------------------------|
            | Graduate Attributes     | {data.get('graduate_attributes', '')} |
            | Support to SDGs/Values  | {data.get('sdg_value_systems_mapping', '')} |

            # SUGGESTIONS FOR IMPROVEMENT / FEEDBACK FROM IQAC
            {data.get('iqac_feedback', '')}

            # ATTACHMENTS/EVIDENCE
            {data.get('attachments', '- List any evidence (photos, worksheets, etc.) if available.')}

            ---

            ## Ensure the final output is clear, formal, and as per IQAC standards.
            ## DO NOT leave sections blank; fill with professional-sounding content if data is missing.
            """

            model = genai.GenerativeModel("models/gemini-1.5-pro-latest")
            response = model.generate_content(prompt)

            # Google GenAI occasionally returns None
            if not response or not hasattr(response, "text"):
                return JsonResponse(
                    {"error": "AI did not return any text."}, status=500
                )

            return JsonResponse({"report_text": response.text})

        except Exception as e:
            print("AI Generation error:", e)
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Only POST allowed"}, status=405)


@csrf_exempt
@login_required
def save_ai_report(request):
    if request.method == "POST":
        data = json.loads(request.body)
        proposal = get_object_or_404(
            EventProposal, id=data["proposal_id"], submitted_by=request.user
        )
        report, _ = EventReport.objects.get_or_create(proposal=proposal)
        report.summary = data.get("full_text")[:1000]  # or whatever logic
        report.save()
        return JsonResponse({"success": True})
    return JsonResponse({"error": "POST only"}, status=405)


@login_required
def ai_report_progress(request, proposal_id):
    """Return minimal AI report generation status to avoid errors in legacy routes."""
    report = EventReport.objects.filter(proposal_id=proposal_id).select_related("proposal").first()
    if not report:
        return JsonResponse({"status": "none", "summary": ""})
    status = "finished" if (report.summary or "").strip() else "in_progress"
    return JsonResponse({"status": status, "summary": report.summary or ""})


@csrf_exempt
@login_required
def ai_report_partial(request, proposal_id):
    from .models import EventReport

    report = EventReport.objects.filter(proposal_id=proposal_id).first()
    if not report or not report.summary:
        # Simulate progress if nothing generated yet
        return JsonResponse({"text": "", "status": "in_progress"})
    # For now, always show the full summary and mark as finished
    return JsonResponse({"text": report.summary, "status": "finished"})


@login_required
def generate_ai_report_stream(request, proposal_id):
    import time

    proposal = get_object_or_404(EventProposal, id=proposal_id)
    report = EventReport.objects.get_or_create(proposal=proposal)[0]
    # Compose strict, flat prompt!

    genai.GenerativeModel("models/gemini-1.5-pro-latest")

    chunks = [
        f"# Event Report: {proposal.event_title}\n\n",
        "## Summary\nThis is a simulated AI-generated report...\n\n",
        "## Outcomes\n- Outcome 1\n- Outcome 2\n\n",
        "## Recommendations\nFuture improvements...\n",
    ]

    def generate():

        for chunk in chunks:
            yield chunk
            time.sleep(0.5)  # Simulate delay

    report.ai_generated_report = "".join(chunks)
    report.save()

    return StreamingHttpResponse(generate(), content_type="text/plain")


@login_required
def admin_dashboard(request):
    """
    Render the static admin dashboard template.
    """
    return render(request, "core/admin_dashboard.html")


@login_required
def ai_report_edit(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id)
    last_instructions = ""
    last_fields = ""
    if request.method == "POST":
        # Collect user changes/prompts
        instructions = request.POST.get("instructions", "").strip()
        manual_fields = request.POST.get("manual_fields", "").strip()
        # You may want to store these temporarily for next reload
        last_instructions = instructions
        last_fields = manual_fields

        # Construct a new prompt for the AI
        ai_prompt = f"""
        Please regenerate the IQAC Event Report as before,
        but follow these special user instructions:
        ---
        {instructions}
        ---
        {manual_fields}
        ---
        Use the same field structure as before.
        """

        # Call Gemini here or set a session variable with prompt and redirect to progress
        request.session["ai_custom_prompt"] = ai_prompt
        return redirect("emt:ai_report_progress", proposal_id=proposal.id)

    # Pre-fill manual_fields with last generated report fields if you want
    return render(
        request,
        "emt/ai_report_edit.html",
        {
            "proposal": proposal,
            "last_instructions": last_instructions,
            "last_fields": last_fields,
        },
    )


@login_required
def ai_report_submit(request, proposal_id):
    proposal = get_object_or_404(
        EventProposal, id=proposal_id, submitted_by=request.user
    )

    # Get or create report
    report, created = EventReport.objects.get_or_create(proposal=proposal)

    # Update status
    proposal.report_generated = True
    proposal.status = "finalized"
    proposal.save()

    # Add success message
    messages.success(request, "Event report submitted successfully!")
    return redirect("emt:report_success", proposal_id=proposal.id)


@user_passes_test(lambda u: u.is_superuser)
def api_organization_types(request):
    org_types = OrganizationType.objects.filter(is_active=True).order_by("name")
    data = [{"id": ot.name.lower(), "name": ot.name} for ot in org_types]
    return JsonResponse(data, safe=False)


# ------------------------------------------------------------------
# │ NEW FUNCTION ADDED BELOW                                       │
# ------------------------------------------------------------------


@login_required
def admin_reports_view(request):
    try:
        submitted_reports = list(
            Report.objects.select_related("organization", "submitted_by")
        )
        generated_reports = list(
            EventReport.objects.select_related(
                "proposal",
                "proposal__organization",
                "proposal__submitted_by",
            )
        )

        for report in submitted_reports:
            report.sort_date = report.created_at

        for report in generated_reports:
            report.sort_date = report.created_at or report.proposal.created_at

        all_reports_list = sorted(
            submitted_reports + generated_reports,
            key=attrgetter("sort_date"),
            reverse=True,
        )

        context = {"reports": all_reports_list}

        return render(request, "core/admin_reports.html", context)

    except Exception as e:
        # It's good practice to log the actual exception
        logger.error(f"Error in admin_reports_view: {e}", exc_info=True)
        return HttpResponse(f"An error occurred: {e}", status=500)


def _basic_info_context(data):
    parts = []
    title = (data.get("title") or "").strip()
    if title:
        parts.append(f"Event title: {title}")
    audience = (data.get("audience") or "").strip()
    if audience:
        parts.append(f"Target audience: {audience}")
    focus = (data.get("focus") or "").strip()
    if focus:
        parts.append(f"Event focus: {focus}")
    venue = (data.get("venue") or "").strip()
    if venue:
        parts.append(f"Location: {venue}")
    existing = (data.get("context") or "").strip()
    if existing:
        parts.append(f"Existing text:\n{existing}")
    return "\n".join(parts)[:3000]


NEED_PROMPT = "Write a concise, factual Need Analysis (80-140 words) for the event."
OBJ_PROMPT = "Provide 3-5 clear objectives for the event as bullet points."
OUT_PROMPT = "List 3-5 expected learning outcomes for participants as bullet points."


@login_required
@require_POST
def generate_need_analysis(request):
    ctx = _basic_info_context(request.POST)
    if not ctx:
        return JsonResponse({"ok": False, "error": "No context"}, status=400)
    try:
        messages = [{"role": "user", "content": f"{NEED_PROMPT}\n\n{ctx}"}]
        timeout = getattr(settings, "AI_HTTP_TIMEOUT", 60)
        text = chat(
            messages,
            system="You write crisp academic content for university event proposals.",
            timeout=timeout,
        )
        return JsonResponse({"ok": True, "text": text})
    except AIError as exc:
        logger.error("Need analysis generation failed: %s", exc)
        return JsonResponse({"ok": False, "error": str(exc)}, status=503)
    except Exception as exc:
        logger.error("Need analysis generation unexpected error: %s", exc)
        return JsonResponse(
            {"ok": False, "error": f"Unexpected error: {exc}"}, status=500
        )


@login_required
@require_POST
def generate_objectives(request):
    ctx = _basic_info_context(request.POST)
    if not ctx:
        return JsonResponse({"ok": False, "error": "No context"}, status=400)
    try:
        messages = [{"role": "user", "content": f"{OBJ_PROMPT}\n\n{ctx}"}]
        timeout = getattr(settings, "AI_HTTP_TIMEOUT", 60)
        text = chat(
            messages,
            system="You write measurable, outcome-focused objectives aligned to higher-education events.",
            timeout=timeout,
        )
        return JsonResponse({"ok": True, "text": text})
    except AIError as exc:
        logger.error("Objectives generation failed: %s", exc)
        return JsonResponse({"ok": False, "error": str(exc)}, status=503)
    except Exception as exc:
        logger.error("Objectives generation unexpected error: %s", exc)
        return JsonResponse(
            {"ok": False, "error": f"Unexpected error: {exc}"}, status=500
        )


@login_required
@require_POST
def generate_expected_outcomes(request):
    ctx = _basic_info_context(request.POST)
    if not ctx:
        return JsonResponse({"ok": False, "error": "No context"}, status=400)
    try:
        messages = [{"role": "user", "content": f"{OUT_PROMPT}\n\n{ctx}"}]
        timeout = getattr(settings, "AI_HTTP_TIMEOUT", 60)
        text = chat(
            messages,
            system="You write measurable expected outcomes for higher-education events.",
            timeout=timeout,
        )
        return JsonResponse({"ok": True, "text": text})
    except AIError as exc:
        logger.error("Expected outcomes generation failed: %s", exc)
        return JsonResponse({"ok": False, "error": str(exc)}, status=503)
    except Exception as exc:
        logger.error("Expected outcomes generation unexpected error: %s", exc)
        return JsonResponse(
            {"ok": False, "error": f"Unexpected error: {exc}"}, status=500
        )
