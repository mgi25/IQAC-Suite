# core/views.py

from django.shortcuts               import render, redirect,get_object_or_404
from django.contrib.auth            import logout
from django.contrib.auth.decorators import login_required

# import your model
from .models import EventProposal
from django.shortcuts import render
from emt.models import EventProposal

def login_view(request):
    # Simply show the login page; the form action in the template will point
    # to allauth’s Google login URL via the provider_login_url tag.
    return render(request, 'core/login.html')

def login_page(request):
    return render(request, 'login.html')

def logout_view(request):
    """
    Log out locally and send back to the login page.
    """
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    # Use the correct field name based on your EventProposal model.
    # If your model has 'user', use user=request.user
    # If it has 'submitted_by', use submitted_by=request.user

    proposals = EventProposal.objects.filter(submitted_by=request.user).exclude(status='completed').order_by('-updated_at')
    # If your model uses 'submitted_by':
    # proposals = EventProposal.objects.filter(submitted_by=request.user).exclude(status='completed').order_by('-updated_at')

    other_notifications = [
        {'type': 'info', 'msg': 'System update scheduled for tonight at 10 PM.', 'time': '2 hours ago'},
        {'type': 'reminder', 'msg': 'Submit your event report before 26 June.', 'time': '1 day ago'},
        {'type': 'alert', 'msg': 'One of your proposals was returned for revision.', 'time': '5 mins ago'},
    ]

    return render(request, 'core/dashboard.html', {
        'proposals': proposals,
        'other_notifications': other_notifications,
    })


@login_required
def propose_event(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        desc  = request.POST.get('description')
        EventProposal.objects.create(
            user=request.user,
            title=title,
            description=desc
        )
        return redirect('dashboard')
    return render(request, 'core/event_proposal.html')
def proposal_status(request, pk):
    proposal = get_object_or_404(EventProposal, pk=pk, submitted_by=request.user)
    # prepare any tracker steps, comments, etc
    steps = [
        {'key': 'draft', 'label': 'Draft'},
        {'key': 'submitted', 'label': 'Submitted'},
        {'key': 'under_review', 'label': 'Under Review'},
        {'key': 'approved', 'label': 'Approved'},
        {'key': 'rejected', 'label': 'Rejected'},
        {'key': 'returned', 'label': 'Returned for Revision'},
    ]
    return render(request, 'core/proposal_status.html', {
        'proposal': proposal,
        'steps': steps,
    })