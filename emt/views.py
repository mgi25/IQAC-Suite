from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.conf import settings
import json
import re
from urllib.parse import urlparse
import requests
from suite.ai_client import chat, AIError
import time
from bs4 import BeautifulSoup
from django.db.models import Q
from .models import (
    EventProposal, EventNeedAnalysis, EventObjectives,
    EventExpectedOutcomes, TentativeFlow, EventActivity,
    ExpenseDetail, IncomeDetail, SpeakerProfile, EventReport,
    EventReportAttachment, CDLSupport, Student
)
from .forms import (
    EventProposalForm, NeedAnalysisForm, ExpectedOutcomesForm,
    ObjectivesForm, TentativeFlowForm, SpeakerProfileForm,
    ExpenseDetailForm,EventReportForm, EventReportAttachmentForm, CDLSupportForm
)
from django.forms import modelformset_factory
from core.models import (
    Organization,
    OrganizationType,
    Report as SubmittedReport,
    ApprovalFlowTemplate,
    SDGGoal,
    Class,
    SDG_GOALS,
    OrganizationMembership,
)
from django.contrib.auth.models import User
from emt.utils import (
    build_approval_chain,
    auto_approve_non_optional_duplicates,
    unlock_optionals_after,
    skip_all_downstream_optionals,
    get_downstream_optional_candidates,
)
from emt.models import ApprovalStep
import os
OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://127.0.0.1:11434")
GEN_MODEL   = os.getenv("OLLAMA_GEN_MODEL", "qwen2.5:7b-instruct-q4_0")
CRITIC_MODEL = os.getenv("OLLAMA_CRITIC_MODEL", "llama3.2:3b-instruct-q4_0")

# ---------------------------------------------------------------------------
# Role name constants for lookup to avoid hardcoded strings
# ---------------------------------------------------------------------------
FACULTY_ROLE = ApprovalStep.Role.FACULTY.value
DEAN_ROLE = ApprovalStep.Role.DEAN.value
ACADEMIC_COORDINATOR_ROLE = "academic_coordinator"

from django.contrib import messages
from django.utils import timezone
from django.db import models
from .models import MediaRequest
from datetime import timedelta
from django.utils.timezone import now
from django.db.models import Sum
import google.generativeai as genai
import os
from django.contrib.auth.decorators import login_required, user_passes_test

# --- Added for the new function ---
from itertools import chain
from operator import attrgetter
# ----------------------------------

import logging

# Get an instance of the logger for the 'emt' app
logger = logging.getLogger(__name__) # __name__ will resolve to 'emt.views'
# Configure Gemini API key from environment variable(s)
# Prefer `GEMINI_API_KEY`; fall back to `GOOGLE_API_KEY`
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

@login_required
def submit_request_view(request):
    if request.method == 'POST':
        media_type = request.POST.get('media_type')
        title = request.POST.get('title')
        description = request.POST.get('description')
        event_date = request.POST.get('event_date')
        media_file = request.FILES.get('media_file')

        MediaRequest.objects.create(
            user=request.user,
            media_type=media_type,
            title=title,
            description=description,
            event_date=event_date,
            media_file=media_file
        )
        messages.success(request, 'Your media request has been submitted.')
        return redirect('cdl_dashboard')

    return render(request, 'emt/cdl_submit_request.html')

@login_required
def my_requests_view(request):
    requests = MediaRequest.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'emt/cdl_my_requests.html', {'requests': requests})

# ──────────────────────────────
# REPORT GENERATION
# ──────────────────────────────
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.template.loader import render_to_string
from django.http import HttpResponse
import pdfkit

def report_form(request):
 return render(request, "report_generation.html")
@csrf_exempt
def generate_report_pdf(request):
    if request.method == 'POST':
        html = render_to_string("pdf_template.html", {"data": request.POST})
        pdf = pdfkit.from_string(html, False)
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="Event_Report.pdf"'
        return response

# Helper to persist text-based sections for proposals
def _save_text_sections(proposal, data):
    section_map = {
        "need_analysis": EventNeedAnalysis,
        "objectives": EventObjectives,
        "outcomes": EventExpectedOutcomes,
        "flow": TentativeFlow,
    }
    for field, model in section_map.items():
        if field in data:
            obj, _ = model.objects.get_or_create(proposal=proposal)
            obj.content = data.get(field) or ""
            obj.save()


def _save_activities(proposal, data):
    proposal.activities.all().delete()
    pattern = re.compile(r"^activity_(?:name|date)_(\d+)$")
    indices = sorted({int(m.group(1)) for key in data.keys() if (m := pattern.match(key))})
    for index in indices:
        name = data.get(f"activity_name_{index}")
        date = data.get(f"activity_date_{index}")
        if name and date:
            EventActivity.objects.create(proposal=proposal, name=name, date=date)


def _save_speakers(proposal, data, files):
    proposal.speakers.all().delete()
    pattern = re.compile(
        r"^speaker_(?:full_name|designation|affiliation|contact_email|contact_number|linkedin_url|photo|detailed_profile)_(\d+)$"
    )
    all_keys = list(data.keys()) + list(files.keys())
    indices = sorted({int(m.group(1)) for key in all_keys if (m := pattern.match(key))})
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


def _save_expenses(proposal, data):
    proposal.expense_details.all().delete()
    pattern = re.compile(r"^expense_(?:sl_no|particulars|amount)_(\d+)$")
    indices = sorted({int(m.group(1)) for key in data.keys() if (m := pattern.match(key))})
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
    proposal.income_details.all().delete()
    pattern = re.compile(
        r"^income_(?:sl_no|particulars|participants|rate|amount)_(\d+)$"
    )
    indices = sorted({int(m.group(1)) for key in data.keys() if (m := pattern.match(key))})
    for index in indices:
        particulars = data.get(f"income_particulars_{index}")
        participants = data.get(f"income_participants_{index}")
        rate = data.get(f"income_rate_{index}")
        amount = data.get(f"income_amount_{index}")
        if particulars and participants and rate and amount:
            sl_no = data.get(f"income_sl_no_{index}") or 0
            IncomeDetail.objects.create(
                proposal=proposal,
                sl_no=sl_no or 0,
                particulars=particulars,
                participants=participants,
                rate=rate,
                amount=amount,
            )


# ──────────────────────────────
# PROPOSAL STEP 1: Proposal Submission
# ──────────────────────────────
@login_required
def submit_proposal(request, pk=None):
    from transcript.models import get_active_academic_year

    active_year = get_active_academic_year()
    selected_academic_year = active_year.year if active_year else ""

    proposal = None
    if pk:
        proposal = get_object_or_404(
            EventProposal, pk=pk, submitted_by=request.user
        )

    if request.method == "POST":
        post_data = request.POST.copy()
        logger.debug("submit_proposal POST data: %s", post_data)
        logger.debug("Faculty IDs from POST: %s", post_data.getlist("faculty_incharges"))
        form = EventProposalForm(
            post_data,
            instance=proposal,
            selected_academic_year=selected_academic_year,
            user=request.user,
        )

        # --------- FACULTY INCHARGES QUERYSET FIX ---------
        faculty_ids = post_data.getlist("faculty_incharges")
        if faculty_ids:
            form.fields['faculty_incharges'].queryset = User.objects.filter(
                Q(role_assignments__role__name=FACULTY_ROLE) | Q(id__in=faculty_ids)
            ).distinct()
        else:
            form.fields['faculty_incharges'].queryset = User.objects.filter(
                role_assignments__role__name=FACULTY_ROLE
            ).distinct()
        # --------------------------------------------------

    else:
        # Only pre-populate form with existing data if it's still a draft
        form_instance = proposal if (proposal and proposal.status == 'draft') else None

        form = EventProposalForm(
            instance=form_instance,
            selected_academic_year=selected_academic_year,
            user=request.user,
        )
        # Populate all faculty as available choices for JS search/select on GET.
        # Include already assigned faculty so their selections remain visible.
        fac_ids = list(proposal.faculty_incharges.all().values_list('id', flat=True)) if proposal else []
        form.fields['faculty_incharges'].queryset = User.objects.filter(
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

    need_analysis = EventNeedAnalysis.objects.filter(proposal=proposal).first() if proposal else None
    objectives = EventObjectives.objects.filter(proposal=proposal).first() if proposal else None
    outcomes = EventExpectedOutcomes.objects.filter(proposal=proposal).first() if proposal else None
    flow = TentativeFlow.objects.filter(proposal=proposal).first() if proposal else None
    activities = list(proposal.activities.values('name', 'date')) if proposal else []
    speakers = list(proposal.speakers.values('full_name','designation','affiliation','contact_email','contact_number','linkedin_url','detailed_profile')) if proposal else []
    expenses = list(proposal.expense_details.values('sl_no','particulars','amount')) if proposal else []
    income = list(proposal.income_details.values('sl_no','particulars','participants','rate','amount')) if proposal else []

    ctx = {
        "form": form,
        "proposal": proposal,
        "org_types": OrganizationType.objects.filter(is_active=True).order_by('name'),
        "need_analysis": need_analysis,
        "objectives": objectives,
        "outcomes": outcomes,
        "flow": flow,
        "sdg_goals_list": json.dumps(list(SDGGoal.objects.filter(name__in=SDG_GOALS).values('id','name'))),
        "activities_json": json.dumps(activities),
        "speakers_json": json.dumps(speakers),
        "expenses_json": json.dumps(expenses),
        "income_json": json.dumps(income),
    }


    if request.method == "POST" and form.is_valid():
        proposal = form.save(commit=False)
        proposal.submitted_by = request.user
        if "final_submit" in request.POST:
            proposal.status = "submitted"
            proposal.submitted_at = timezone.now()
            proposal.save()
            form.save_m2m()
            _save_text_sections(proposal, request.POST)
            _save_activities(proposal, request.POST)
            _save_speakers(proposal, request.POST, request.FILES)
            _save_expenses(proposal, request.POST)
            _save_income(proposal, request.POST)
            logger.debug(
                "Proposal %s saved with faculty %s",
                proposal.id,
                list(proposal.faculty_incharges.values_list("id", flat=True)),
            )
            build_approval_chain(proposal)
            messages.success(
                request,
                f"Proposal '{proposal.event_title}' submitted.",
            )
            return redirect("emt:proposal_status_detail", proposal_id=proposal.id)
        else:
            proposal.status = "draft"
            proposal.save()
            form.save_m2m()
            _save_text_sections(proposal, request.POST)
            _save_activities(proposal, request.POST)
            _save_speakers(proposal, request.POST, request.FILES)
            _save_expenses(proposal, request.POST)
            _save_income(proposal, request.POST)
            logger.debug(
                "Draft proposal %s saved with faculty %s",
                proposal.id,
                list(proposal.faculty_incharges.values_list("id", flat=True)),
            )
            return redirect("emt:submit_need_analysis", proposal_id=proposal.id)

    return render(request, "emt/submit_proposal.html", ctx)


# ──────────────────────────────────────────────────────────────
#  Autosave draft (XHR from JS)
# ──────────────────────────────────────────────────────────────
@csrf_exempt
@login_required
def autosave_proposal(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    data = json.loads(request.body.decode("utf-8"))
    logger.debug("autosave_proposal payload: %s", data)

    # Replace department logic with generic organization
    org_type_val = data.get("organization_type")  # You'll need to capture org type in your frontend/form!
    org_name_val = data.get("organization")
    if org_type_val and org_name_val and not str(org_name_val).isdigit():
        from core.models import Organization, OrganizationType
        org_type_obj, _ = OrganizationType.objects.get_or_create(name=org_type_val)
        org_obj, _ = Organization.objects.get_or_create(name=org_name_val, org_type=org_type_obj)
        data["organization"] = str(org_obj.id)


    proposal = None
    if pid := data.get("proposal_id"):
        proposal = EventProposal.objects.filter(
            id=pid, submitted_by=request.user
        ).first()
        
        # Don't autosave if proposal is already submitted
        if proposal and proposal.status != "draft":
            return JsonResponse({"success": False, "error": "Cannot modify submitted proposal"}, status=400)

    form = EventProposalForm(data, instance=proposal, user=request.user)
    faculty_ids = data.get("faculty_incharges") or []
    if faculty_ids:
        form.fields['faculty_incharges'].queryset = User.objects.filter(
            Q(role_assignments__role__name=FACULTY_ROLE) | Q(id__in=faculty_ids)
        ).distinct()
    else:
        form.fields['faculty_incharges'].queryset = User.objects.filter(
            role_assignments__role__name=FACULTY_ROLE
        ).distinct()

    if not form.is_valid():
        logger.debug("autosave_proposal form errors: %s", form.errors)
        return JsonResponse({"success": False, "errors": form.errors}, status=400)

    proposal = form.save(commit=False)
    proposal.submitted_by = request.user
    proposal.status = "draft"
    proposal.save()
    form.save_m2m()               # 🆕 keep M2M in sync
    _save_text_sections(proposal, data)

    errors = {}

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
            else:
                missing[field] = "This field is required."
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
        if particulars or participants or rate or amount:
            if not particulars:
                missing["particulars"] = "This field is required."
            if not participants:
                missing["participants"] = "This field is required."
            if not rate:
                missing["rate"] = "This field is required."
            if not amount:
                missing["amount"] = "This field is required."
        if missing:
            in_errors[in_idx] = missing
        in_idx += 1
    if in_errors:
        errors["income"] = in_errors

    if errors:
        logger.debug("autosave_proposal dynamic errors: %s", errors)
        return JsonResponse({"success": False, "errors": errors}, status=400)

    _save_activities(proposal, data)
    _save_speakers(proposal, data, request.FILES)
    _save_expenses(proposal, data)
    _save_income(proposal, data)

    logger.debug(
        "Autosaved proposal %s with faculty %s",
        proposal.id,
        list(proposal.faculty_incharges.values_list("id", flat=True)),
    )

    return JsonResponse({"success": True, "proposal_id": proposal.id})


# ──────────────────────────────────────────────────────────────
#  Remaining steps (unchanged)
# ──────────────────────────────────────────────────────────────
@login_required
def submit_need_analysis(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id,
                                 submitted_by=request.user)
    instance = EventNeedAnalysis.objects.filter(proposal=proposal).first()

    if request.method == "POST":
        form = NeedAnalysisForm(request.POST, instance=instance)
        logger.debug("NeedAnalysis POST data: %s", request.POST)
        if form.is_valid():
            need = form.save(commit=False)
            need.proposal = proposal
            need.save()
            logger.debug("NeedAnalysis saved for proposal %s", proposal.id)
            return redirect("emt:submit_objectives", proposal_id=proposal.id)
    else:
        form = NeedAnalysisForm(instance=instance)

    return render(request, "emt/need_analysis.html",
                  {"form": form, "proposal": proposal})


@login_required
def submit_objectives(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id,
                                 submitted_by=request.user)
    instance = EventObjectives.objects.filter(proposal=proposal).first()

    if request.method == "POST":
        form = ObjectivesForm(request.POST, instance=instance)
        logger.debug("Objectives POST data: %s", request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.proposal = proposal
            obj.save()
            logger.debug("Objectives saved for proposal %s", proposal.id)
            return redirect("emt:submit_expected_outcomes",
                            proposal_id=proposal.id)
    else:
        form = ObjectivesForm(instance=instance)

    return render(request, "emt/objectives.html",
                  {"form": form, "proposal": proposal})


@login_required
def submit_expected_outcomes(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id,
                                 submitted_by=request.user)
    instance = EventExpectedOutcomes.objects.filter(proposal=proposal).first()

    if request.method == "POST":
        form = ExpectedOutcomesForm(request.POST, instance=instance)
        logger.debug("ExpectedOutcomes POST data: %s", request.POST)
        if form.is_valid():
            outcome = form.save(commit=False)
            outcome.proposal = proposal
            outcome.save()
            logger.debug("ExpectedOutcomes saved for proposal %s", proposal.id)
            return redirect("emt:submit_tentative_flow",
                            proposal_id=proposal.id)
    else:
        form = ExpectedOutcomesForm(instance=instance)

    return render(request, "emt/submit_expected_outcomes.html",
                  {"form": form, "proposal": proposal})


@login_required
def submit_tentative_flow(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id,
                                 submitted_by=request.user)
    instance = TentativeFlow.objects.filter(proposal=proposal).first()

    if request.method == "POST":
        form = TentativeFlowForm(request.POST, instance=instance)
        logger.debug("TentativeFlow POST data: %s", request.POST)
        if form.is_valid():
            flow = form.save(commit=False)
            flow.proposal = proposal
            flow.save()
            logger.debug("TentativeFlow saved for proposal %s", proposal.id)
            return redirect("emt:submit_speaker_profile",
                            proposal_id=proposal.id)
    else:
        form = TentativeFlowForm(instance=instance)

    return render(request, "emt/tentative_flow.html",
                  {"form": form, "proposal": proposal})

# ──────────────────────────────
# PROPOSAL STEP 6: Speaker Profile
# ──────────────────────────────
@login_required
def submit_speaker_profile(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id,
                                 submitted_by=request.user)
    SpeakerFS = modelformset_factory(
        SpeakerProfile, form=SpeakerProfileForm, extra=1, can_delete=True
    )

    if request.method == "POST":
        formset = SpeakerFS(request.POST, request.FILES,
                            queryset=SpeakerProfile.objects.filter(
                                proposal=proposal))
        if formset.is_valid():
            objs = formset.save(commit=False)
            for obj in objs:
                obj.proposal = proposal
                obj.save()
            for obj in formset.deleted_objects:
                obj.delete()
            return redirect("emt:submit_expense_details",
                            proposal_id=proposal.id)
    else:
        formset = SpeakerFS(queryset=SpeakerProfile.objects.filter(
            proposal=proposal))

    return render(request, "emt/speaker_profile.html",
                  {"formset": formset, "proposal": proposal})

# ──────────────────────────────
# PROPOSAL STEP 7: Expense Details
# ──────────────────────────────
@login_required
def submit_expense_details(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id,
                                 submitted_by=request.user)
    ExpenseFS = modelformset_factory(
        ExpenseDetail, form=ExpenseDetailForm, extra=1, can_delete=True
    )

    if request.method == "POST":
        formset = ExpenseFS(request.POST, queryset=ExpenseDetail.objects.filter(
            proposal=proposal))
        if formset.is_valid():
            objs = formset.save(commit=False)
            for obj in objs:
                obj.proposal = proposal
                obj.save()
            for obj in formset.deleted_objects:
                obj.delete()

            return redirect("emt:submit_cdl_support", proposal_id=proposal.id)
    else:
        formset = ExpenseFS(queryset=ExpenseDetail.objects.filter(
            proposal=proposal))

    return render(request, "emt/expense_details.html",
                  {"proposal": proposal, "formset": formset})


# ──────────────────────────────
# PROPOSAL STEP 8: CDL Support
# ──────────────────────────────
@login_required
def submit_cdl_support(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id, submitted_by=request.user)
    instance = getattr(proposal, "cdl_support", None)

    if request.method == "POST":
        form = CDLSupportForm(request.POST, instance=instance)
        if form.is_valid():
            support = form.save(commit=False)
            support.proposal = proposal
            support.support_options = form.cleaned_data.get("support_options", [])
            support.save()

            proposal.status = "submitted"
            proposal.save()

            from emt.utils import build_approval_chain
            build_approval_chain(proposal)

            messages.success(request, "Your event proposal has been submitted for approval.")
            return redirect("dashboard")
    else:
        initial = {}
        if instance:
            initial["support_options"] = instance.support_options
        form = CDLSupportForm(instance=instance, initial=initial)

    return render(request, "emt/cdl_support.html", {"form": form, "proposal": proposal})



# ──────────────────────────────
# Event Management Suite Dashboard
# ──────────────────────────────
@login_required
def proposal_status_detail(request, proposal_id):
    proposal = get_object_or_404(
        EventProposal.objects.select_related('organization', 'submitted_by')
        .prefetch_related('sdg_goals', 'faculty_incharges'),
        id=proposal_id,
        submitted_by=request.user
    )
    
    if request.method == 'POST':
        action = request.POST.get('action') # Assuming you get 'approve' or 'reject' from a form

        if action == 'approve':
            proposal.status = 'Approved' # Use your actual status value
            
            # Add the logging statement for approval
            logger.info(
                f"User '{request.user.username}' APPROVED proposal '{proposal.title}' (ID: {proposal.id})."
            )
            
            proposal.save()

        elif action == 'reject':
            proposal.status = 'Rejected' # Use your actual status value
            rejection_reason = request.POST.get('reason', 'No reason provided')
            
            # Add the logging statement for rejection
            logger.warning(
                f"User '{request.user.username}' REJECTED proposal '{proposal.title}' (ID: {proposal.id}). "
                f"Reason: {rejection_reason}"
            )
            
            proposal.save()
            
        return redirect('some-success-url')

    # Get approval steps
    all_steps = (
        ApprovalStep.objects.filter(proposal=proposal).order_by("order_index")
    )
    visible_steps = all_steps.visible_for_ui()

    # Total budget calculation
    budget_total = ExpenseDetail.objects.filter(
        proposal=proposal
    ).aggregate(total=Sum('amount'))['total'] or 0

    # ✅ Dynamically assign statuses
    db_status = (proposal.status or '').strip().lower()

    if db_status == 'rejected':
        statuses = ['draft', 'submitted', 'under_review', 'rejected']
    else:
        statuses = ['draft', 'submitted', 'under_review', 'finalized']

    status_index = statuses.index(db_status) if db_status in statuses else 0
    # Progress should start at 0% for the initial status
    if len(statuses) > 1:
        progress_percent = int(status_index * 100 / (len(statuses) - 1))
    else:
        progress_percent = 100
    current_label = statuses[status_index].replace('_', ' ').capitalize()

    return render(request, 'emt/proposal_status_detail.html', {
        'proposal': proposal,
        'steps': visible_steps,
        'all_steps': all_steps,
        'budget_total': budget_total,
        'statuses': statuses,
        'status_index': status_index,
        'progress_percent': progress_percent,
        'current_label': current_label,
    })

# ──────────────────────────────
# PENDING REPORTS, GENERATION, SUCCESS
# ──────────────────────────────

@login_required
def pending_reports(request):
    proposals = EventProposal.objects.filter(
        submitted_by=request.user,
        status__in=['approved', 'finalized'],
        report_generated=False
    ).select_related('report_assigned_to')
    return render(request, 'emt/pending_reports.html', {'proposals': proposals})


@login_required
@require_http_methods(["GET"])
def api_event_participants(request, proposal_id):
    """API endpoint to search for eligible assignees for a specific event"""
    try:
        proposal = get_object_or_404(EventProposal, id=proposal_id)

        # Check if user has permission to view this proposal
        if proposal.submitted_by != request.user and request.user not in proposal.faculty_incharges.all():
            return JsonResponse({'error': 'Permission denied'}, status=403)

        query = request.GET.get('q', '').strip().lower()

        # Collect all eligible users
        participants = set()

        # Members of the event's organization
        if proposal.organization:
            memberships = OrganizationMembership.objects.filter(organization=proposal.organization)

            # Filter by target audience roles if specified
            if proposal.target_audience:
                target_roles = [r.strip().lower() for r in proposal.target_audience.split(',')]
                memberships = memberships.filter(role__in=target_roles)

            for membership in memberships.select_related('user'):
                participants.add(membership.user)

        # Always include submitter and faculty incharges
        participants.add(proposal.submitted_by)
        for faculty in proposal.faculty_incharges.all():
            participants.add(faculty)

        # Apply search filter
        if query:
            filtered_participants = [
                user for user in participants
                if query in (user.get_full_name() or '').lower() or
                   query in user.username.lower() or
                   query in (user.email or '').lower()
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
                membership = OrganizationMembership.objects.filter(user=user, organization=proposal.organization).first()
                role = membership.role.capitalize() if membership else "Member"

            results.append({
                'id': user.id,
                'name': user.get_full_name() or user.username,
                'email': user.email,
                'role': role,
                'username': user.username
            })

        return JsonResponse({'participants': results})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def assign_report_task(request, proposal_id):
    """API endpoint to assign report generation task to a user"""
    try:
        proposal = get_object_or_404(EventProposal, id=proposal_id)
        
        # Check if user has permission to assign (only submitter can assign)
        if proposal.submitted_by != request.user:
            return JsonResponse({'error': 'Only the event submitter can assign report tasks'}, status=403)
        
        data = json.loads(request.body)
        assigned_user_id = data.get('assigned_user_id')
        
        if not assigned_user_id:
            return JsonResponse({'error': 'assigned_user_id is required'}, status=400)
        
        # Verify the assigned user is eligible for assignment
        assigned_user = get_object_or_404(User, id=assigned_user_id)

        if (assigned_user != proposal.submitted_by and
            assigned_user not in proposal.faculty_incharges.all()):

            membership_qs = OrganizationMembership.objects.filter(
                user=assigned_user,
                organization=proposal.organization,
            )

            if proposal.target_audience:
                target_roles = [r.strip().lower() for r in proposal.target_audience.split(',')]
                membership_qs = membership_qs.filter(role__in=target_roles)

            if not membership_qs.exists():
                return JsonResponse({'error': 'Can only assign to event organization members or target audience'}, status=400)
        
        # Update assignment
        proposal.report_assigned_to = assigned_user
        proposal.report_assigned_at = timezone.now()
        proposal.save()
        
        return JsonResponse({
            'success': True,
            'assigned_to': {
                'id': assigned_user.id,
                'name': assigned_user.get_full_name() or assigned_user.username,
                'email': assigned_user.email
            },
            'assigned_at': proposal.report_assigned_at.isoformat()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def unassign_report_task(request, proposal_id):
    """API endpoint to remove report generation assignment"""
    try:
        proposal = get_object_or_404(EventProposal, id=proposal_id)
        
        # Check if user has permission to unassign (only submitter can unassign)
        if proposal.submitted_by != request.user:
            return JsonResponse({'error': 'Only the event submitter can unassign report tasks'}, status=403)
        
        # Remove assignment
        proposal.report_assigned_to = None
        proposal.report_assigned_at = None
        proposal.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def generate_report(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id, submitted_by=request.user)
    # TODO: Add your real PDF/Word generation logic here!
    proposal.report_generated = True
    proposal.save()
    return redirect('emt:report_success', proposal_id=proposal.id)

    report = EventReport.objects.get(id=report_id)
    
    # ... your existing logic to gather data for the AI ...
    
    try:
        # Call your AI service to get the report content
        generated_text = ai_report_service.create_summary(report)
        report.ai_generated_report = generated_text
        report.save()

        # Add the logging statement here
        logger.info(
            f"User '{request.user.username}' generated an AI report for event "
            f"'{report.event.title}' (Report ID: {report.id})."
        )
        
    except Exception as e:
        logger.error(f"Failed to generate AI report for Report ID {report.id}: {e}")
        # Handle the error

@login_required
def report_success(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id)
    return render(request, 'emt/report_success.html', {'proposal': proposal})

@login_required
def generated_reports(request):
    reports = EventProposal.objects.filter(report_generated=True, submitted_by=request.user).order_by('-id')
    return render(request, 'emt/generated_reports.html', {'reports': reports})

@login_required
def view_report(request, report_id):
    report = get_object_or_404(EventProposal, id=report_id, submitted_by=request.user, report_generated=True)
    return render(request, 'emt/view_report.html', {'report': report})

    """
    Displays the details of a single event report.
    """
    # Get the report object, or return a 404 error if not found
    report = get_object_or_404(EventReport, id=report_id)

    # Add the logging statement here, right after fetching the object
    logger.info(
        f"User '{request.user.username}' viewed the report for event "
        f"'{report.event.title}' (Report ID: {report.id})."
    )

    # Render the template with the report data
    context = {
        'report': report
    }
    return render(request, 'emt/view_report.html', context)

# ──────────────────────────────
# FILE DOWNLOAD (PLACEHOLDER)
# ──────────────────────────────

@login_required
def download_pdf(request, proposal_id):
    # TODO: Implement actual PDF generation and return the file
    return HttpResponse(f"PDF download for Proposal {proposal_id}", content_type='application/pdf')

    report = EventReport.objects.get(id=report_id)
    
    # Assuming you have a utility to render a template to a PDF
    try:
        pdf_file = render_to_pdf('emt/pdf_template.html', {'report': report})

        # Add the logging statement here
        logger.info(
            f"User '{request.user.username}' downloaded the PDF report for event "
            f"'{report.event.title}' (Report ID: {report.id})."
        )

        # Return the PDF as an HTTP response
        return HttpResponse(pdf_file, content_type='application/pdf')

    except Exception as e:  
        logger.error(f"Failed to generate PDF for Report ID {report.id}: {e}")
        # Handle the error

@login_required
def download_word(request, proposal_id):
    # TODO: Implement actual Word generation and return the file
    return HttpResponse(
        f"Word download for Proposal {proposal_id}",
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

# ──────────────────────────────
# AUTOSAVE Need Analysis (if you use autosave)
# ──────────────────────────────
@csrf_exempt
@login_required
def autosave_need_analysis(request):
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        proposal_id = data.get('proposal_id')
        content = data.get('content', '')
        proposal = EventProposal.objects.get(id=proposal_id, submitted_by=request.user)
        na, created = EventNeedAnalysis.objects.get_or_create(proposal=proposal)
        na.content = content
        na.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

@login_required
def api_organizations(request):
    q = request.GET.get("q", "").strip()
    org_type = request.GET.get("org_type", "").strip()  # e.g., "Department", "Club", etc.
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

    users = User.objects.filter(
        role_assignments__role__name__icontains="faculty"
    )
    if org_id:
        users = users.filter(role_assignments__organization_id=org_id)

    users = (
        users
        .filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
        )
        .distinct()
        .order_by("first_name")[:20]
    )
    return JsonResponse(
        [{"id": u.id, "text": f"{u.get_full_name() or u.username} ({u.email})"} for u in users],
        safe=False
    )


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
    data = [
        {"id": u.id, "text": u.get_full_name() or u.username}
        for u in users
    ]
    return JsonResponse(data, safe=False)


@login_required
@require_http_methods(["GET"])
def api_classes(request, org_id):
    """Return classes and their students for an organization."""
    try:
        classes = (
            Class.objects
            .filter(organization_id=org_id, is_active=True)
            .prefetch_related('students__user')
            .order_by('name')
        )
        data = []
        for cls in classes:
            students = [
                {
                    'id': s.user.id,
                    'name': s.user.get_full_name() or s.user.username,
                }
                for s in cls.students.all()
            ]
            data.append({
                'id': cls.id,
                'name': cls.name,
                'code': cls.code,
                'students': students,
            })
        return JsonResponse({'success': True, 'classes': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


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
    from core.models import Program, ProgramOutcome, ProgramSpecificOutcome, Organization
    try:
        org = Organization.objects.get(id=org_id)
    except Organization.DoesNotExist:
        return JsonResponse({"success": False, "error": "Organization not found"}, status=404)

    programs = Program.objects.filter(organization=org)
    pos = []
    psos = []
    if programs.exists():
        program = programs.first()
        pos = list(ProgramOutcome.objects.filter(program=program).values("id", "description"))
        psos = list(ProgramSpecificOutcome.objects.filter(program=program).values("id", "description"))

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
@user_passes_test(lambda u: getattr(getattr(u, 'profile', None), 'role', '') != 'student')
def review_approval_step(request, step_id):
    step = get_object_or_404(ApprovalStep, id=step_id)

    # Fetch the proposal along with all related details in one go.
    proposal = (
        EventProposal.objects
        .select_related(
            "need_analysis",
            "objectives",
            "expected_outcomes",
            "tentative_flow",
        )
        .prefetch_related("speakers", "expense_details", "faculty_incharges", "sdg_goals")
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
    if step.assigned_to_id == request.user.id and step.status == ApprovalStep.Status.PENDING:
        optional_candidates = list(get_downstream_optional_candidates(step))
        show_optional_picker = len(optional_candidates) > 0

    history_steps = proposal.approval_steps.visible_for_ui().order_by("order_index")

    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment', '')
        forward_flag = bool(request.POST.get("forward_to_optionals"))
        selected_optionals = request.POST.getlist("optional_step_ids")

        if action == 'approve':
            step.status = ApprovalStep.Status.APPROVED
            step.approved_by = request.user
            step.approved_at = timezone.now()
            step.decided_by = request.user
            step.decided_at = step.approved_at
            step.comment = comment
            step.save()

            auto_approve_non_optional_duplicates(step.proposal, request.user, request.user)

            if forward_flag and selected_optionals:
                unlock_optionals_after(step, selected_optionals)
            else:
                skip_all_downstream_optionals(step)

            def activate_next(current_order):
                next_step = (
                    ApprovalStep.objects.filter(
                        proposal=proposal,
                        step_order__gt=current_order,
                    )
                    .order_by("step_order")
                    .first()
                )
                if not next_step:
                    return
                if next_step.status == 'waiting':
                    next_step.status = 'pending'
                    next_step.save()
                else:
                    activate_next(next_step.step_order)

            activate_next(step.step_order)

            if ApprovalStep.objects.filter(proposal=proposal, status='pending').exists():
                proposal.status = 'under_review'
            else:
                proposal.status = 'finalized'
            proposal.save()
            messages.success(request, 'Proposal approved.')
            return redirect('emt:my_approvals')

        elif action == 'reject':
            if not comment.strip():
                messages.error(request, 'Comment is required to reject the proposal.')
            else:
                step.status = ApprovalStep.Status.REJECTED
                step.comment = comment
                step.approved_by = request.user
                step.approved_at = timezone.now()
                step.decided_by = request.user
                step.decided_at = step.approved_at
                proposal.status = 'rejected'
                proposal.save()
                step.save()
                messages.error(request, 'Proposal rejected.')
                return redirect('emt:my_approvals')
        else:
            return redirect('emt:my_approvals')

    return render(
        request,
        'emt/review_approval_step.html',
        {
            'step': step,
            'proposal': proposal,
            'need_analysis': need_analysis,
            'objectives': objectives,
            'outcomes': outcomes,
            'flow': flow,
            'speakers': speakers,
            'expenses': expenses,
            'optional_candidates': optional_candidates,
            'show_optional_picker': show_optional_picker,
            'history_steps': history_steps,
        },
    )

@login_required
def submit_event_report(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id, submitted_by=request.user)

    # Only allow if no report exists yet
    report, created = EventReport.objects.get_or_create(proposal=proposal)
    AttachmentFormSet = modelformset_factory(EventReportAttachment, form=EventReportAttachmentForm, extra=2, can_delete=True)

    if request.method == "POST":
        form = EventReportForm(request.POST, instance=report)
        formset = AttachmentFormSet(request.POST, request.FILES, queryset=report.attachments.all())
        if form.is_valid() and formset.is_valid():
            report = form.save(commit=False)
            report.proposal = proposal
            report.save()
            form.save_m2m()

            # Save attachments
            instances = formset.save(commit=False)
            for obj in instances:
                obj.report = report
                obj.save()
            for obj in formset.deleted_objects:
                obj.delete()
            messages.success(request, "Report submitted successfully! Starting AI generation...")
            # Directly redirect to streaming AI progress page
            return redirect('emt:ai_report_progress', proposal_id=proposal.id)
    else:
        form = EventReportForm(instance=report)
        formset = AttachmentFormSet(queryset=report.attachments.all())

    # Pre-fill context with proposal info for readonly/preview display
    context = {
        "proposal": proposal,
        "form": form,
        "formset": formset,
    }
    return render(request, "emt/submit_event_report.html", context)

@login_required
def suite_dashboard(request):
    """
    Show current user's proposals excluding finalized ones older than 2 days.
    Compute per-proposal progress for display in dashboard.html.
    """
    # 1) Get proposals excluding finalized + 2-day-old ones
    user_proposals = (
        EventProposal.objects
        .filter(submitted_by=request.user)
        .exclude(
            status='finalized',
            updated_at__lt=now() - timedelta(days=2)
        )
        .prefetch_related('approval_steps')
        .order_by('-updated_at')
    )

    # 2) Prepare statuses and UI fields
    for p in user_proposals:
        db_status = (p.status or '').strip().lower()

        if db_status == 'rejected':
            p.statuses = ['draft', 'submitted', 'under_review', 'rejected']
        else:
            p.statuses = ['draft', 'submitted', 'under_review', 'finalized']

        p.status_index = p.statuses.index(db_status) if db_status in p.statuses else 0
        p.progress_percent = int(p.status_index * 100 / (len(p.statuses) - 1)) if len(p.statuses) > 1 else 100
        p.current_label = p.statuses[p.status_index].replace('_', ' ').capitalize()

    # 3) Approvals card visibility
    is_student = getattr(getattr(request.user, 'profile', None), 'role', '') == 'student'
    show_approvals_card = not is_student

    # 4) Return dashboard with user_proposals
    return render(request, 'dashboard.html', {
        'user_proposals': user_proposals,
        'show_approvals_card': show_approvals_card,
    })
@login_required
def ai_generate_report(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id)
    # Always ensure there is a report
    report, _ = EventReport.objects.get_or_create(proposal=proposal)
    return render(request, 'emt/ai_generate_report.html', {
        'proposal': proposal,
        'report': report,
    })

@csrf_exempt
def generate_ai_report(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            prompt = f"""
            You are an expert in academic event reporting for university IQAC documentation.
            Generate a detailed, formal, and highly structured IQAC-style event report using the following data.
            **Follow the given format strictly**. Use professional, concise, academic language. Format all sections as shown, and fill any missing info sensibly if needed.

            ---
            # EVENT INFORMATION
            | Field                | Value                         |
            |----------------------|-------------------------------|
            | Department           | {data.get('department','')} |
            | Location             | {data.get('location','')} |
            | Event Title          | {data.get('event_title','')} |
            | No of Activities     | {data.get('no_of_activities','1')} |
            | Date and Time        | {data.get('event_datetime','')} |
            | Venue                | {data.get('venue','')} |
            | Academic Year        | {data.get('academic_year','')} |
            | Event Type (Focus)   | {data.get('event_focus_type','')} |

            # PARTICIPANTS INFORMATION
            | Field                   | Value                      |
            |-------------------------|----------------------------|
            | Target Audience         | {data.get('target_audience','')} |
            | Organising Committee    | {data.get('organising_committee_details','')} |
            | No of Student Volunteers| {data.get('no_of_volunteers','')} |
            | No of Attendees         | {data.get('no_of_attendees','')} |

            # SUMMARY OF THE OVERALL EVENT
            {data.get('summary','(Please write a 2–3 paragraph formal summary of the event. Cover objectives, flow, engagement, and outcomes.)')}

            # OUTCOMES OF THE EVENT
            {data.get('outcomes','- List 3–5 major outcomes, in bullets.')}

            # ANALYSIS
            - Impact on Attendees: {data.get('impact_on_attendees','')}
            - Impact on Schools: {data.get('impact_on_schools','')}
            - Impact on Volunteers: {data.get('impact_on_volunteers','')}

            # RELEVANCE OF THE EVENT
            | Criteria                | Description                 |
            |-------------------------|-----------------------------|
            | Graduate Attributes     | {data.get('graduate_attributes','')} |
            | Support to SDGs/Values  | {data.get('sdg_value_systems_mapping','')} |

            # SUGGESTIONS FOR IMPROVEMENT / FEEDBACK FROM IQAC
            {data.get('iqac_feedback','')}

            # ATTACHMENTS/EVIDENCE
            {data.get('attachments','- List any evidence (photos, worksheets, etc.) if available.')}

            ---

            ## Ensure the final output is clear, formal, and as per IQAC standards. DO NOT leave sections blank, fill with professional-sounding content if data is missing.
            """

            model = genai.GenerativeModel("models/gemini-1.5-pro-latest")
            response = model.generate_content(prompt)

            # Google GenAI occasionally returns None
            if not response or not hasattr(response, 'text'):
                return JsonResponse({'error': 'AI did not return any text.'}, status=500)

            return JsonResponse({'report_text': response.text})

        except Exception as e:
            print("AI Generation error:", e)
            return JsonResponse({'error': str(e)}, status=500)


    return JsonResponse({'error': 'Only POST allowed'}, status=405)

@csrf_exempt
@login_required
def save_ai_report(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        proposal = get_object_or_404(EventProposal, id=data['proposal_id'], submitted_by=request.user)
        report, _ = EventReport.objects.get_or_create(proposal=proposal)
        report.summary = data.get('full_text')[:1000]  # or whatever logic
        report.save()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'POST only'}, status=405)
@login_required
def ai_report_progress(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id)
    return render(request, 'emt/ai_report_progress.html', {'proposal': proposal})
@csrf_exempt
@login_required
def ai_report_partial(request, proposal_id):
    from .models import EventReport
    import random
    import time
    report = EventReport.objects.filter(proposal_id=proposal_id).first()
    if not report or not report.summary:
        # Simulate progress if nothing generated yet
        return JsonResponse({'text': "", 'status': 'in_progress'})
    # For now, always show the full summary and mark as finished
    return JsonResponse({'text': report.summary, 'status': 'finished'})
from django.http import StreamingHttpResponse

@login_required
def generate_ai_report_stream(request, proposal_id):
    import time

    proposal = get_object_or_404(EventProposal, id=proposal_id)
    # Compose strict, flat prompt!
    prompt = f"""
You are an academic event reporting assistant. 
Output an IQAC Event Report using the following fields, one per line, in the exact order, using **plain text** and a colon after each field name. Do NOT use Markdown or bullets, just FIELD: VALUE format. 
If a value is missing, write "To be filled".

Event Title: {proposal.event_title or "To be filled"}
Date & Time: {proposal.event_datetime or "To be filled"}
Venue: {proposal.venue or "To be filled"}
Academic Year: {proposal.academic_year or "To be filled"}
Focus / Objective: {getattr(proposal, 'event_focus_type', '') or "To be filled"}
Target Audience: {getattr(proposal, 'target_audience', '') or "To be filled"}
Organizing Department: {getattr(proposal, 'department', '') or "To be filled"}
No. of Participants: To be filled

Event Summary: [Write a concise, formal event summary.]
Outcomes: [List 2-3 major outcomes.]
Feedback & Suggestions: [Summarize participant feedback.]
Recommendations: [Give 1-2 improvements.]
Attachments: [List any supporting docs, if any.]

Prepared by: AI Assistant
Date of Submission: To be filled
Approved by: To be filled

Repeat: Output each field as FIELD: VALUE (colon required), one per line, nothing else. No Markdown, no formatting, no section headings, no empty lines.
    """

    model = genai.GenerativeModel("models/gemini-1.5-pro-latest")

    def generate():
        for chunk in model.generate_content(prompt, stream=True):
            text = getattr(chunk, 'text', '')
            if text:
                yield text
                time.sleep(0.03)

    return StreamingHttpResponse(generate(), content_type='text/plain')

@login_required
def admin_dashboard(request):
    """
    Render the static admin dashboard template.
    """
    return render(request, 'core/admin_dashboard.html')

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
        Please regenerate the IQAC Event Report as before, but follow these special user instructions: 
        ---
        {instructions}
        ---
        {manual_fields}
        ---
        Use the same field structure as before.
        """

        # Call Gemini here or set a session variable with prompt and redirect to progress
        request.session['ai_custom_prompt'] = ai_prompt
        return redirect('emt:ai_report_progress', proposal_id=proposal.id)

    # Pre-fill manual_fields with last generated report fields if you want
    return render(request, "emt/ai_report_edit.html", {
        "proposal": proposal,
        "last_instructions": last_instructions,
        "last_fields": last_fields,
    })
@login_required
def ai_report_submit(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id, submitted_by=request.user)
    # Mark the report as generated/submitted
    proposal.report_generated = True
    proposal.status = "finalized"   # Or "submitted", depending on your workflow
    proposal.save()
    # Optionally, add a success message here
    from django.contrib import messages
    messages.success(request, "Event report submitted successfully!")
    return redirect('emt:report_success', proposal_id=proposal.id)

@user_passes_test(lambda u: u.is_superuser)
def api_organization_types(request):
    org_types = OrganizationType.objects.filter(is_active=True).order_by('name')
    data = [{"id": ot.name.lower(), "name": ot.name} for ot in org_types]
    return JsonResponse(data, safe=False)

# ------------------------------------------------------------------
# │ NEW FUNCTION ADDED BELOW                                       │
# ------------------------------------------------------------------


from core.models import Report

@login_required
def admin_reports_view(request):
    try:
        submitted_reports = Report.objects.all()
        generated_reports = EventReport.objects.select_related('proposal').all()

        all_reports_list = list(chain(submitted_reports, generated_reports))

        all_reports_list.sort(key=attrgetter('created_at'), reverse=True)

        context = {'reports': all_reports_list}

        return render(request, 'core/admin_reports.html', context)

    except Exception as e:
        print(f"Error in admin_reports_view: {e}")
        return HttpResponse(f"An error occurred: {e}", status=500)
def _ollama_chat(model, system, user, max_tokens=220, temp=0.4):
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temp,
        "max_tokens": max_tokens,
    }
    r = requests.post(
        f"{OLLAMA_BASE}/v1/chat/completions",
        headers={"Content-Type": "application/json"},
        data=json.dumps(body),
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


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


NEED_PROMPT = "Write a concise, factual Need Analysis (80–140 words) for the event." 
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
        return JsonResponse({"error": f"Unexpected error: {exc}"}, status=500)


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
        return JsonResponse({"ok": False, "error": f"Unexpected error: {exc}"}, status=500)


@login_required
@require_POST
def generate_expected_outcomes(request):
    ctx = _basic_info_context(request.POST)
    if not ctx:
        return JsonResponse({"ok": False, "error": "No context"}, status=400)
    try:
        text = _ollama_chat(GEN_MODEL, OUT_PROMPT, ctx, max_tokens=200, temp=0.4)
        return JsonResponse({"ok": True, "text": text})
    except Exception as exc:
        logger.error("Expected outcomes generation failed: %s", exc)
        return JsonResponse({"ok": False, "error": "AI service unavailable"}, status=503)
