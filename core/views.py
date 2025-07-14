from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden, JsonResponse, HttpResponseRedirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.forms import inlineformset_factory
from django.urls import reverse
from django.views.decorators.http import require_POST
import json
from .models import (
    Profile, RoleAssignment,
    Department, Club, Center, Report,Cell, Association
)
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count
from emt.models import EventProposal
from emt.models import (
    EventProposal, EventNeedAnalysis, EventObjectives, EventExpectedOutcomes, TentativeFlow,
    ExpenseDetail, SpeakerProfile, ApprovalStep
)
from django.db.models import Sum
# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────
def superuser_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_superuser):
            return HttpResponseForbidden("You are not authorized to access this page.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# ─────────────────────────────────────────────────────────────
#  Auth Views
# ─────────────────────────────────────────────────────────────
def login_view(request):
    return render(request, "core/login.html")

def login_page(request):
    return render(request, "login.html")

def logout_view(request):
    logout(request)
    return redirect("login")

def custom_logout(request):
    logout(request)
    # Google logout endpoint (will log out of Google in this browser session)
    google_logout_url = "https://accounts.google.com/Logout"
    # After Google logout, redirect back to your login page
    return redirect(f"{google_logout_url}?continue=https://appengine.google.com/_ah/logout?continue=http://127.0.0.1:8000/accounts/login/")

# ─────────────────────────────────────────────────────────────
#  Dashboard
# ─────────────────────────────────────────────────────────────
@login_required
def dashboard(request):
    proposals = (
        EventProposal.objects
        .filter(submitted_by=request.user)
        .exclude(status="completed")
        .order_by("-created_at")

    )
    other_notifications = [
        {"type": "info",     "msg": "System update scheduled for tonight at 10 PM.", "time": "2 hours ago"},
        {"type": "reminder", "msg": "Submit your event report before 26 June.",      "time": "1 day ago"},
        {"type": "alert",    "msg": "One of your proposals was returned.",           "time": "5 mins ago"},
    ]
    return render(
        request,
        "core/dashboard.html",
        {"proposals": proposals, "notifications": other_notifications},
    )


@login_required
def propose_event(request):
    """
    NOTE: This is the *old* quick-and-simple proposal form that lives in the
    core app. It still relies only on Department (FK) and doesn't collide with
    the richer EMT workflow you’re building.
    """
    if request.method == "POST":
        dept_input = request.POST.get("department", "").strip()
        department = None
        if dept_input.isdigit():
            department = Department.objects.filter(pk=dept_input).first()
        else:
            department, _ = Department.objects.get_or_create(name=dept_input)

        # capture title & description
        title = request.POST.get("title", "").strip()
        desc  = request.POST.get("description", "").strip()

        # collect the user’s role summary for display
        roles = [ra.get_role_display() for ra in request.user.role_assignments.all()]
        user_type = ", ".join(roles) or getattr(request.user.profile, "role", "")

        EventProposal.objects.create(
            submitted_by=request.user,
            department=department,
            user_type=user_type,
            title=title,
            description=desc,
        )
        return redirect("dashboard")

    return render(request, "core/event_proposal.html")

# ─────────────────────────────────────────────────────────────
#  Proposal Status
# ─────────────────────────────────────────────────────────────
@login_required
def proposal_status(request, pk):
    proposal = get_object_or_404(EventProposal, pk=pk, submitted_by=request.user)
    steps = [
        {"key": "draft",     "label": "Draft"},
        {"key": "submitted", "label": "Submitted"},
        {"key": "under_review", "label": "Under Review"},
        {"key": "approved",  "label": "Approved"},
        {"key": "rejected",  "label": "Rejected"},
        {"key": "returned",  "label": "Returned for Revision"},
    ]
    return render(request, "core/proposal_status.html", {"proposal": proposal, "steps": steps})

# ─────────────────────────────────────────────────────────────
#  Admin Dashboard
# ─────────────────────────────────────────────────────────────
def admin_dashboard(request):
    """
    Just render the admin_dashboard.html template, without data.
    """
    return render(request, "core/admin_dashboard.html")



@user_passes_test(lambda u: u.is_superuser)
def admin_user_panel(request):
    return render(request, "core/admin_user_panel.html")

@user_passes_test(lambda u: u.is_superuser)
def admin_user_management(request):
    users = User.objects.all().order_by('-date_joined')
    role = request.GET.get('role')
    q = request.GET.get('q', '').strip()
    if role:
        users = users.filter(role_assignments__role=role)
    if q:
        users = users.filter(
            Q(email__icontains=q) | 
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(username__icontains=q)
        )
    users = users.distinct().prefetch_related('role_assignments', 'role_assignments__department', 'role_assignments__club', 'role_assignments__center')
    return render(request, "core/admin_user_management.html", {"users": users})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_user_edit(request, user_id):
    """
    • edits basic name / e-mail
    • manages a RoleAssignment inline-form-set
    • supports the JS “Other…” inputs for Department / Club / Center / Cell / Association
    """
    user = get_object_or_404(User, id=user_id)

    RoleFormSet = inlineformset_factory(
        User,
        RoleAssignment,
        fields=('role', 'department', 'club', 'center', 'cell', 'association'),
        extra=0,
        can_delete=True
    )

    if request.method == "POST":
        formset = RoleFormSet(request.POST, instance=user)

        # Update basic info
        user.first_name = request.POST.get("first_name", "").strip()
        user.last_name  = request.POST.get("last_name", "").strip()
        user.email      = request.POST.get("email", "").strip()
        user.save()

        if formset.is_valid():
            for idx, form in enumerate(formset.forms):
                new_dept   = request.POST.get(f'new_department_{idx}', '').strip()
                new_club   = request.POST.get(f'new_club_{idx}', '').strip()
                new_center = request.POST.get(f'new_center_{idx}', '').strip()
                new_cell   = request.POST.get(f'new_cell_{idx}', '').strip()
                new_association = request.POST.get(f'new_association_{idx}', '').strip()

                if new_dept:
                    dept, _ = Department.objects.get_or_create(name=new_dept)
                    form.instance.department = dept

                if new_club:
                    club, _ = Club.objects.get_or_create(name=new_club)
                    form.instance.club = club

                if new_center:
                    cen, _ = Center.objects.get_or_create(name=new_center)
                    form.instance.center = cen

                if new_cell:
                    cell, _ = Cell.objects.get_or_create(name=new_cell)
                    form.instance.cell = cell

                if new_association:
                    assoc, _ = Association.objects.get_or_create(name=new_association)
                    form.instance.association = assoc

            formset.save()
            messages.success(request, "User roles updated successfully.")
            return redirect("admin_user_management")
        else:
            messages.error(request, "Please fix the errors below and try again.")
    else:
        formset = RoleFormSet(instance=user)

    return render(
        request,
        "core/admin_user_edit.html",
        {
            "user_obj":  user,
            "formset":   formset,
            "departments": Department.objects.all(),
            "clubs":      Club.objects.all(),
            "centers":    Center.objects.all(),
            "cells":      Cell.objects.all(),
            "associations": Association.objects.all(),
        },
    )



@user_passes_test(lambda u: u.is_superuser)
def admin_event_proposals(request):
    proposals = EventProposal.objects.all().order_by("-created_at")
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    if q:
        proposals = proposals.filter(
            Q(event_title__icontains=q) |
            Q(submitted_by__username__icontains=q) |
            Q(department__name__icontains=q) |
            Q(association__name__icontains=q) |
            Q(club__name__icontains=q) |
            Q(center__name__icontains=q) |
            Q(cell__name__icontains=q)
        )
    if status:
        proposals = proposals.filter(status=status)
    return render(request, "core/admin_event_proposals.html", {"proposals": proposals})



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
@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_reports(request):
    reports = Report.objects.select_related('submitted_by').all().order_by('-date_submitted')
    return render(request, 'core/admin_reports.html', {
        'reports': reports,
    })
@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_reports_approve(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    report.status = 'approved'
    report.save()
    messages.success(request, f"Report '{report.title}' approved.")
    return HttpResponseRedirect(reverse('admin_reports'))

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_reports_reject(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    report.status = 'rejected'
    report.save()
    messages.warning(request, f"Report '{report.title}' rejected.")
    return HttpResponseRedirect(reverse('admin_reports'))

def cdl_dashboard(request):
    return render(request, 'emt/cdl_dashboard.html')

STATUSES = ['submitted', 'under_review', 'approved', 'rejected']

def iqac_suite_dashboard(request):
    user_proposals = (
        EventProposal.objects
        .filter(submitted_by=request.user)
        .order_by("-created_at")

    )
    for proposal in user_proposals:
        proposal.status_index = STATUSES.index(proposal.status) if proposal.status in STATUSES else -1

    context = {
        "user_proposals": user_proposals,
        "statuses": STATUSES,
    }
    return render(request, "emt/iqac_suite_dashboard.html", context)
@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_master_data(request):
    departments = Department.objects.all()
    clubs = Club.objects.all()
    centers = Center.objects.all()
    cells = Cell.objects.all()
    associations = Association.objects.select_related("department").all()
    return render(request, "core/admin_master_data.html", {
        "departments": departments,
        "clubs": clubs,
        "centers": centers,
        "cells": cells,
        "associations": associations,
    })

# The following can be made more DRY, but let's keep simple for now:

@login_required
@user_passes_test(lambda u: u.is_superuser)
@csrf_exempt
def admin_master_data_add(request, model_name):
    MODEL_MAP = {
        "department": Department,
        "club": Club,
        "center": Center,
        "cell": Cell,
        "association": Association,
    }
    Model = MODEL_MAP.get(model_name)
    if request.method == "POST" and Model:
        name = request.POST.get("name", "").strip()
        obj, created = Model.objects.get_or_create(name=name)
        return JsonResponse({"success": True, "id": obj.id, "name": obj.name})
    return JsonResponse({"success": False, "error": "Invalid request"})

@login_required
@user_passes_test(lambda u: u.is_superuser)
@csrf_exempt
def admin_master_data_edit(request, model_name, pk):
    MODEL_MAP = {
        "department": Department,
        "club": Club,
        "center": Center,
        "cell": Cell,
        "association": Association,
    }
    Model = MODEL_MAP.get(model_name)
    if request.method == "POST" and Model:
        obj = get_object_or_404(Model, pk=pk)
        name = request.POST.get("name", "").strip()
        obj.name = name
        if model_name == "association":
            # Handle department field for Association
            dept_id = request.POST.get("department")
            if dept_id:
                obj.department_id = dept_id
        obj.save()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "error": "Invalid request"})

@login_required
@user_passes_test(lambda u: u.is_superuser)
@csrf_exempt
def admin_master_data_delete(request, model_name, pk):
    MODEL_MAP = {
        "department": Department,
        "club": Club,
        "center": Center,
        "cell": Cell,
        "association": Association,
    }
    Model = MODEL_MAP.get(model_name)
    if request.method == "POST" and Model:
        obj = get_object_or_404(Model, pk=pk)
        obj.delete()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "error": "Invalid request"})
@user_passes_test(lambda u: u.is_superuser)
def admin_proposal_detail(request, proposal_id):
    proposal = get_object_or_404(EventProposal, id=proposal_id)
    need_analysis = EventNeedAnalysis.objects.filter(proposal=proposal).first()
    objectives = EventObjectives.objects.filter(proposal=proposal).first()
    outcomes = EventExpectedOutcomes.objects.filter(proposal=proposal).first()
    flow = TentativeFlow.objects.filter(proposal=proposal).first()
    speakers = SpeakerProfile.objects.filter(proposal=proposal)
    expenses = ExpenseDetail.objects.filter(proposal=proposal)
    approval_steps = ApprovalStep.objects.filter(proposal=proposal).order_by('step_order')

    budget_total = expenses.aggregate(total=Sum('amount'))['total'] or 0

    context = {
        "proposal": proposal,
        "need_analysis": need_analysis,
        "objectives": objectives,
        "outcomes": outcomes,
        "flow": flow,
        "speakers": speakers,
        "expenses": expenses,
        "approval_steps": approval_steps,
        "budget_total": budget_total,
    }
    return render(request, "core/admin_proposal_detail.html", context)
@user_passes_test(lambda u: u.is_superuser)
def admin_settings_dashboard(request):
    # Renders the new dashboard with cards for each settings app
    return render(request, "core/admin_settings.html")
@user_passes_test(lambda u: u.is_superuser)
def admin_approval_flow(request):
    return render(request, "core/admin_approval_flow.html")
