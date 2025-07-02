from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.forms import inlineformset_factory
from .models import (
    Profile, EventProposal, RoleAssignment,
    Department, Club, Center
)
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

def superuser_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_superuser):
            return HttpResponseForbidden("You are not authorized to access this page.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def login_view(request):
    return render(request, 'core/login.html')

def login_page(request):
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    proposals = EventProposal.objects.filter(submitted_by=request.user).exclude(status='completed').order_by('-date_submitted')
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
        department = request.POST.get('department') or ''
        title = request.POST.get('title')
        desc  = request.POST.get('description')
        # Use main role or summary of roles
        roles = [ra.get_role_display() for ra in request.user.role_assignments.all()]
        user_type = ", ".join(roles) or (request.user.profile.main_role if hasattr(request.user, "profile") else "")
        EventProposal.objects.create(
            submitted_by=request.user,
            department=department,
            user_type=user_type,
            title=title,
            description=desc
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
        "students": RoleAssignment.objects.filter(role="student").count(),
        "faculties": RoleAssignment.objects.filter(role="faculty").count(),
        "hods": RoleAssignment.objects.filter(role="hod").count(),
        "centers": RoleAssignment.objects.filter(role="center_head").count(),
    }
    return render(request, "core/admin_dashboard.html", {"stats": stats})

@user_passes_test(lambda u: u.is_superuser)
def admin_user_panel(request):
    return render(request, "core/admin_user_panel.html")

@user_passes_test(lambda u: u.is_superuser)
def admin_user_management(request):
    users = User.objects.all().order_by('-date_joined')
    # --- Filtering Logic ---
    role = request.GET.get('role')
    q = request.GET.get('q', '').strip()
    if role:
        users = users.filter(role_assignments__role=role).distinct()
    if q:
        users = users.filter(
            Q(email__icontains=q) | 
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(username__icontains=q)
        ).distinct()
    # Pre-fetch roles for performance
    users = users.prefetch_related('role_assignments', 'role_assignments__department', 'role_assignments__club', 'role_assignments__center')
    return render(request, "core/admin_user_management.html", {"users": users})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)

    # extra=0 → we’ll only add rows via JS & the empty_form prototype
    RoleFormSet = inlineformset_factory(
        User, RoleAssignment,
        fields=('role', 'department', 'club', 'center'),
        extra=0, can_delete=True
    )

    if request.method == 'POST':
        formset = RoleFormSet(request.POST, instance=user)
        # update basic info
        user.first_name = request.POST.get('first_name','')
        user.last_name  = request.POST.get('last_name','')
        user.email      = request.POST.get('email','')
        user.save()

        if formset.is_valid():
            # handle any “Other…” text inputs
            for idx, form in enumerate(formset.forms):
                nd = request.POST.get(f'new_department_{idx}','').strip()
                nc = request.POST.get(f'new_club_{idx}','').strip()
                ne = request.POST.get(f'new_center_{idx}','').strip()
                if nd:
                    dept, _ = Department.objects.get_or_create(name=nd)
                    form.instance.department = dept
                if nc:
                    club, _ = Club.objects.get_or_create(name=nc)
                    form.instance.club = club
                if ne:
                    cen,  _ = Center.objects.get_or_create(name=ne)
                    form.instance.center = cen

            formset.save()
            messages.success(request, "User roles updated successfully.")
            return redirect('admin_user_management')
        else:
            messages.error(request, "Please fix the errors below and try again.")
    else:
        formset = RoleFormSet(instance=user)

    return render(request, 'core/admin_user_edit.html', {
        'user_obj': user,
        'formset':  formset,
        'departments': Department.objects.all(),
        'clubs':      Club.objects.all(),
        'centers':    Center.objects.all(),
    })

@user_passes_test(lambda u: u.is_superuser)
def admin_event_proposals(request):
    q = request.GET.get("q", "")
    status = request.GET.get("status", "")
    proposals = EventProposal.objects.all().order_by("-date_submitted")
    if q:
        proposals = proposals.filter(
            Q(title__icontains=q) | Q(submitted_by__username__icontains=q) | Q(department__icontains=q)
        )
    if status:
        proposals = proposals.filter(status=status)
    return render(request, "core/admin_event_proposals.html", {
        "proposals": proposals
    })

@user_passes_test(lambda u: u.is_superuser)
def event_proposal_json(request, proposal_id):
    p = get_object_or_404(EventProposal, id=proposal_id)
    return JsonResponse({
        "title": p.title,
        "description": p.description,
        "department": p.department,
        "user_type": p.user_type,
        "status": p.status,
        "status_display": p.get_status_display(),
        "date_submitted": p.date_submitted.strftime("%Y-%m-%d %H:%M"),
        "submitted_by": p.submitted_by.get_full_name() or p.submitted_by.username,
    })

@user_passes_test(lambda u: u.is_superuser)
@require_POST
def event_proposal_action(request, proposal_id):
    p = get_object_or_404(EventProposal, id=proposal_id)
    data = json.loads(request.body)
    action = data.get("action")
    comment = data.get("comment", "")
    if action == "approved":
        p.status = "approved"
    elif action == "rejected":
        p.status = "rejected"
    elif action == "returned":
        p.status = "returned"
    else:
        return JsonResponse({"success": False, "error": "Invalid action"})
    if comment:
        p.admin_comment = comment
    p.save()
    return JsonResponse({"success": True})
