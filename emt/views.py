from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import EventProposal, EventNeedAnalysis, EventObjectives, AttendanceRecord, Coordinator, Volunteer,EventExpectedOutcomes, TentativeFlow, ExpenseDetail
from .forms import EventProposalForm, NeedAnalysisForm, ExpectedOutcomesForm, AttendanceForm, CoordinatorForm, VolunteerForm,ObjectivesForm,TentativeFlowForm,SpeakerProfileForm,SpeakerProfile,ExpenseDetailForm
from django.forms import modelformset_factory

@login_required
def index(request):
    # you can change this template path later once you build it out
    return render(request, 'emt/index.html')

@login_required
def submit_proposal(request):
    if request.method == 'POST':
        form = EventProposalForm(request.POST)
        if form.is_valid():
            proposal = form.save(commit=False)
            proposal.submitted_by = request.user
            proposal.save()
            return redirect('emt:submit_need_analysis', proposal_id=proposal.id)  # Next step
    else:
        form = EventProposalForm()
    return render(request, 'emt/submit_proposal.html', {'form': form})

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

@login_required
def submit_expected_outcomes(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id)

    try:
        instance = EventExpectedOutcomes.objects.get(proposal=proposal)
    except EventExpectedOutcomes.DoesNotExist:
        instance = None

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
            return redirect('emt:submit_expense_details', proposal_id=proposal.id)  # Next step
    else:
        formset = SpeakerFormSet(queryset=SpeakerProfile.objects.filter(proposal=proposal))

    return render(request, 'emt/speaker_profile.html', {
        'formset': formset,
        'proposal': proposal
    })
@login_required
def submit_expense_details(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id)
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
            # Final redirect or thank you page can go here
            return redirect('dashboard')  # or any final view
    else:
        formset = ExpenseFormSet(queryset=ExpenseDetail.objects.filter(proposal=proposal))

    return render(request, 'emt/expense_details.html', {
        'proposal': proposal,
        'formset': formset
    })
@login_required
def proposal_status(request, proposal_id):
    """
    Show the details & status of a single proposal.
    """
    # You probably want to restrict to the current user:
    proposal = get_object_or_404(
        EventProposal,
        id=proposal_id,
        submitted_by=request.user
    )

    return render(request, 'emt/proposal_status.html', {
        'proposal': proposal
    })


@login_required
def attendance_view(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id)

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
@login_required
@login_required
def submit_objectives(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id)
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
