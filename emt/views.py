from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import (
    EventProposal, EventNeedAnalysis, EventObjectives, AttendanceRecord, Coordinator, Volunteer,
    EventExpectedOutcomes, TentativeFlow, ExpenseDetail, SpeakerProfile
)
from .forms import (
    EventProposalForm, NeedAnalysisForm, ExpectedOutcomesForm, AttendanceForm, CoordinatorForm, VolunteerForm,
    ObjectivesForm, TentativeFlowForm, SpeakerProfileForm, ExpenseDetailForm
)
from django.forms import modelformset_factory
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from django.http import HttpResponse

# ========== PROPOSAL STEP 1 ==========
@login_required
def submit_proposal(request, pk=None):
    proposal = None
    if pk:
        # Only load a proposal (draft) if pk given
        proposal = get_object_or_404(EventProposal, pk=pk, submitted_by=request.user)

    if request.method == 'POST':
        form = EventProposalForm(request.POST, instance=proposal)
        if form.is_valid():
            proposal = form.save(commit=False)
            proposal.submitted_by = request.user
            if 'save_draft' in request.POST:
                proposal.status = 'draft'
                proposal.save()
                return redirect('proposal_status', proposal.id)
            elif 'submit' in request.POST:
                proposal.status = 'submitted'
                proposal.save()
                return redirect('emt:submit_need_analysis', proposal_id=proposal.id)
    else:
        form = EventProposalForm(instance=proposal)
    return render(request, 'emt/submit_proposal.html', {'form': form, 'proposal': proposal})


# ========== AUTOSAVE ENDPOINT ==========
@csrf_exempt
@login_required
def autosave_proposal(request):
    """Handles AJAX autosave of draft."""
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        proposal_id = data.get('proposal_id')
        if proposal_id:
            proposal = EventProposal.objects.filter(id=proposal_id, submitted_by=request.user).first()
            form = EventProposalForm(data, instance=proposal)
        else:
            form = EventProposalForm(data)
        if form.is_valid():
            proposal = form.save(commit=False)
            proposal.submitted_by = request.user
            proposal.status = 'draft'
            proposal.save()
            return JsonResponse({'success': True, 'proposal_id': proposal.id})
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    return JsonResponse({'error': 'Invalid request'}, status=400)

# ========== STEP 2 ==========
@login_required
def submit_need_analysis(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id, submitted_by=request.user)
    instance = EventNeedAnalysis.objects.filter(proposal=proposal).first()
    if request.method == 'POST':
        form = NeedAnalysisForm(request.POST, instance=instance)
        if form.is_valid():
            need = form.save(commit=False)
            need.proposal = proposal
            need.save()
            return redirect('emt:submit_objectives', proposal_id=proposal.id)
    else:
        form = NeedAnalysisForm(instance=instance)
    return render(request, 'emt/need_analysis.html', {'form': form, 'proposal': proposal})

# ========== STEP 3 ==========
@login_required
def submit_objectives(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id, submitted_by=request.user)
    instance = EventObjectives.objects.filter(proposal=proposal).first()
    if request.method == 'POST':
        form = ObjectivesForm(request.POST, instance=instance)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.proposal = proposal
            obj.save()
            return redirect('emt:submit_expected_outcomes', proposal_id=proposal.id)
    else:
        form = ObjectivesForm(instance=instance)
    return render(request, 'emt/objectives.html', {'form': form, 'proposal': proposal})

# ========== STEP 4 ==========
@login_required
def submit_expected_outcomes(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id, submitted_by=request.user)
    instance = EventExpectedOutcomes.objects.filter(proposal=proposal).first()
    if request.method == 'POST':
        form = ExpectedOutcomesForm(request.POST, instance=instance)
        if form.is_valid():
            outcome = form.save(commit=False)
            outcome.proposal = proposal
            outcome.save()
            return redirect('emt:submit_tentative_flow', proposal_id=proposal.id)
    else:
        form = ExpectedOutcomesForm(instance=instance)
    return render(request, 'emt/submit_expected_outcomes.html', {'form': form, 'proposal': proposal})

# ========== STEP 5 ==========
@login_required
def submit_tentative_flow(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id, submitted_by=request.user)
    instance = TentativeFlow.objects.filter(proposal=proposal).first()
    if request.method == 'POST':
        form = TentativeFlowForm(request.POST, instance=instance)
        if form.is_valid():
            flow = form.save(commit=False)
            flow.proposal = proposal
            flow.save()
            return redirect('emt:submit_speaker_profile', proposal_id=proposal.id)
    else:
        form = TentativeFlowForm(instance=instance)
    return render(request, 'emt/tentative_flow.html', {'form': form, 'proposal': proposal})

# ========== STEP 6 ==========
@login_required
def submit_speaker_profile(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id, submitted_by=request.user)
    SpeakerFormSet = modelformset_factory(SpeakerProfile, form=SpeakerProfileForm, extra=1, can_delete=True)
    if request.method == 'POST':
        formset = SpeakerFormSet(request.POST, request.FILES, queryset=SpeakerProfile.objects.filter(proposal=proposal))
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.proposal = proposal
                instance.save()
            for obj in formset.deleted_objects:
                obj.delete()
            return redirect('emt:submit_expense_details', proposal_id=proposal.id)
    else:
        formset = SpeakerFormSet(queryset=SpeakerProfile.objects.filter(proposal=proposal))
    return render(request, 'emt/speaker_profile.html', {'formset': formset, 'proposal': proposal})

# ========== STEP 7 ==========
@login_required
def submit_expense_details(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id, submitted_by=request.user)
    ExpenseFormSet = modelformset_factory(ExpenseDetail, form=ExpenseDetailForm, extra=1, can_delete=True)
    if request.method == 'POST':
        formset = ExpenseFormSet(request.POST, queryset=ExpenseDetail.objects.filter(proposal=proposal))
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.proposal = proposal
                instance.save()
            for obj in formset.deleted_objects:
                obj.delete()
            return redirect('dashboard')
    else:
        formset = ExpenseFormSet(queryset=ExpenseDetail.objects.filter(proposal=proposal))
    return render(request, 'emt/expense_details.html', {'proposal': proposal, 'formset': formset})

# ========== STATUS PAGE ==========
@login_required
def proposal_status(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id, submitted_by=request.user)
    return render(request, 'emt/proposal_status.html', {'proposal': proposal})

# ========== DASHBOARD ==========
@login_required
def iqac_suite_dashboard(request):
    return render(request, 'emt/iqac_suite_dashboard.html')

# ========== ATTENDANCE (bonus, unchanged) ==========
@login_required
def attendance_view(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id, submitted_by=request.user)
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'student':
            form = AttendanceForm(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.proposal = proposal
                obj.save()
        elif form_type == 'coordinator':
            form = CoordinatorForm(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.proposal = proposal
                obj.save()
        elif form_type == 'volunteer':
            form = VolunteerForm(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.proposal = proposal
                obj.save()
        return redirect('emt:attendance', proposal_id=proposal.id)
    context = {
        'proposal': proposal,
        'students': proposal.attendees.all(),
        'coordinators': proposal.coordinators.all(),
        'volunteers': proposal.volunteers.all(),
        'student_form': AttendanceForm(),
        'coordinator_form': CoordinatorForm(),
        'volunteer_form': VolunteerForm(),
    }
    return render(request, 'emt/attendance.html', context)
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
def pending_reports(request):
    proposals = EventProposal.objects.filter(report_generated=False, submitted_by=request.user)
    return render(request, 'emt/pending_reports.html', {'proposals': proposals})



def generate_report(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id, submitted_by=request.user)

    # 🚀 Logic to generate report goes here
    # TODO: Call your PDF/Word report generation logic here
    # Example: generate_pdf(proposal), generate_docx(proposal), etc.

    proposal.report_generated = True
    proposal.save()
    return redirect('emt:report_success', proposal_id=proposal.id)


def report_success(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id)
    return render(request, 'emt/report_success.html', {'proposal': proposal})
def download_pdf(request, proposal_id):
    # TODO: Generate and return actual PDF
    return HttpResponse(f"PDF download for Proposal {proposal_id}", content_type='application/pdf')

def download_word(request, proposal_id):
    # TODO: Generate and return actual Word file
    return HttpResponse(f"Word download for Proposal {proposal_id}", content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
@login_required
def generated_reports(request):
    reports = EventProposal.objects.filter(report_generated=True, submitted_by=request.user).order_by('-id')
    return render(request, 'emt/generated_reports.html', {'reports': reports})

@login_required
def view_report(request, report_id):
    report = get_object_or_404(EventProposal, id=report_id, submitted_by=request.user, report_generated=True)
    # Gather more details if needed
    return render(request, 'emt/view_report.html', {'report': report})
