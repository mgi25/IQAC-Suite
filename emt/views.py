from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import JsonResponse
from django.db.models import Q
from .models import (
    EventProposal, EventNeedAnalysis, EventObjectives,
    EventExpectedOutcomes, TentativeFlow,
    ExpenseDetail, SpeakerProfile
)
from .forms import (
    EventProposalForm, NeedAnalysisForm, ExpectedOutcomesForm,
    ObjectivesForm, TentativeFlowForm, SpeakerProfileForm,
    ExpenseDetailForm
)
from django.forms import modelformset_factory
from .models import Department           # FK model you created
from django.contrib.auth.models import User
from emt.utils import create_approval_steps
from emt.models import ApprovalStep
from django.contrib import messages
from django.utils import timezone
# ──────────────────────────────
# PROPOSAL STEP 1: Proposal Submission
# ──────────────────────────────
@login_required
def submit_proposal(request, pk=None):
    proposal = None
    if pk:
        proposal = get_object_or_404(
            EventProposal, pk=pk, submitted_by=request.user
        )

    if request.method == "POST":
        post_data = request.POST.copy()

        # ——— Normalize department field
        dept_value = post_data.get("department")
        if dept_value and not dept_value.isdigit():
            dept_obj, _ = Department.objects.get_or_create(name=dept_value)
            post_data["department"] = str(dept_obj.id)

        form = EventProposalForm(post_data, instance=proposal)
        if form.is_valid():
            proposal = form.save(commit=False)
            proposal.submitted_by = request.user
            proposal.status = "draft"   # always draft at this stage
            proposal.save()
            form.save_m2m()             # Save faculty in-charges

            return redirect("emt:submit_need_analysis", proposal_id=proposal.id)
    else:
        form = EventProposalForm(instance=proposal)

    return render(request, "emt/submit_proposal.html",
                  {"form": form, "proposal": proposal})

# ──────────────────────────────────────────────────────────────
#  Autosave draft (XHR from JS)
# ──────────────────────────────────────────────────────────────
@csrf_exempt
@login_required
def autosave_proposal(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    data = json.loads(request.body.decode("utf-8"))

    # Same dept text-to-ID conversion as above
    if (dept_val := data.get("department")) and not str(dept_val).isdigit():
        dept_obj, _ = Department.objects.get_or_create(name=dept_val)
        data["department"] = str(dept_obj.id)

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
            from emt.utils import create_approval_steps
            create_approval_steps(proposal)

            messages.success(request, "Your event proposal has been submitted for approval.")
            return redirect("dashboard")
    else:
        formset = ExpenseFS(queryset=ExpenseDetail.objects.filter(
            proposal=proposal))

    return render(request, "emt/expense_details.html",
                  {"proposal": proposal, "formset": formset})


# ──────────────────────────────
# STATUS PAGE
# ──────────────────────────────
@login_required
def proposal_status(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id, submitted_by=request.user)
    return render(request, 'emt/proposal_status.html', {'proposal': proposal})

# ──────────────────────────────
# IQAC Suite Dashboard
# ──────────────────────────────
@login_required
def iqac_suite_dashboard(request):
    user = request.user
    # DEBUG >>> ------------------------------------------
    ras = list(user.role_assignments.all())
    print("DEBUG – role_assignments for", user.username, ":", ras)
    print("DEBUG – raw roles:", [ra.role for ra in ras])
    # <<< -----------------------------------------------

    roles = {ra.role for ra in ras}
    approval_roles = {
        "faculty", "dept_iqac", "hod", "dean",
        "director", "club_head", "center_head",
    }
    show_approvals_card = bool(roles & approval_roles)
    return render(
        request,
        "emt/iqac_suite_dashboard.html",
        {"show_approvals_card": show_approvals_card},
    )


# ──────────────────────────────
# PENDING REPORTS, GENERATION, SUCCESS
# ──────────────────────────────

@login_required
def pending_reports(request):
    proposals = EventProposal.objects.filter(report_generated=False, submitted_by=request.user)
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
def api_departments(request):
    q = request.GET.get("q", "").strip()
    depts = Department.objects.filter(name__icontains=q).order_by("name")[:20]
    response = [{"id": d.id, "text": d.name} for d in depts]
    return JsonResponse(response, safe=False)

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

    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment', '')

        # HOD special: can trigger finance/dean steps
        needs_finance_approval = False
        is_big_event = False

        if step.role_required == 'hod' and action == 'approve':
            needs_finance_approval = bool(request.POST.get('needs_finance_approval'))
            is_big_event = bool(request.POST.get('is_big_event'))
            proposal.needs_finance_approval = needs_finance_approval
            proposal.is_big_event = is_big_event
            proposal.save()

        if action == 'approve':
            step.status = 'approved'
            step.approved_by = request.user
            step.approved_at = timezone.now()
            step.comment = comment
            step.save()

            # If this is HOD and extra approval is needed, add steps now
            if step.role_required == 'hod':
                from emt.utils import create_additional_approval_steps
                create_additional_approval_steps(proposal, starting_step=step.step_order + 1)

            # Move proposal to next step if exists
            next_step = ApprovalStep.objects.filter(proposal=step.proposal, step_order=step.step_order+1).first()
            if next_step:
                step.proposal.status = 'under_review'
            else:
                # Last approval
                step.proposal.status = 'approved'
            step.proposal.save()
            messages.success(request, 'Proposal approved.')
        elif action == 'reject':
            step.status = 'rejected'
            step.comment = comment
            step.approved_by = request.user
            step.approved_at = timezone.now()
            step.proposal.status = 'rejected'
            step.proposal.save()
            step.save()
            messages.error(request, 'Proposal rejected.')
        return redirect('emt:my_approvals')

    return render(request, 'emt/review_approval_step.html', {'step': step})