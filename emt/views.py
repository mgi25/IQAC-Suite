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
from core.models import Department,Association, Club, Center, Cell      # FK model you created
from django.contrib.auth.models import User
from emt.utils import build_approval_chain
from emt.models import ApprovalStep
from django.contrib import messages
from django.utils import timezone
from django.db import models
from .models import MediaRequest
# ──────────────────────────────
# CDL DASHBOARD
# ──────────────────────────────
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
    proposal = None
    if pk:
        proposal = get_object_or_404(
            EventProposal, pk=pk, submitted_by=request.user
        )

    if request.method == "POST":
        post_data = request.POST.copy()

        # Normalize org fields for new names
        dept_value = post_data.get("department")
        if dept_value and not dept_value.isdigit():
            dept_obj, _ = Department.objects.get_or_create(name=dept_value)
            post_data["department"] = str(dept_obj.id)

        assoc_value = post_data.get("association")
        if assoc_value and not assoc_value.isdigit():
            assoc_obj, _ = Association.objects.get_or_create(name=assoc_value)
            post_data["association"] = str(assoc_obj.id)

        club_value = post_data.get("club")
        if club_value and not club_value.isdigit():
            club_obj, _ = Club.objects.get_or_create(name=club_value)
            post_data["club"] = str(club_obj.id)

        center_value = post_data.get("center")
        if center_value and not center_value.isdigit():
            center_obj, _ = Center.objects.get_or_create(name=center_value)
            post_data["center"] = str(center_obj.id)

        cell_value = post_data.get("cell")
        if cell_value and not cell_value.isdigit():
            cell_obj, _ = Cell.objects.get_or_create(name=cell_value)
            post_data["cell"] = str(cell_obj.id)

        form = EventProposalForm(post_data, instance=proposal)

        # --------- FACULTY INCHARGES QUERYSET FIX ---------
        # Always set the queryset to include posted IDs (and all faculty for JS search)
        faculty_ids = post_data.getlist("faculty_incharges")
        if faculty_ids:
            form.fields['faculty_incharges'].queryset = User.objects.filter(
                Q(role_assignments__role='faculty') | Q(id__in=faculty_ids)
            ).distinct()
        else:
            form.fields['faculty_incharges'].queryset = User.objects.filter(role_assignments__role='faculty').distinct()
        # --------------------------------------------------

    else:
        form = EventProposalForm(instance=proposal)
        # Populate all faculty as available choices for JS search/select on GET
        form.fields['faculty_incharges'].queryset = User.objects.filter(role_assignments__role='faculty').distinct()

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
        "department_name": get_name(Department, form['department'].value()),
        "association_name": get_name(Association, form['association'].value()),
        "club_name": get_name(Club, form['club'].value()),
        "center_name": get_name(Center, form['center'].value()),
        "cell_name": get_name(Cell, form['cell'].value()),
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

    # Fetch user's submitted proposals
    user_proposals = EventProposal.objects.filter(submitted_by=user).order_by('-created_at')

    # DEBUG >>> ------------------------------------------
    ras = list(user.role_assignments.all())
    print("DEBUG – role_assignments for", user.username, ":", ras)
    print("DEBUG – raw roles:", [ra.role for ra in ras])
    # <<< -----------------------------------------------

    roles = {ra.role for ra in ras}
    approval_roles = {
        "faculty", "dept_iqac", "hod", "dean",
        "academic_coordinator", "club_head", "center_head",
    }
    show_approvals_card = bool(roles & approval_roles)

    return render(
        request,
        'emt/iqac_suite_dashboard.html',
        {
            'user_proposals': user_proposals,
            'show_approvals_card': show_approvals_card
        }
    )
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
def api_departments(request):
    q = request.GET.get("q", "").strip()
    depts = Department.objects.filter(name__icontains=q).order_by("name")[:20]
    return JsonResponse([{"id": d.id, "text": d.name} for d in depts], safe=False)

@login_required
def api_associations(request):
    q = request.GET.get("q", "").strip()
    assocs = Association.objects.filter(name__icontains=q).order_by("name")[:20]
    return JsonResponse([{"id": a.id, "text": a.name} for a in assocs], safe=False)

@login_required
def api_clubs(request):
    q = request.GET.get("q", "").strip()
    clubs = Club.objects.filter(name__icontains=q).order_by("name")[:20]
    return JsonResponse([{"id": c.id, "text": c.name} for c in clubs], safe=False)

@login_required
def api_centers(request):
    q = request.GET.get("q", "").strip()
    centers = Center.objects.filter(name__icontains=q).order_by("name")[:20]
    return JsonResponse([{"id": c.id, "text": c.name} for c in centers], safe=False)

@login_required
def api_cells(request):
    q = request.GET.get("q", "").strip()
    cells = Cell.objects.filter(name__icontains=q).order_by("name")[:20]
    return JsonResponse([{"id": c.id, "text": c.name} for c in cells], safe=False)

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
            return redirect('pending_reports')  # or wherever you want
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

