from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import JsonResponse
from django.db.models import Q
from .models import (
    EventProposal, EventNeedAnalysis, EventObjectives,
    EventExpectedOutcomes, TentativeFlow,
    ExpenseDetail, SpeakerProfile,EventReport, EventReportAttachment
)
from .forms import (
    EventProposalForm, NeedAnalysisForm, ExpectedOutcomesForm,
    ObjectivesForm, TentativeFlowForm, SpeakerProfileForm,
    ExpenseDetailForm,EventReportForm, EventReportAttachmentForm
)
from django.forms import modelformset_factory
from core.models import Organization, OrganizationType, Report as SubmittedReport    # FK model you created AND the submitted report model
from django.contrib.auth.models import User
from emt.utils import build_approval_chain
from emt.models import ApprovalStep
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

# ──────────────────────────────
# CDL DASHBOARD
# ──────────────────────────────
# Configure Gemini API key from environment variable
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
def cdl_dashboard(request):
    return render(request, 'emt/cdl_dashboard.html')

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

    return render(request, 'cdl/cdl_submit_request.html')

@login_required
def my_requests_view(request):
    requests = MediaRequest.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'cdl/cdl_my_requests.html', {'requests': requests})

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

# ──────────────────────────────
# PROPOSAL STEP 1: Proposal Submission
# ──────────────────────────────
@login_required
def submit_proposal(request, pk=None):
    # --- Academic year: set a default if missing (for demo/dev, set your real logic as needed) ---
    if not request.session.get('selected_academic_year'):
        request.session['selected_academic_year'] = "2024-2025"  # Or dynamically fetch the current active year!

    proposal = None
    if pk:
        proposal = get_object_or_404(
            EventProposal, pk=pk, submitted_by=request.user
        )

    if request.method == "POST":
        post_data = request.POST.copy()
        form = EventProposalForm(post_data, instance=proposal, selected_academic_year=request.session.get('selected_academic_year'))

        # --------- FACULTY INCHARGES QUERYSET FIX ---------
        faculty_ids = post_data.getlist("faculty_incharges")
        if faculty_ids:
            form.fields['faculty_incharges'].queryset = User.objects.filter(
                Q(role_assignments__role='faculty') | Q(id__in=faculty_ids)
            ).distinct()
        else:
            form.fields['faculty_incharges'].queryset = User.objects.filter(role_assignments__role='faculty').distinct()
        # --------------------------------------------------

    else:
        # Always get the selected academic year from session (ensured above)
        selected_academic_year = request.session.get('selected_academic_year')
        form = EventProposalForm(instance=proposal, selected_academic_year=selected_academic_year)
        # Populate all faculty as available choices for JS search/select on GET
        form.fields['faculty_incharges'].queryset = User.objects.filter(role_assignments__role__name='faculty').distinct()

    # Utility to get the display name from ID
    def get_name(model, value):
        try:
            if value:
                return model.objects.get(id=value).name
        except model.DoesNotExist:
            return ""
        return ""

    ctx = {
        "form": form,
        "proposal": proposal,
        "org_types": OrganizationType.objects.filter(is_active=True).order_by('name'),
    }

    if request.method == "POST" and form.is_valid():
        proposal = form.save(commit=False)
        proposal.submitted_by = request.user
        proposal.status = "draft"
        proposal.save()
        form.save_m2m()
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

    form = EventProposalForm(data, instance=proposal)

    if not form.is_valid():
        return JsonResponse({"success": False, "errors": form.errors}, status=400)

    proposal = form.save(commit=False)
    proposal.submitted_by = request.user
    proposal.status = "draft"
    proposal.save()
    form.save_m2m()               # 🆕 keep M2M in sync

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
        if form.is_valid():
            need = form.save(commit=False)
            need.proposal = proposal
            need.save()
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
        if form.is_valid():
            obj = form.save(commit=False)
            obj.proposal = proposal
            obj.save()
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
        if form.is_valid():
            outcome = form.save(commit=False)
            outcome.proposal = proposal
            outcome.save()
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
        if form.is_valid():
            flow = form.save(commit=False)
            flow.proposal = proposal
            flow.save()
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

            # ✅ Now mark as submitted
            proposal.status = "submitted"
            proposal.save()

            # ✅ Create approvals
            from emt.utils import build_approval_chain
            build_approval_chain(proposal)

            messages.success(request, "Your event proposal has been submitted for approval.")
            return redirect("dashboard")
    else:
        formset = ExpenseFS(queryset=ExpenseDetail.objects.filter(
            proposal=proposal))

    return render(request, "emt/expense_details.html",
                  {"proposal": proposal, "formset": formset})



# ──────────────────────────────
# IQAC Suite Dashboard
# ──────────────────────────────
@login_required
def proposal_status_detail(request, proposal_id):
    proposal = get_object_or_404(
        EventProposal,
        id=proposal_id,
        submitted_by=request.user
    )

    # Get approval steps
    approval_steps = ApprovalStep.objects.filter(
        proposal=proposal
    ).order_by('step_order')

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
    progress_percent = int((status_index + 1) * 100 / len(statuses))
    current_label = statuses[status_index].replace('_', ' ').capitalize()

    return render(request, 'emt/proposal_status_detail.html', {
        'proposal': proposal,
        'approval_steps': approval_steps,
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
    )
    return render(request, 'emt/pending_reports.html', {'proposals': proposals})


@login_required
def generate_report(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id, submitted_by=request.user)
    # TODO: Add your real PDF/Word generation logic here!
    proposal.report_generated = True
    proposal.save()
    return redirect('emt:report_success', proposal_id=proposal.id)

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

# ──────────────────────────────
# FILE DOWNLOAD (PLACEHOLDER)
# ──────────────────────────────

@login_required
def download_pdf(request, proposal_id):
    # TODO: Implement actual PDF generation and return the file
    return HttpResponse(f"PDF download for Proposal {proposal_id}", content_type='application/pdf')

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
    orgs = Organization.objects.filter(name__icontains=q, is_active=True)
    if org_type:
        orgs = orgs.filter(org_type__name=org_type)
    orgs = orgs.order_by("name")[:20]
    return JsonResponse([{"id": o.id, "text": o.name} for o in orgs], safe=False)

@login_required
def api_faculty(request):
    q = request.GET.get("q", "").strip()
    users = (User.objects
                  .filter(role_assignments__role="faculty")
                  .filter(
                      Q(first_name__icontains=q) |
                      Q(last_name__icontains=q) |
                      Q(email__icontains=q))
                  .distinct()
                  .order_by("first_name")[:20])
    return JsonResponse(
        [{"id": u.id, "text": f"{u.get_full_name() or u.username} ({u.email})"} for u in users],
        safe=False
    )


@login_required
def my_approvals(request):
    pending_steps = ApprovalStep.objects.filter(
        assigned_to=request.user,
        status='pending'
    ).select_related('proposal').order_by('step_order')
    return render(request, "emt/my_approvals.html", {
        "pending_steps": pending_steps
    })


@login_required
def review_approval_step(request, step_id):
    step = get_object_or_404(ApprovalStep, id=step_id, assigned_to=request.user)
    proposal = step.proposal

    need_analysis = getattr(proposal, "eventneedanalysis", None)
    objectives = getattr(proposal, "eventobjectives", None)
    outcomes = getattr(proposal, "eventexpectedoutcomes", None)
    flow = getattr(proposal, "tentativeflow", None)
    speakers = SpeakerProfile.objects.filter(proposal=proposal)
    expenses = ExpenseDetail.objects.filter(proposal=proposal)

    GATEKEEPER_ROLES = [
        "hod", "uni_iqac", "university_club_head", "center_head", "cell_head"
    ]

    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment', '')

        needs_academic_coord_approval = bool(request.POST.get('needs_academic_coord_approval'))
        needs_dean_approval = bool(request.POST.get('needs_dean_approval'))

        if action == 'approve':
            step.status = 'approved'
            step.approved_by = request.user
            step.approved_at = timezone.now()
            step.comment = comment
            step.save()

            # Escalation logic unchanged (add AC/Dean steps if needed)
            next_step_order = (
                ApprovalStep.objects.filter(proposal=proposal).aggregate(max_order=models.Max('step_order'))['max_order'] or 0
            ) + 1
            additional_steps = []

            def approval_exists(role):
                return ApprovalStep.objects.filter(
                    proposal=proposal,
                    role_required=role,
                    status__in=['pending', 'approved', 'waiting']
                ).exists()

            if step.role_required in GATEKEEPER_ROLES:
                if needs_academic_coord_approval and not approval_exists('academic_coordinator'):
                    acad_coord = User.objects.filter(role_assignments__role='academic_coordinator').first()
                    if acad_coord:
                        additional_steps.append(
                            ApprovalStep(
                                proposal=proposal,
                                step_order=next_step_order,
                                role_required='academic_coordinator',
                                assigned_to=acad_coord,
                                status='waiting'
                            )
                        )
                        next_step_order += 1

                if needs_dean_approval and not approval_exists('dean'):
                    dean = User.objects.filter(role_assignments__role='dean').first()
                    if dean:
                        additional_steps.append(
                            ApprovalStep(
                                proposal=proposal,
                                step_order=next_step_order,
                                role_required='dean',
                                assigned_to=dean,
                                status='waiting'
                            )
                        )
                        next_step_order += 1

            if step.role_required == "academic_coordinator":
                if needs_dean_approval and not approval_exists('dean'):
                    dean = User.objects.filter(role_assignments__role='dean').first()
                    if dean:
                        additional_steps.append(
                            ApprovalStep(
                                proposal=proposal,
                                step_order=next_step_order,
                                role_required='dean',
                                assigned_to=dean,
                                status='waiting'
                            )
                        )
                        next_step_order += 1

            if additional_steps:
                ApprovalStep.objects.bulk_create(additional_steps)

            # Sequential activation: set next step's status to 'pending'
            next_step = ApprovalStep.objects.filter(
                proposal=proposal,
                step_order=step.step_order + 1,
                status='waiting'
            ).first()
            if next_step:
                next_step.status = 'pending'
                next_step.save()

            # Proposal status logic
            if ApprovalStep.objects.filter(proposal=proposal, status='pending').exists():
                proposal.status = 'under_review'
            else:
                proposal.status = 'finalized'
            proposal.save()
            messages.success(request, 'Proposal approved.')

        elif action == 'reject':
            step.status = 'rejected'
            step.comment = comment
            step.approved_by = request.user
            step.approved_at = timezone.now()
            proposal.status = 'rejected'
            proposal.save()
            step.save()
            messages.error(request, 'Proposal rejected.')

        return redirect('emt:my_approvals')

    return render(request, 'emt/review_approval_step.html', {
        'step': step,
        'GATEKEEPER_ROLES': GATEKEEPER_ROLES,
        'need_analysis': need_analysis,
        'objectives': objectives,
        'outcomes': outcomes,
        'flow': flow,
        'speakers': speakers,
        'expenses': expenses,
    })

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
            messages.success(request, "Report submitted successfully!")
            # Redirect as needed (PDF preview/download, dashboard, etc.)
            return redirect('emt:ai_generate_report', proposal_id=proposal.id)
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
    Show all of the current user's proposals that are:
      - Not finalized older than 2 days
      - Sorted newest-first
    Also compute per-proposal progress and whether to show the "Event Approvals" card.
    """
    # 1) Grab the proposals, excluding any finalized ones last updated more than 2 days ago
    user_proposals = (
        EventProposal.objects
        .filter(submitted_by=request.user)
        .exclude(
            status='finalized',
            updated_at__lt=now() - timedelta(days=2)
        )
        .order_by('-updated_at')
    )

    # 2) Define your workflow statuses in order
    statuses_all = ['draft', 'submitted', 'under_review', 'rejected', 'finalized']
    for p in user_proposals:
        db_status = (p.status or '').strip().lower()

        if db_status == 'rejected':
            # Show only till rejected
            p.statuses = ['draft', 'submitted', 'under_review', 'rejected']
        else:
            # Normal workflow (excluding rejected if not applicable)
            p.statuses = ['draft', 'submitted', 'under_review', 'finalized']

        p.status_index = p.statuses.index(db_status) if db_status in p.statuses else 0
        p.progress_percent = int((p.status_index + 1) * 100 / len(p.statuses))
        p.current_label = p.statuses[p.status_index].replace('_', ' ').capitalize()

    # 4A) Option A: show approvals card based on the user's assigned roles
    ras = request.user.role_assignments.all()
    user_roles = { ra.role for ra in ras }
    approval_roles = {
        "faculty", "dept_iqac", "hod", "dean",
        "academic_coordinator", "club_head", "center_head",
        "association_head",
    }
    show_approvals_card = bool(user_roles & approval_roles)

    # 4B) (Optional) Or, gate by whether they actually have any pending steps:
    # show_approvals_card = ApprovalStep.objects.filter(
    #     assigned_to=request.user,
    #     status='pending'
    # ).exists()

    # 5) Render
    return render(request, 'emt/iqac_suite_dashboard.html', {
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

@login_required
def admin_reports_view(request):
    """
    Displays a combined list of all reports for the admin dashboard.
    This includes submitted reports from the 'core' app and generated
    reports from the 'emt' app.
    """
    # 1. Get all user-submitted reports from the 'core' app
    # Assuming the model in core.models is named 'Report'
    submitted_reports = SubmittedReport.objects.all()

    # 2. Get all generated event reports from the 'emt' app
    # Using 'select_related' to efficiently fetch the related proposal details
    generated_reports = EventReport.objects.select_related('proposal').all()

    # 3. Combine the two different querysets into a single Python list
    all_reports_list = list(chain(submitted_reports, generated_reports))

    # 4. Sort the combined list by their creation date in descending order
    # This assumes both models have a 'created_at' field. If not, you can
    # use a @property on each model to return a common date field.
    all_reports_list.sort(key=attrgetter('created_at'), reverse=True)

    # 5. Pass the final list to the admin reports template
    context = {
        'reports': all_reports_list
    }
    return render(request, 'core/admin_reports.html', context)