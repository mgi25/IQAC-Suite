from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden
from django.contrib.auth.models import User
from django.contrib import messages
# Assuming you have a Profile model with a 'role' field
from core.models import Profile
from emt.models import EventProposal
from django.db.models import Q


def superuser_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_superuser):
            return HttpResponseForbidden("You are not authorized to access this page.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def login_view(request):
    # Allauth login
    return render(request, 'core/login.html')

def login_page(request):
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    proposals = EventProposal.objects.filter(submitted_by=request.user).exclude(status='completed').order_by('-updated_at')
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
            submitted_by=request.user,
            event_title=title,
            # description=desc  # Make sure your model has this field
        )
        return redirect('dashboard')
    return render(request, 'core/event_proposal.html')

@login_required
def proposal_status(request, pk):
    proposal = get_object_or_404(EventProposal, pk=pk, submitted_by=request.user)
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

@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    stats = {
        "students": User.objects.filter(profile__role="student").count(),
        "faculties": User.objects.filter(profile__role="faculty").count(),
        "hods": User.objects.filter(profile__role="hod").count(),
        "centers": User.objects.filter(profile__role="center").count(),
    }
    return render(request, "core/admin_dashboard.html", {"stats": stats})

@user_passes_test(lambda u: u.is_superuser)
def admin_user_panel(request):
    return render(request, "core/admin_user_panel.html")

@user_passes_test(lambda u: u.is_superuser)
@user_passes_test(lambda u: u.is_superuser)
def admin_user_management(request):
    users = User.objects.select_related('profile').all().order_by('-date_joined')

    # --- Filtering Logic ---
    role = request.GET.get('role')
    q = request.GET.get('q', '').strip()
    
    # Filter by role if provided
    if role:
        users = users.filter(profile__role__iexact=role)
    
    # Filter by search query (name or email)
    if q:
        users = users.filter(
            Q(email__icontains=q) | 
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(username__icontains=q)
        )

    return render(request, "core/admin_user_management.html", {"users": users})


@user_passes_test(lambda u: u.is_superuser)
def admin_user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    # Add form logic for editing if needed
    return render(request, "core/admin_user_edit.html", {"user": user})
@user_passes_test(lambda u: u.is_superuser)
def admin_user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile = user.profile

    if request.method == "POST":
        # Update user fields
        user.first_name = request.POST.get("first_name", "")
        user.last_name = request.POST.get("last_name", "")
        user.email = request.POST.get("email", "")
        user.save()

        # Update role
        role = request.POST.get("role")
        if role in ["student", "faculty", "hod", "center"]:
            profile.role = role
            profile.save()

        messages.success(request, "User updated successfully.")
        return redirect('admin_user_management')  # Redirect to user management

    return render(request, "core/admin_user_edit.html", {
        "user_obj": user,
        "profile": profile,
    })
