

import os
import shutil
from datetime import timedelta, datetime
from django.shortcuts import render, redirect, get_object_or_404, resolve_url
from django.contrib.auth import logout
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden, JsonResponse, HttpResponseRedirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from django.db.models import Q, Sum, Count
from django.forms import inlineformset_factory
from django import forms
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import models, transaction
from django.db.models.functions import TruncDate
from django.utils import timezone
import json
import logging
logger = logging.getLogger(__name__)
from .decorators import popso_manager_required, popso_program_access_required
from .forms import RoleAssignmentForm, RegistrationForm
from .models import (
    Profile,
    RoleAssignment,
    Organization,
    OrganizationType,
    Report,
    Class,
    OrganizationRole,
    Program,
    ProgramOutcome,
    ProgramSpecificOutcome,
    ActivityLog,
)
from emt.models import EventProposal, Student
from django.views.decorators.http import require_GET, require_POST
from .models import (
    ApprovalFlowTemplate,
    ApprovalFlowConfig,
    CDLRequest,
    CertificateBatch,
    CDLCommunicationThread,
    CDLMessage,
    CertificateEntry,
)
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from .decorators import admin_required
from .models import FacultyMeeting
from .forms import CDLRequestForm, CertificateBatchUploadForm, CDLMessageForm

# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────
def is_admin(user):
    """Return True if the user is staff or superuser.

    Defined near the top so decorators like `@user_passes_test(is_admin)`
    can resolve this symbol at import time.
    """
    try:
        return bool(getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))
    except Exception:
        return False

def superuser_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_superuser):
            return HttpResponseForbidden("You are not authorized to access this page.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def _superuser_check(user):
    if not user.is_superuser:
        raise PermissionDenied("You are not authorized to access this page.")
    return True


def safe_next(request, fallback="/"):
    nxt = (
        request.POST.get("next")
        or request.GET.get("next")
        or request.META.get("HTTP_REFERER")
    )
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return nxt
    return resolve_url(fallback)
@login_required
def cdl_event_user_view(request):
    """Unified CDL user page (UI only). Expects ?eventId=<id>."""
    return render(request, "core/cdl_event_user_view.html")


# ────────────────────────────────────────────────
# Unified CDL Event APIs (UI support for cdl_event_user_view)
# ────────────────────────────────────────────────
@login_required
@require_http_methods(["GET"])  # /api/cdl/event/<proposal_id>/details/
def api_cdl_event_details(request, proposal_id:int):
    try:
        p = EventProposal.objects.select_related('organization').get(id=proposal_id)
    except EventProposal.DoesNotExist:
        return JsonResponse({"success": False, "error": "Event not found"}, status=404)
    date = None
    if p.event_start_date:
        date = p.event_start_date.isoformat()
    elif p.event_datetime:
        try:
            date = p.event_datetime.date().isoformat()
        except Exception:
            date = None
    return JsonResponse({
        "success": True,
        "id": p.id,
        "title": p.event_title,
        "date": date,
        "location": p.venue,
        "organization": getattr(p.organization, 'name', None),
        "description": (getattr(getattr(p, 'objectives', None), 'content', '') or '').strip(),
    })


@login_required
@require_http_methods(["GET"])  # /api/cdl/event/<proposal_id>/content/
def api_cdl_event_content(request, proposal_id:int):
    try:
        p = EventProposal.objects.get(id=proposal_id)
    except EventProposal.DoesNotExist:
        return JsonResponse({"success": False, "error": "Event not found"}, status=404)
    # Compose simple HTML using available related content models
    parts = []
    need = getattr(p, 'need_analysis', None)
    if need and getattr(need, 'content', '').strip():
        parts.append(f"<h3>Need Analysis</h3><div>{need.content}</div>")
    obj = getattr(p, 'objectives', None)
    if obj and getattr(obj, 'content', '').strip():
        parts.append(f"<h3>Objectives</h3><div>{obj.content}</div>")
    out = getattr(p, 'expected_outcomes', None)
    if out and getattr(out, 'content', '').strip():
        parts.append(f"<h3>Expected Outcomes</h3><div>{out.content}</div>")
    html = "\n".join(parts) or "<div>No additional content.</div>"
    return JsonResponse({"success": True, "html": html})


@login_required
@require_http_methods(["GET"])  # /api/cdl/event/<proposal_id>/assignments/
def api_cdl_event_assignments(request, proposal_id:int):
    try:
        p = EventProposal.objects.get(id=proposal_id)
    except EventProposal.DoesNotExist:
        return JsonResponse({"success": False, "error": "Event not found"}, status=404)
    from emt.models import CDLTaskAssignment as _Task
    tasks = (
        _Task.objects.filter(proposal=p)
        .select_related('assignee')
        .order_by('resource_key')
    )
    items = []
    for t in tasks:
        items.append({
            'resource': t.resource_key,
            'label': (t.label or t.resource_key.replace('_',' ').title()),
            'assignee_id': t.assignee_id,
            'assignee_name': ((t.assignee.get_full_name() or t.assignee.username) if t.assignee_id else None),
        })
    return JsonResponse({"success": True, "items": items})


@login_required
@require_http_methods(["GET"])  # /api/cdl/event/<proposal_id>/process/
def api_cdl_event_process(request, proposal_id:int):
    try:
        p = EventProposal.objects.get(id=proposal_id)
    except EventProposal.DoesNotExist:
        return JsonResponse({"success": False, "error": "Event not found"}, status=404)
    from emt.models import CDLTaskAssignment as _Task
    tasks = _Task.objects.filter(proposal=p).order_by('resource_key')
    items = [{ 'label': (t.label or t.resource_key.replace('_',' ').title()), 'status': t.status } for t in tasks]
    return JsonResponse({"success": True, "items": items})


@login_required
@require_http_methods(["GET"])  # /api/cdl/events/my-support/
def api_cdl_events_my_support(request):
    me = request.user
    qs = (
        EventProposal.objects
        .filter(submitted_by=me, cdl_support__needs_support=True)
        .select_related('organization')
        .order_by('-created_at')
    )
    items = []
    for p in qs[:200]:
        # Pick a date sensibly
        date = None
        if p.event_start_date:
            date = p.event_start_date.isoformat()
        elif p.event_datetime:
            try:
                date = p.event_datetime.date().isoformat()
            except Exception:
                date = None
        # Description preview from objectives or pos_pso
        desc = (getattr(getattr(p,'objectives',None),'content','') or p.pos_pso or '')
        if desc:
            desc = (desc[:180] + '…') if len(desc) > 180 else desc
        items.append({
            'id': p.id,
            'title': p.event_title,
            'date': date,
            'status': p.status,
            'description': desc,
            'organization': getattr(p.organization, 'name', None),
        })
    return JsonResponse({'success': True, 'items': items})


@login_required
@require_http_methods(["GET"])  # /api/cdl/event/<proposal_id>/documents/
def api_cdl_event_documents(request, proposal_id:int):
    try:
        p = EventProposal.objects.get(id=proposal_id)
    except EventProposal.DoesNotExist:
        return JsonResponse({"success": False, "error": "Event not found"}, status=404)
    s = getattr(p, 'cdl_support', None)
    if not s or not s.needs_support:
        return JsonResponse({'success': True, 'documents': {}})
    docs = {
        'poster_required': bool(s.poster_required),
        'poster': {
            'choice': s.poster_choice,
            'date': s.poster_date.isoformat() if s.poster_date else None,
            'time': s.poster_time,
            'venue': s.poster_venue,
            'design_link': s.poster_design_link,
            'title': s.poster_event_title,
            'summary': s.poster_summary,
            'resource_person': s.resource_person_name,
            'resource_person_designation': s.resource_person_designation,
        },
        'certificates_required': bool(s.certificates_required),
        'certificates': {
            'help': bool(s.certificate_help),
            'choice': s.certificate_choice,
            'design_link': s.certificate_design_link,
        },
        'other_services': s.other_services or [],
    }
    return JsonResponse({'success': True, 'documents': docs})



# Reuse the ModelForm defined in core.forms so it can be imported from here for tests


class RoleAssignmentFormSet(forms.BaseInlineFormSet):
    """Validate duplicate role assignments on the formset level."""

    def clean(self):
        super().clean()
        seen = set()
        for form in self.forms:
            if form.cleaned_data.get("DELETE"):
                continue
            role = form.cleaned_data.get("role")
            org = form.cleaned_data.get("organization")
            key = (role, org)
            if key in seen:
                raise forms.ValidationError(
                    "Duplicate role assignment for the same organization is not allowed."
                )
            seen.add(key)

# ─────────────────────────────────────────────────────────────
#  Auth Views
# ─────────────────────────────────────────────────────────────
def login_view(request):
    """Render the login page."""
    return render(request, "core/login.html")

def login_page(request):
    return render(request, "login.html")

def logout_view(request):
    logout(request)
    return redirect("login")

def custom_logout(request):
    logout(request)
    google_logout_url = "https://accounts.google.com/Logout"
    return redirect(f"{google_logout_url}?continue=https://appengine.google.com/_ah/logout?continue=http://127.0.0.1:8000/accounts/login/")


@login_required
def my_profile(request):
    """Display user's role-specific profile page with dashboard integration."""
    user = request.user
    
    # ---- role / domain detection ----
    roles = RoleAssignment.objects.filter(user=user).select_related('role', 'organization')
    role_lc = [ra.role.name.lower() for ra in roles]

    if user.is_superuser:
        return redirect('admin_dashboard')

    email = (user.email or "").lower()
    is_student = ('student' in role_lc) or email.endswith('@christuniversity.in')
    
    # Set session role for sidebar permissions
    if is_student:
        request.session["role"] = "student"
    else:
        request.session["role"] = "faculty"
    
    # Determine if this is accessed from dashboard (check for 'from_dashboard' parameter)
    from_dashboard = request.GET.get('from_dashboard', False)
    
    # Base context for all users
    context = {
        'user': user,
        'is_student': is_student,
        'from_dashboard': from_dashboard,
        'user_role': 'student' if is_student else 'faculty',
    }
    
    if is_student:
        # Student-specific data
        try:
            student_profile = Student.objects.get(user=user)
            context.update({
                'student_profile': student_profile,
                'registration_number': student_profile.registration_number,
                'department': getattr(student_profile, 'department', None),
                'academic_year': getattr(student_profile, 'academic_year', None),
            })
        except Student.DoesNotExist:
            context.update({
                'student_profile': None,
                'registration_number': None,
                'department': None,
                'academic_year': None,
            })
        
        # Student-specific achievements and organizations
        participated_events = EventProposal.objects.filter(
            Q(participants__user=user) | Q(submitted_by=user)
        ).distinct()
        
        user_org_ids = list(roles.filter(organization__isnull=False).values_list('organization_id', flat=True))
        user_organizations = Organization.objects.filter(id__in=user_org_ids)
        
        context.update({
            'user_achievements': [],  # Placeholder for achievements system
            'user_organizations': user_organizations,
            'participated_events': participated_events,
            'total_events': participated_events.count(),
            'org_count': user_organizations.count(),
            'years_active': calculate_years_active(user),
            'profile_completion_percentage': calculate_student_profile_completion(user, context),
        })
        
        template = 'core/student_profile.html' if from_dashboard else 'core/my_profile.html'
        
    else:
        # Faculty-specific data
        my_students = Student.objects.filter(mentor=user)
        my_classes = Class.objects.filter(teacher=user, is_active=True)
        organized_events = EventProposal.objects.filter(submitted_by=user)
        
        context.update({
            'my_students': my_students,
            'my_classes': my_classes,
            'organized_events': organized_events,
            'students_count': my_students.count(),
            'classes_count': my_classes.count(),
            'total_events': organized_events.count(),
            'user_organizations': Organization.objects.filter(
                id__in=roles.filter(organization__isnull=False).values_list('organization_id', flat=True)
            ),
            'years_active': calculate_years_active(user),
            'profile_completion_percentage': calculate_faculty_profile_completion(user, context),
        })
        
        template = 'core/faculty_profile.html' if from_dashboard else 'core/my_profile.html'
    
    return render(request, template, context)


def calculate_years_active(user):
    """Calculate how many years the user has been active."""
    if user.date_joined:
        delta = timezone.now() - user.date_joined
        return delta.days // 365
    return 0


def calculate_student_profile_completion(user, context):
    """Calculate profile completion percentage for students."""
    completion_factors = []
    
    # Basic profile info (40%)
    if user.first_name and user.last_name:
        completion_factors.append(20)
    if user.email:
        completion_factors.append(10)
    if context.get('registration_number'):
        completion_factors.append(10)
    
    # Academic info (30%)
    if context.get('department'):
        completion_factors.append(15)
    if context.get('academic_year'):
        completion_factors.append(15)
    
    # Activity participation (30%)
    if context.get('total_events', 0) > 0:
        completion_factors.append(20)
    if context.get('org_count', 0) > 0:
        completion_factors.append(10)
    
    return sum(completion_factors)


def calculate_faculty_profile_completion(user, context):
    """Calculate profile completion percentage for faculty."""
    completion_factors = []
    
    # Basic profile info (50%)
    if user.first_name and user.last_name:
        completion_factors.append(25)
    if user.email:
        completion_factors.append(15)
    if hasattr(user, 'profile') and user.profile:
        completion_factors.append(10)
    
    # Professional info (50%)
    if context.get('classes_count', 0) > 0:
        completion_factors.append(20)
    if context.get('students_count', 0) > 0:
        completion_factors.append(15)
    if context.get('total_events', 0) > 0:
        completion_factors.append(15)
    
    return sum(completion_factors)


# ─────────────────────────────────────────────────────────────
#  API: CDL Head Dashboard (AJAX data source)
# ─────────────────────────────────────────────────────────────
@login_required
@require_GET
def api_cdl_head_dashboard(request):
    """Return CDL Head dashboard data for the given scope (all|support).

    Response schema:
    {
      "kpis": {
        "total_active_requests": int,
        "assets_pending": int,
        "unassigned_tasks": int,
        "total_events_supported": int
      },
      "events": [
        {"id": int, "title": str, "date": "YYYY-MM-DD"|null, "status": str, "organization": str|null, "type": "cdl_support"|"proposal"}
      ],
      "event_details": [
        {"id": int, "title": str, "date": "YYYY-MM-DD"|null, "status": str, "organization": str|null, "assigned_member": str|null,
         "poster_required": bool, "certificates_required": bool}
      ],
      "workload": {"members": [str,...], "assignments": [int,...]}
    }
    """
    scope = request.GET.get("scope", "all").lower().strip()

    # Base queryset for KPIs (can include non-finalized where appropriate)
    kpi_qs = (
        EventProposal.objects.all()
        .select_related("organization")
        .prefetch_related("cdl_support")
    )

    # Events/notifications must be FINALIZED only
    events_qs = (
        EventProposal.objects.filter(status=EventProposal.Status.FINALIZED)
        .select_related("organization")
        .prefetch_related("cdl_support")
    )

    # Filter: support => only proposals with CDL support requested (and finalized)
    if scope == "support":
        events_qs = events_qs.filter(cdl_support__needs_support=True)

    # Helper: get best date for calendar/listing
    def _get_date(p: EventProposal):
        if getattr(p, "event_start_date", None):
            return p.event_start_date
        if getattr(p, "event_datetime", None):
            try:
                return p.event_datetime.date()
            except Exception:
                return None
        return None

    # Active statuses (interpreted as in-progress)
    active_statuses = [
        EventProposal.Status.SUBMITTED,
        EventProposal.Status.UNDER_REVIEW,
        EventProposal.Status.WAITING,
    ]

    # KPI calculations (independent of finalized-only constraint)
    total_active_requests = kpi_qs.filter(status__in=active_statuses).count()

    assets_pending = kpi_qs.filter(
        cdl_support__needs_support=True,
    ).filter(
        models.Q(cdl_support__poster_required=True) | models.Q(cdl_support__certificates_required=True)
    ).filter(
        status__in=[
            EventProposal.Status.SUBMITTED,
            EventProposal.Status.UNDER_REVIEW,
            EventProposal.Status.WAITING,
            EventProposal.Status.APPROVED,
        ]
    ).count()

    # No explicit CDL assignment model exists; return 0 as per "missing → 0"
    unassigned_tasks = 0

    total_events_supported = kpi_qs.filter(cdl_support__needs_support=True).count()

    # Events (for calendar)
    events = []
    for p in events_qs:
        d = _get_date(p)
        events.append({
            "id": p.id,
            "title": p.title,
            "date": d.isoformat() if d else None,
            "status": (p.status or "").lower(),
            "organization": getattr(p.organization, "name", None),
            "type": "cdl_support" if getattr(getattr(p, "cdl_support", None), "needs_support", False) else "proposal",
        })

    # Event Details (right panel)
    event_details = []
    for p in events_qs.select_related("cdl_support"):
        d = _get_date(p)
        cs = getattr(p, "cdl_support", None)
        event_details.append({
            "id": p.id,
            "title": p.title,
            "date": d.isoformat() if d else None,
            "status": (p.status or "").lower(),
            "organization": getattr(p.organization, "name", None),
            "assigned_member": None,  # Missing assignment model → null (UI should show Unassigned)
            "poster_required": bool(getattr(cs, "poster_required", False)),
            "certificates_required": bool(getattr(cs, "certificates_required", False)),
        })

    # Workload - get CDL team members from groups
    from django.contrib.auth.models import Group
    try:
        cdl_group = Group.objects.get(name="CDL_MEMBER")
        cdl_members = [user.get_full_name() or user.username for user in cdl_group.user_set.all()]
        if not cdl_members:
            cdl_members = []
    except Group.DoesNotExist:
        cdl_members = []
    
    workload = {
        "members": cdl_members,
        "assignments": [0] * len(cdl_members) if cdl_members else []
    }

    data = {
        "kpis": {
            "total_active_requests": total_active_requests or 0,
            "assets_pending": assets_pending or 0,
            "unassigned_tasks": unassigned_tasks or 0,
            "total_events_supported": total_events_supported or 0,
        },
        "events": events,
        "event_details": event_details,
        "workload": workload,
    }

    return JsonResponse(data)


@login_required
def registration_form(request):
    """Collect registration number and role assignments for a user."""
    user = request.user
    domain = user.email.split("@")[-1].lower() if user.email else ""
    is_student = domain.endswith("christuniversity.in")

    student = None
    if is_student:
        student, _ = Student.objects.get_or_create(user=user)
        if student.registration_number:
            return redirect("dashboard")

    form_kwargs = {"include_regno": is_student}

    if request.method == "POST":
        form = RegistrationForm(request.POST, **form_kwargs)
        if form.is_valid():
            if is_student:
                student.registration_number = form.cleaned_data["registration_number"]
                student.save()
            for item in form.cleaned_data["assignments"]:
                RoleAssignment.objects.get_or_create(
                    user=user,
                    organization_id=item["organization"],
                    role_id=item["role"],
                )
            return redirect("dashboard")
    else:
        initial = {}
        if is_student:
            initial["registration_number"] = student.registration_number
        form = RegistrationForm(initial=initial, **form_kwargs)

    return render(request, "core/Registration_form.html", {"form": form, "is_student": is_student})


@require_GET
def api_organizations(request):
    """Return active organizations for typeahead."""
    q = request.GET.get("q", "").strip()
    orgs = Organization.objects.filter(is_active=True)
    if q:
        orgs = orgs.filter(name__icontains=q)
    data = [{"id": o.id, "text": o.name} for o in orgs.order_by("name")[:20]]
    return JsonResponse({"organizations": data})


@require_GET
def api_roles(request):
    """Return roles filtered by organization for typeahead."""
    org_id = request.GET.get("organization")
    q = request.GET.get("q", "").strip()
    roles = OrganizationRole.objects.filter(is_active=True)
    if org_id:
        roles = roles.filter(organization_id=org_id)
    if q:
        roles = roles.filter(name__icontains=q)
    data = [{"id": r.id, "text": r.name} for r in roles.order_by("name")[:20]]
    return JsonResponse({"roles": data})

# ─────────────────────────────────────────────────────────────
#  Dashboard (safe: context always defined)
# ─────────────────────────────────────────────────────────────
@login_required
def dashboard(request):
    user = request.user

    # Check dashboard assignments; redirect directly if one, otherwise fall back by role
    from .models import DashboardAssignment
    available_dashboards = DashboardAssignment.get_user_dashboards(user)
    if len(available_dashboards) == 1:
        dashboard_key = available_dashboards[0][0]
        return redirect('select_dashboard', dashboard_key=dashboard_key)

    # ---- role / domain detection (fallback for users without assignments) ----
    roles = (
        RoleAssignment.objects.filter(user=user)
        .select_related('role', 'organization', 'organization__org_type')
    )
    role_lc = [ra.role.name.lower() for ra in roles if ra.role]

    if user.is_superuser:
        return redirect('admin_dashboard')

    email = (user.email or "").lower()
    # CDL mapping first (bug fix: CDL users were getting faculty dashboard)
    is_cdl_admin = any(
        (ra.role and ra.role.name.lower() in {"cdl admin", "cdl head"})
        and (ra.organization and ra.organization.org_type and ra.organization.org_type.name.lower() == "cdl")
        for ra in roles
    )
    is_cdl_employee = any(
        (ra.role and ra.role.name.lower() in {"cdl employee", "cdl member", "cdl team"})
        and (ra.organization and ra.organization.org_type and ra.organization.org_type.name.lower() == "cdl")
        for ra in roles
    )
    if is_cdl_admin:
        logger.debug("dashboard(): user=%s mapped to CDL Head dashboard via role fallback", user.id)
        return redirect('cdl_head_dashboard')
    if is_cdl_employee:
        logger.debug("dashboard(): user=%s mapped to CDL Work dashboard via role fallback", user.id)
        return redirect('cdl_work_dashboard')

    is_student = ('student' in role_lc) or email.endswith('@christuniversity.in')
    
    # Set session role for sidebar permissions
    if is_student:
        request.session["role"] = "student"
    else:
        request.session["role"] = "faculty"
    
    dashboard_template = "core/student_dashboard.html" if is_student else "core/dashboard.html"

    # ---- defaults (avoid UnboundLocalError) ----
    my_events = EventProposal.objects.none()
    other_events = EventProposal.objects.none()
    upcoming_events_count = 0
    organized_events_count = 0
    this_week_events = 0
    students_participated = 0
    my_students = Student.objects.none()
    my_classes = Class.objects.none()
    user_proposals = EventProposal.objects.none()
    calendar_events = []

    # ---- data (wrapped for safety) ----
    try:
        finalized_events = EventProposal.objects.filter(status='finalized').distinct()

        if is_student:
            my_events = EventProposal.objects.filter(
                Q(submitted_by=user) | Q(status='finalized')
            ).distinct()
        else:
            my_events = finalized_events.filter(
                Q(submitted_by=user) | Q(faculty_incharges=user)
            ).distinct()

        other_events = finalized_events.exclude(
            Q(submitted_by=user) | Q(faculty_incharges=user)
        ).distinct()

        # Upcoming events: prefer user's organizations if student; otherwise count all finalized upcoming
        now_dt = timezone.now()
        today = timezone.localdate()
        if is_student:
            user_org_ids = list(roles.filter(organization__isnull=False).values_list('organization_id', flat=True))
            upcoming_events_count = finalized_events.filter(
                Q(organization_id__in=user_org_ids),
            ).filter(
                Q(event_datetime__gte=now_dt) | Q(event_start_date__gte=today)
            ).count()
        else:
            upcoming_events_count = finalized_events.filter(
                Q(event_datetime__gte=now_dt) | Q(event_start_date__gte=today)
            ).count()

        organized_events_count = EventProposal.objects.filter(submitted_by=user).count()

        week_start = timezone.now().date() - timezone.timedelta(days=timezone.now().weekday())
        week_end = week_start + timezone.timedelta(days=6)
        this_week_events = finalized_events.filter(
            event_datetime__date__gte=week_start,
            event_datetime__date__lte=week_end
        ).count()

        students_participated = finalized_events.aggregate(
            total=Sum('fest_fee_participants') + Sum('conf_fee_participants')
        )['total'] or 0

        my_students = Student.objects.filter(mentor=user)
        my_classes = Class.objects.filter(teacher=user, is_active=True)

        user_proposals = EventProposal.objects.filter(submitted_by=user).order_by('-updated_at')[:5]

        all_events = finalized_events.filter(event_datetime__isnull=False)
        calendar_events = [{
            'id': e.id,
            'title': e.event_title,
            'date': e.event_datetime.strftime('%Y-%m-%d'),
            'datetime': e.event_datetime.strftime('%Y-%m-%d %H:%M'),
            'venue': e.venue or '',
            'organization': e.organization.name if e.organization else '',
            'submitted_by': e.submitted_by.get_full_name() or e.submitted_by.username,
            'participants': e.fest_fee_participants or e.conf_fee_participants or 0,
            'is_my_event': user in [e.submitted_by] + list(e.faculty_incharges.all())
        } for e in all_events]

    except Exception:  # keep UI alive even if data fails
        pass

    # ---- student-only bindings ----
    participated_events_count = my_events.count() if is_student else 0
    # Count distinct organizations for current user (for student KPI)
    try:
        org_count = (
            roles.filter(organization__isnull=False)
            .values_list('organization_id', flat=True)
            .distinct()
            .count()
        )
    except Exception:
        org_count = 0
    achievements_count = 0
    clubs_count = 0
    activity_score = 0
    recent_activity = []
    proposals_min = [{'title': p.event_title, 'status': p.get_status_display()} for p in user_proposals]

    # ---- context (always defined) ----
    context = {
        "my_events": my_events,
        "other_events": other_events,
        "upcoming_events_count": upcoming_events_count,
        "organized_events_count": organized_events_count,
        "this_week_events": this_week_events,
        "students_participated": students_participated,
        "my_students": my_students,
        "my_classes": my_classes,
        "role_names": [ra.role.name for ra in roles],
        "user": user,
        "user_proposals": user_proposals,
        "calendar_events": calendar_events,

        # student dashboard bindings
        "participated_events_count": participated_events_count,
        "achievements_count": achievements_count,
        "clubs_count": clubs_count,
        "activity_score": activity_score,
        "recent_activity": recent_activity,
        "proposals": proposals_min,
    "org_count": org_count,
    }

        # --- robust template selection ---
    from django.template.loader import select_template

    candidates = ["core/student_dashboard.html", "student_dashboard.html"] if is_student else ["core/dashboard.html", "dashboard.html"]
    tpl = select_template(candidates)  # picks the first that actually exists
    try:
        roles_dbg = [
            {
                'role': (ra.role.name if ra.role else None),
                'org': (ra.organization.name if ra.organization else None),
                'org_type': (ra.organization.org_type.name if ra.organization and ra.organization.org_type else None),
            }
            for ra in roles
        ]
        logger.debug(
            "dashboard(): rendering %s for user=%s roles=%s",
            tpl.template.name, user.id, roles_dbg,
        )
    except Exception:
        pass
    return render(request, tpl.template.name, context)


@login_required
def event_contribution_data(request):
    """API endpoint for event contribution chart data"""
    user = request.user
    organization_id = request.GET.get('organization_id', None)
    
    # Get user's organizations
    user_organizations = user.role_assignments.all()
    
    if organization_id and organization_id != 'all':
        try:
            # Filter by specific organization
            selected_org = Organization.objects.get(id=organization_id)
            organizations = user_organizations.filter(organization=selected_org)
        except Organization.DoesNotExist:
            return JsonResponse({'error': 'Organization not found'}, status=404)
    else:
        # Get all user's organizations
        organizations = user_organizations
    
    chart_data = []
    total_events = 0
    total_user_events = 0
    
    for role_assignment in organizations:
        org = role_assignment.organization
        if not org:
            continue
            
        # Count total events in this organization
        org_total_events = EventProposal.objects.filter(organization=org).count()
        
        # Count events user participated in, organized, or was faculty in-charge of
        user_events_query = Q(organization=org) & (
            Q(submitted_by=user) |  # User is the proposer
            Q(faculty_incharges=user) |  # User is faculty in-charge
            Q(participants__user=user)  # User is a participant through Student profile
        )
        
        user_events_count = EventProposal.objects.filter(user_events_query).distinct().count()
        
        if org_total_events > 0:
            contribution_percent = (user_events_count / org_total_events) * 100
        else:
            contribution_percent = 0
            
        chart_data.append({
            'organization': org.name,
            'organization_id': org.id,
            'total_events': org_total_events,
            'user_events': user_events_count,
            'percentage': round(contribution_percent, 1),
            'role': role_assignment.role.name if role_assignment.role else 'Unknown'
        })
        
        total_events += org_total_events
        total_user_events += user_events_count
    
    # Calculate overall contribution
    overall_percentage = (total_user_events / total_events * 100) if total_events > 0 else 0
    
    return JsonResponse({
        'chart_data': chart_data,
        'total_events': total_events,
        'total_user_events': total_user_events,
        'overall_percentage': round(overall_percentage, 1),
        'organizations': [
            {'id': ra.organization.id, 'name': ra.organization.name} 
            for ra in user.role_assignments.all() if ra.organization
        ]
    })

@login_required
def propose_event(request):
    """
    This is the *old* quick proposal form. If you want to keep it, now use Organization instead of Department.
    """
    if request.method == "POST":
        org_type_name = request.POST.get("organization_type", "").strip()
        org_name = request.POST.get("organization", "").strip()
        organization = None
        if org_type_name and org_name:
            # Validate org_type_name exists to prevent typos creating unwanted entries
            try:
                org_type_obj = OrganizationType.objects.get(name=org_type_name)
            except OrganizationType.DoesNotExist:
                messages.error(request, f"Organization type '{org_type_name}' does not exist.")
                return redirect('propose_event')
            organization, _ = Organization.objects.get_or_create(name=org_name, org_type=org_type_obj)

        title = request.POST.get("title", "").strip()
        desc  = request.POST.get("description", "").strip()

        roles = [ra.role.name for ra in request.user.role_assignments.all()]
        user_type = ", ".join(roles) or getattr(request.user.profile, "role", "")

        EventProposal.objects.create(
            submitted_by=request.user,
            organization=organization,
            user_type=user_type,
            title=title,
            description=desc,
        )
        return redirect("dashboard")

    org_types = OrganizationType.objects.all().order_by('name')
    return render(request, "core/event_proposal.html", {"organization_types": org_types})

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
#  Admin Dashboard and User Management
# ─────────────────────────────────────────────────────────────
@login_required
def select_dashboard(request, dashboard_key):
    """Handle dashboard selection and redirect to appropriate dashboard"""
    from .models import DashboardAssignment
    
    # Verify user has access to this dashboard
    available_dashboards = dict(DashboardAssignment.get_user_dashboards(request.user))
    
    if dashboard_key not in available_dashboards and not request.user.is_superuser:
        messages.error(request, "You don't have access to that dashboard.")
        return redirect('dashboard')
    
    # Set session data for the selected dashboard
    request.session['selected_dashboard'] = dashboard_key
    
    # Route to appropriate dashboard
    if dashboard_key == 'admin':
        return redirect('admin_dashboard')
    elif dashboard_key == 'faculty':
        request.session["role"] = "faculty"
        logger.debug("select_dashboard: user=%s -> faculty dashboard", request.user.id)
        return _render_faculty_dashboard(request)
    elif dashboard_key == 'student':
        request.session["role"] = "student"
        logger.debug("select_dashboard: user=%s -> student dashboard", request.user.id)
        return _render_student_dashboard(request)
    elif dashboard_key == 'cdl_head':
        logger.debug("select_dashboard: user=%s -> cdl_head dashboard", request.user.id)
        return redirect('cdl_head_dashboard')
    elif dashboard_key == 'cdl_work':
        logger.debug("select_dashboard: user=%s -> cdl_work dashboard", request.user.id)
        return redirect('cdl_work_dashboard')
    else:
        messages.error(request, "Invalid dashboard selection.")
        return redirect('dashboard')


def _render_faculty_dashboard(request):
    """Render faculty dashboard with existing logic"""
    user = request.user
    roles = RoleAssignment.objects.filter(user=user).select_related('role', 'organization')
    
    # ---- defaults (avoid UnboundLocalError) ----
    my_events = EventProposal.objects.none()
    other_events = EventProposal.objects.none()
    upcoming_events_count = 0
    organized_events_count = 0
    this_week_events = 0
    students_participated = 0
    my_students = Student.objects.none()
    classes_count = 0
    recent_activity = []
    user_proposals = []
    calendar_events = []
    org_count = 0
    mentee_count = 0

    # ---- common: events for calendar ----
    from datetime import timedelta
    from emt.models import EventProposal
    
    try:
        my_events = EventProposal.objects.filter(
            Q(submitted_by=user) | Q(faculty_incharges=user)
        ).distinct().order_by('-start_date')[:10]

        other_events = EventProposal.objects.exclude(
            Q(submitted_by=user) | Q(faculty_incharges=user)
        ).filter(status='approved').order_by('-start_date')[:5]

        calendar_events = list(my_events) + list(other_events)
        
        # KPI calculations
        upcoming_events_count = my_events.filter(
            start_date__gte=timezone.now().date()
        ).count()
        
        organized_events_count = my_events.count()
        
        this_week_events = my_events.filter(
            start_date__gte=timezone.now().date(),
            start_date__lte=timezone.now().date() + timedelta(days=7)
        ).count()

    except Exception as e:
        print(f"Event loading error: {e}")

    # ---- faculty-specific data ----
    try:
        my_students = Student.objects.filter(mentor=user)
        from core.models import Class
        my_classes = Class.objects.filter(teacher=user, is_active=True)
        classes_count = my_classes.count()
        mentee_count = my_students.count()
        
        # Calculate students who participated in events
        students_participated = my_students.filter(
            user__in=EventProposal.objects.filter(
                Q(submitted_by=user) | Q(faculty_incharges=user)
            ).values_list('participants__user', flat=True)
        ).distinct().count()

    except Exception as e:
        print(f"Faculty data loading error: {e}")

    # ---- user organizations ----
    try:
        user_organizations = Organization.objects.filter(
            Q(role_assignments__user=user) | Q(memberships__user=user)
        ).distinct()
        org_count = user_organizations.count()
    except Exception as e:
        print(f"Organization loading error: {e}")
        user_organizations = Organization.objects.none()

    # ---- user proposals for API ----
    try:
        user_proposals = list(my_events.values(
            'id', 'title', 'status', 'start_date', 'end_date', 
            'organization__name', 'description'
        ))
        for proposal in user_proposals:
            if proposal['start_date']:
                proposal['start_date'] = proposal['start_date'].isoformat()
            if proposal['end_date']:
                proposal['end_date'] = proposal['end_date'].isoformat()
    except Exception as e:
        print(f"Proposals serialization error: {e}")
        user_proposals = []

    # ---- final context ----
    context = {
        "user": user,
        "roles": roles,
        "my_events": my_events,
        "other_events": other_events,
        "upcoming_events_count": upcoming_events_count,
        "organized_events_count": organized_events_count,
        "this_week_events": this_week_events,
        "students_participated": students_participated,
        "classes_count": classes_count,
        "mentee_count": mentee_count,
        "org_count": org_count,
        "calendar_events": calendar_events,
        "user_proposals": user_proposals,
        "role_names": [ra.role.name for ra in roles],
    }

    return render(request, "core/dashboard.html", context)


def _render_student_dashboard(request):
    """Render student dashboard with existing logic"""
    user = request.user
    roles = RoleAssignment.objects.filter(user=user).select_related('role', 'organization')
    
    # ---- defaults ----
    participated_events_count = 0
    achievements_count = 0
    clubs_count = 0
    activity_score = 0
    recent_activity = []
    user_proposals = []
    calendar_events = []
    org_count = 0

    # ---- student-specific data ----
    try:
        from emt.models import Student
        student_profile = Student.objects.filter(user=user).first()
        
        if student_profile:
            # Get events where student participated
            participated_events = EventProposal.objects.filter(
                participants=student_profile
            ).distinct()
            participated_events_count = participated_events.count()
            
            # Mock achievements and activity score
            achievements_count = participated_events_count // 3
            activity_score = min(participated_events_count * 10, 100)
            
            calendar_events = list(participated_events[:10])

    except Exception as e:
        print(f"Student data loading error: {e}")

    # ---- user organizations ----
    try:
        user_organizations = Organization.objects.filter(
            Q(role_assignments__user=user) | Q(memberships__user=user)
        ).distinct()
        org_count = user_organizations.count()
        clubs_count = user_organizations.filter(
            org_type__name__icontains='club'
        ).count()
    except Exception as e:
        print(f"Organization loading error: {e}")

    # ---- user proposals for API ----
    try:
        user_events = EventProposal.objects.filter(
            Q(submitted_by=user) | Q(participants__user=user)
        ).distinct()[:10]
        
        user_proposals = list(user_events.values(
            'id', 'title', 'status', 'start_date', 'end_date',
            'organization__name', 'description'
        ))
        for proposal in user_proposals:
            if proposal['start_date']:
                proposal['start_date'] = proposal['start_date'].isoformat()
            if proposal['end_date']:
                proposal['end_date'] = proposal['end_date'].isoformat()
    except Exception as e:
        print(f"Student proposals error: {e}")
        user_proposals = []

    # ---- final context ----
    context = {
        "user": user,
        "roles": roles,
        "participated_events_count": participated_events_count,
        "achievements_count": achievements_count,
        "clubs_count": clubs_count,
        "activity_score": activity_score,
        "org_count": org_count,
        "calendar_events": calendar_events,
        "user_proposals": user_proposals,
        "role_names": [ra.role.name for ra in roles],
        "recent_activity": recent_activity,
    }

    return render(request, "core/student_dashboard.html", context)


# core/views.py

@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    """
    Render the admin dashboard with dynamic analytics and calendar events.
    """
    from django.contrib.auth.models import User
    from django.db.models import Q
    from datetime import timedelta
    import json
    from emt.models import EventReport # Make sure this is imported

    # --- Role statistics logic (this part is correct) ---
    all_assignments = RoleAssignment.objects.select_related('role', 'user').filter(
        user__is_active=True,
        user__last_login__isnull=False,
    )
    counted_users = {'faculty': set(), 'student': set(), 'hod': set()}
    for assignment in all_assignments:
        role_name = (getattr(assignment.role, 'name', "") or "").lower()
        user_id = assignment.user.id
        if 'faculty' in role_name:
            counted_users['faculty'].add(user_id)
        elif 'student' in role_name:
            counted_users['student'].add(user_id)
        elif 'hod' in role_name or 'head' in role_name:
            counted_users['hod'].add(user_id)
    
    # === CORRECTED LOGIC FOR EVENT REPORT STATS ===
    total_event_reports = EventReport.objects.count()
    
    # We assume a report is 'pending' if 'iqac_feedback' is empty.
    pending_event_reports = EventReport.objects.filter(Q(iqac_feedback__isnull=True) | Q(iqac_feedback='')).count()
    
    # We assume a report is 'reviewed' if 'iqac_feedback' is NOT empty.
    reviewed_event_reports = EventReport.objects.filter(iqac_feedback__isnull=False).exclude(iqac_feedback='').count()
    
    # NOTE: There is no obvious field for 'rejected'. I've set this to 0.
    # You will need to adjust this logic if you have a specific way to track rejections.
    rejected_event_reports = 0 
    # ===============================================

    stats = {
        'students': len(counted_users['student']),
        'faculties': len(counted_users['faculty']),
        'hods': len(counted_users['hod']),
        'centers': Organization.objects.filter(is_active=True).count(),
        'departments': Organization.objects.filter(org_type__name__icontains='department', is_active=True).count(),
        'clubs': Organization.objects.filter(org_type__name__icontains='club', is_active=True).count(),
        'total_proposals': EventProposal.objects.count(),
        'pending_proposals': EventProposal.objects.filter(status__in=['submitted', 'under_review']).count(),
        'approved_proposals': EventProposal.objects.filter(status__in=['approved', 'finalized']).count(),
        'rejected_proposals': EventProposal.objects.filter(status='rejected').count(),
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True, last_login__isnull=False).count(),
        'new_users_this_week': User.objects.filter(
            is_active=True,
            last_login__isnull=False,
            date_joined__gte=timezone.now() - timedelta(days=7),
        ).count(),
        'total_reports': Report.objects.count() + total_event_reports,
        'total_event_reports': total_event_reports,
        'pending_event_reports': pending_event_reports,
        'reviewed_event_reports': reviewed_event_reports,
        'rejected_event_reports': rejected_event_reports,
        'database_status': 'Operational',
        'email_status': 'Active',
        'storage_status': '45% Used',
        'last_backup': timezone.now().strftime("%b %d, %Y"),
    }
    
    # --- Recent activities logic (this part is correct) ---
    recent_activities = []
    recent_proposals = EventProposal.objects.select_related('submitted_by').order_by('-created_at')[:5]
    for proposal in recent_proposals:
        recent_activities.append({
            'type': 'proposal',
            'title': f"Proposal by {proposal.submitted_by.get_full_name() if proposal.submitted_by else ''}",
            'description': f"New event proposal: {getattr(proposal, 'event_title', getattr(proposal, 'title', 'Untitled Event'))}",
            'user': proposal.submitted_by.get_full_name() if proposal.submitted_by else '',
            'timestamp': proposal.created_at,
            'status': proposal.get_status_display()
        })
    recent_reports = Report.objects.select_related('submitted_by').order_by('-created_at')[:3]
    for report in recent_reports:
        recent_activities.append({
            'type': 'report',
            'title': f"Report by {report.submitted_by.get_full_name() if report.submitted_by else 'System'}",
            'description': f"Report submitted: {report.title}",
            'user': report.submitted_by.get_full_name() if report.submitted_by else 'System',
            'timestamp': report.created_at,
            'status': getattr(report, 'status', '')
        })
    recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activities = recent_activities[:8]
    
    # --- Calendar events logic (this part is correct) ---
    calendar_event_proposals = EventProposal.objects.filter(
        status__in=['approved', 'finalized'],
        event_start_date__isnull=False
    ).select_related('organization')
    events_list = []
    for event in calendar_event_proposals:
        events_list.append({
            'title': event.event_title or 'Untitled Event',
            'date': event.event_start_date.strftime('%Y-%m-%d'),
            'description': f"Organized by {event.organization.name if event.organization else 'N/A'}"
        })
    events_json_string = json.dumps(events_list)
    
    context = {
        'stats': stats,
        'recent_activities': recent_activities,
        'events': events_json_string,
    }
    
    return render(request, 'core/admin_dashboard.html', context)

@user_passes_test(lambda u: u.is_superuser)
def admin_user_panel(request):
    return render(request, "core/admin_user_panel.html")


# ===================================================================
# SINGLE-PAGE ROLE MANAGEMENT VIEW
# ===================================================================

@user_passes_test(lambda u: u.is_superuser)
def admin_role_management(request, organization_id=None):
    """Fixed role management with deduplication"""
    
    if organization_id:
        # Direct access to one organization's roles
        org = get_object_or_404(Organization, id=organization_id)
        show_archived = request.GET.get('archived') in ("1", "true", "True")
        base_qs = OrganizationRole.all_objects if show_archived else OrganizationRole.objects
        roles = base_qs.filter(organization=org)
        if show_archived:
            roles = roles.filter(status='archived')
        roles = roles.order_by('name')
        assignments = (
            RoleAssignment.objects.filter(organization=org)
            .select_related("user", "role")
            .order_by("user__username")
        )

        context = {
            'selected_organization': org,
            'roles': roles,
            'role_assignments': assignments,
            'step': 'single_org_roles',
            'show_archived': show_archived,
        }
        return render(request, "core/admin_role_management.html", context)
    
    else:
        org_type_id = request.GET.get('org_type_id')
        
        if org_type_id:
            # Show UNIQUE roles from this org type (no duplicates)
            org_type = get_object_or_404(OrganizationType, id=org_type_id)
            show_archived = request.GET.get('archived') in ("1", "true", "True")
            
            # Get all organizations of this type for the add form
            organizations = Organization.objects.filter(
                org_type=org_type, 
                is_active=True
            ).order_by('name')
            
            # Get UNIQUE role names (deduplicated) from all organizations of this type
            base_qs = OrganizationRole.all_objects if show_archived else OrganizationRole.objects
            role_names_qs = base_qs.filter(
                organization__org_type=org_type,
                organization__is_active=True
            )
            if show_archived:
                role_names_qs = role_names_qs.filter(status='archived')
            unique_role_names = role_names_qs.values_list('name', flat=True).distinct().order_by('name')
            
            # For each unique role name, get one representative role object (matching the status view)
            unique_roles = []
            for role_name in unique_role_names:
                role_qs = base_qs.filter(
                    organization__org_type=org_type,
                    organization__is_active=True,
                    name=role_name
                )
                if show_archived:
                    role_qs = role_qs.filter(status='archived')
                role = role_qs.select_related('organization').first()
                if role:
                    unique_roles.append(role)
            
            context = {
                'selected_org_type': org_type,
                'roles': unique_roles,  # Now deduplicated
                'organizations': organizations,
                'step': 'org_type_roles',
                'show_archived': show_archived,
            }
            return render(request, "core/admin_role_management.html", context)
        
        else:
            # Show organization types
            org_types = OrganizationType.objects.all().order_by('name')
            
            context = {
                'org_types': org_types,
                'step': 'org_types'
            }
            return render(request, "core/admin_role_management.html", context)


@user_passes_test(lambda u: u.is_superuser)
@require_POST
def add_org_role(request, organization_id):
    """Add role to ALL organizations of the same type"""
    org = get_object_or_404(Organization, id=organization_id)
    name = request.POST.get("name", "").strip()

    if not name:
        messages.error(request, "Role name is required.")
        return redirect(f"{reverse('admin_role_management')}?org_type_id={org.org_type.id}")

    # Check if this role already exists in ANY organization of this type
    existing_role = OrganizationRole.objects.filter(
        organization__org_type=org.org_type,
        name__iexact=name
    ).first()
    if existing_role:
        messages.warning(request, f"Role '{name}' already exists for {org.org_type.name}s.")
        return redirect(f"{reverse('admin_role_management')}?org_type_id={org.org_type.id}")

    # Add this role to ALL organizations of this type
    all_orgs_of_type = Organization.objects.filter(
        org_type=org.org_type,
        is_active=True
    )
    
    for target_org in all_orgs_of_type:
        if not OrganizationRole.objects.filter(
            organization=target_org,
            name__iexact=name
        ).exists():
            OrganizationRole.objects.create(
                organization=target_org,
                name=name,
                is_active=True
            )
    return redirect(f"{reverse('admin_role_management')}?org_type_id={org.org_type.id}")


@user_passes_test(lambda u: u.is_superuser)
@require_POST
def add_role(request):
    """Add a role by organization or organization type (used by tests and legacy UI)."""
    name = request.POST.get("name", "").strip()
    org_id = request.POST.get("org_id")
    org_type_id = request.POST.get("org_type_id")

    if not name:
        return HttpResponseRedirect(reverse("admin_role_management"))

    if org_id:
        orgs = Organization.objects.filter(id=org_id, is_active=True)
        redirect_url = reverse("admin_role_management_org", args=[org_id])
    elif org_type_id:
        orgs = Organization.objects.filter(org_type_id=org_type_id, is_active=True)
        redirect_url = reverse("admin_role_management") + f"?org_type_id={org_type_id}"
    else:
        orgs = []
        redirect_url = reverse("admin_role_management")

    for org in orgs:
        if not OrganizationRole.all_objects.filter(organization=org, name__iexact=name).exists():
            OrganizationRole.objects.create(organization=org, name=name, is_active=True)

    return HttpResponseRedirect(redirect_url)


@user_passes_test(lambda u: u.is_superuser)
@require_POST
def update_org_role(request, role_id):
    """Update this role for ALL organizations of the same type"""
    role = get_object_or_404(OrganizationRole, id=role_id)
    org_type = role.organization.org_type
    old_name = role.name
    
    new_name = request.POST.get("name", "").strip()
    new_description = request.POST.get("description", "").strip()

    if not new_name:
        messages.error(request, "Role name is required.")
        return redirect(f"{reverse('admin_role_management')}?org_type_id={org_type.id}")

    # Update all roles with the old name from all organizations of this type
    updated_count = OrganizationRole.objects.filter(
        organization__org_type=org_type,
        name__iexact=old_name
    ).update(
        name=new_name,
        description=new_description
    )
    
    messages.success(request, f"Role updated for {updated_count} {org_type.name}(s).")
    return redirect(f"{reverse('admin_role_management')}?org_type_id={org_type.id}")


@user_passes_test(lambda u: u.is_superuser)
@require_POST
def toggle_org_role(request, role_id):
    """Handles activating or deactivating a role."""
    role = get_object_or_404(OrganizationRole, id=role_id)
    role.is_active = not role.is_active
    role.save()
    status = "activated" if role.is_active else "deactivated"
    messages.success(request, f"Role '{role.name}' has been {status}.")
    return redirect("admin_role_management_org", organization_id=role.organization.id)


@user_passes_test(lambda u: u.is_superuser)
@require_POST
def delete_org_role(request, role_id):
    """Archive this role across ALL organizations of the same type (no hard delete)"""
    role = get_object_or_404(OrganizationRole, id=role_id)
    org_type = role.organization.org_type
    role_name = role.name
    
    # Archive all roles with this name from all organizations of this type
    roles_qs = OrganizationRole.all_objects.filter(
        organization__org_type=org_type,
        name__iexact=role_name
    )
    archived_count = 0
    for r in roles_qs:
        if r.status != r.Status.ARCHIVED:
            r.archive(by=request.user)
            archived_count += 1
    messages.success(request, f"Role '{role_name}' archived for {archived_count} {org_type.name}(s).")
    return redirect(f"{reverse('admin_role_management')}?org_type_id={org_type.id}")

# ===================================================================
# END OF SINGLE-PAGE ROLE MANAGEMENT
# ===================================================================

@user_passes_test(lambda u: u.is_superuser)
def admin_user_management(request):
    """
    Manages and displays a paginated list of users with enhanced filtering capabilities.
    Supports multi-select filtering for organization types, organizations, and roles.
    """
    # Base queryset
    users_list = User.objects.select_related('profile').prefetch_related(
        'role_assignments__organization__org_type', 
        'role_assignments__role'
    ).order_by('-date_joined')

    # --- CORRECTED LOGIC FOR HANDLING FILTERS ---
    q = request.GET.get('q', '').strip()
    # Start with IDs from manual filters (e.g., role[]=123)
    role_ids = request.GET.getlist('role[]') 
    
    role_name_from_url = request.GET.get('role', '').strip()
    initial_roles_json = '[]'
    
    # If a role NAME came from the dashboard URL, find its IDs
    if role_name_from_url:
        matching_roles = OrganizationRole.objects.filter(
            name__iexact=role_name_from_url, is_active=True
        ).select_related('organization')
        
        matching_role_ids = list(matching_roles.values_list('id', flat=True))
        
        if matching_role_ids:
            # Add the found IDs to our list for filtering
            role_ids.extend([str(rid) for rid in matching_role_ids])
            
            # Prepare the initial data (ID and Text) for the template's JavaScript
            initial_roles_data = [
                {'id': role.id, 'text': f"{role.name} ({role.organization.name})"} 
                for role in matching_roles
            ]
            initial_roles_json = json.dumps(initial_roles_data)
    
    org_ids = request.GET.getlist('organization[]')
    org_type_ids = request.GET.getlist('org_type[]')
    status = request.GET.get('status')
    
    # Clean empty values and remove duplicates
    role_ids = list(set([r for r in role_ids if r and r.strip()]))
    org_ids = list(set([o for o in org_ids if o and o.strip()]))
    org_type_ids = list(set([ot for ot in org_type_ids if ot and ot.strip()]))
    # --- END OF CORRECTION ---
    
    # Apply all filters to the queryset
    if q:
        users_list = users_list.filter(
            Q(email__icontains=q) | Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | Q(username__icontains=q)
        )
    
    if role_ids:
        users_list = users_list.filter(role_assignments__role_id__in=role_ids)
    
    if org_ids:
        users_list = users_list.filter(role_assignments__organization_id__in=org_ids)
        
    if org_type_ids:
        users_list = users_list.filter(role_assignments__organization__org_type_id__in=org_type_ids)

    if status == 'active':
        users_list = users_list.filter(is_active=True, last_login__isnull=False)
    elif status == 'inactive':
        users_list = users_list.filter(Q(is_active=False) | Q(last_login__isnull=True))

    users_list = users_list.distinct()

    # (The rest of the function remains the same)
    paginator = Paginator(users_list, 25)
    page_number = request.GET.get('page')
    try:
        users = paginator.page(page_number)
    except PageNotAnInteger:
        users = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages)

    all_roles = OrganizationRole.objects.filter(is_active=True)
    if org_ids:
        all_roles = all_roles.filter(organization_id__in=org_ids)
    if role_ids:
        all_roles = (all_roles | OrganizationRole.objects.filter(id__in=role_ids)).distinct()
        
    all_roles = all_roles.select_related('organization').order_by('name')
    all_organizations = Organization.objects.filter(is_active=True).order_by('name')
    all_org_types = OrganizationType.objects.filter(is_active=True).order_by('name')

    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']

    context = {
        'users': users,
        'all_roles': all_roles,
        'all_organizations': all_organizations,
        'all_org_types': all_org_types,
        'current_filters': {
            'q': q,
            'role': role_ids,
            'organization': org_ids,
            'org_type': org_type_ids,
            'status': status,
        },
        'query_params': query_params.urlencode(),
        'total_users': users_list.count(),
        'initial_roles_json': initial_roles_json,
    }
    
    return render(request, "core/admin_user_management.html", context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def api_admin_search_users(request):
    """
    API endpoint to provide user data for the server-side DataTables.
    """
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 25))
    
    # Get filter parameters from the request
    q = request.GET.get('q', '').strip()
    role_name_from_url = request.GET.get('role_name', '').strip() # e.g., "Student"
    role_ids = request.GET.getlist('role[]')
    org_ids = request.GET.getlist('organization[]')
    org_type_ids = request.GET.getlist('org_type[]')
    status = request.GET.get('status')

    # Base queryset
    users_qs = User.objects.select_related('profile').prefetch_related(
        'role_assignments__organization__org_type',
        'role_assignments__role'
    ).order_by('-date_joined')

    # Apply filters
    if q:
        users_qs = users_qs.filter(
            Q(email__icontains=q) | Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | Q(username__icontains=q)
        )
    
    if role_name_from_url and not role_ids:
        matching_role_ids = list(
            OrganizationRole.objects.filter(name__iexact=role_name_from_url, is_active=True)
            .values_list('id', flat=True)
        )
        if matching_role_ids:
            users_qs = users_qs.filter(role_assignments__role_id__in=matching_role_ids)

    if role_ids:
        users_qs = users_qs.filter(role_assignments__role_id__in=role_ids)
    if org_ids:
        users_qs = users_qs.filter(role_assignments__organization_id__in=org_ids)
    if org_type_ids:
        users_qs = users_qs.filter(role_assignments__organization__org_type_id__in=org_type_ids)

    if status == 'active':
        users_qs = users_qs.filter(is_active=True, last_login__isnull=False)
    elif status == 'inactive':
        users_qs = users_qs.filter(Q(is_active=False) | Q(last_login__isnull=True))

    users_qs = users_qs.distinct()
    
    total_records = users_qs.count()
    
    # Paginate the queryset
    paginated_users = users_qs[start : start + length]
    
    # Serialize the data
    dashboard_url = reverse('dashboard')
    data = []
    for user in paginated_users:
        roles = []
        organizations = []
        for ra in user.role_assignments.all():
            if ra.role:
                roles.append(f'<span class="badge bg-primary">{ra.role.name}</span>')
            if ra.organization:
                organizations.append(f'<div>{ra.organization.name} <small class="text-muted">({ra.organization.org_type.name})</small></div>')
        
        status_badge = '<span class="badge bg-success">Active</span>' if user.is_active and user.last_login else '<span class="badge bg-danger">Inactive</span>'
        if user.is_superuser:
            status_badge += ' <span class="badge bg-warning">Admin</span>'

        action_buttons = f"""
            <a href="/core-admin/users/{user.id}/edit/" class="btn btn-sm btn-outline-primary"><i class="fas fa-edit"></i> Edit</a>
        """
        if user.id != request.user.id:
            action_buttons += f"""
                <a href="/core-admin/impersonate/{user.id}/?next={dashboard_url}" class="btn btn-sm btn-outline-secondary ms-1">
                    <i class="fas fa-user-secret"></i> Login as
                </a>
            """
            
        data.append({
            's_no': start + len(data) + 1,
            'name': f'<strong>{user.get_full_name() or user.username}</strong><small class="text-muted d-block">@{user.username}</small>',
            'email': f'<a href="mailto:{user.email}">{user.email}</a>' if user.email else '<span class="text-muted">No email</span>',
            'roles': '<br>'.join(roles) or '<span class="text-muted">No roles</span>',
            'organization': '<br>'.join(organizations) or '<span class="text-muted">No assignments</span>',
            'date_joined': user.date_joined.strftime("%b %d, %Y %H:%M"),
            'status': status_badge,
            'action': action_buttons
        })

    return JsonResponse({
        "draw": draw,
        "recordsTotal": total_records,
        "recordsFiltered": total_records,
        "data": data,
    })

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    RoleFormSet = inlineformset_factory(
        User,
        RoleAssignment,
        form=RoleAssignmentForm,
        formset=RoleAssignmentFormSet,
        fields=("role", "organization"),
        extra=0,
        can_delete=True,
    )
    next_url = safe_next(request, fallback="admin_user_management")
    if request.method == "POST":
        formset = RoleFormSet(request.POST, instance=user)
        user.first_name = request.POST.get("first_name", "").strip()
        user.last_name = request.POST.get("last_name", "").strip()
        user.email = request.POST.get("email", "").strip()
        user.save()

        if formset.is_valid():
            formset.save()
            messages.success(request, "User roles updated successfully.")
            return redirect(next_url)
        else:
            messages.error(request, "Please fix the errors below and try again.")
    else:
        formset = RoleFormSet(instance=user)

    org_ids = list(
        user.role_assignments.exclude(organization__isnull=True).values_list("organization_id", flat=True)
    )
    org_qs = Organization.objects.filter(Q(is_active=True) | Q(id__in=org_ids)).select_related("org_type")
    role_ids = list(user.role_assignments.values_list("role_id", flat=True))
    role_qs = OrganizationRole.objects.filter(Q(is_active=True) | Q(id__in=role_ids)).select_related("organization")

    organizations_json = {
        str(o.id): {"name": o.name, "org_type": str(o.org_type_id)} for o in org_qs
    }
    roles_json = {
        str(r.id): {"name": r.name, "organization": str(r.organization_id)} for r in role_qs
    }

    return render(
        request,
        "core/admin_user_edit.html",
        {
            "user_obj": user,
            "formset": formset,
            "organizations": org_qs,
            "organization_types": OrganizationType.objects.filter(),
            "organizations_json": json.dumps(organizations_json),
            "roles_json": json.dumps(roles_json),
            "next": next_url,
        },
    )


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_user_activate(request, user_id):
    """Activate a user and redirect back safely."""
    user = get_object_or_404(User, id=user_id)
    user.is_active = True
    user.save()
    messages.success(
        request,
        f"User '{user.get_full_name() or user.username}' activated successfully.",
    )
    return redirect(safe_next(request, fallback="admin_user_management"))


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_user_deactivate(request, user_id):
    """Deactivate a user and redirect back safely."""
    user = get_object_or_404(User, id=user_id)
    user.is_active = False
    user.save()
    messages.success(
        request,
        f"User '{user.get_full_name() or user.username}' deactivated successfully.",
    )
    return redirect(safe_next(request, fallback="admin_user_management"))

@user_passes_test(lambda u: u.is_superuser)
def admin_event_proposals(request):
    proposals = EventProposal.objects.all().order_by("-created_at")
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    if q:
        proposals = proposals.filter(
            Q(event_title__icontains=q) |
            Q(submitted_by__username__icontains=q) |
            Q(organization__name__icontains=q) |
            Q(organization__org_type__name__icontains=q)
        )
    if status:
        proposals = proposals.filter(status=status)
    return render(request, "core/admin_event_proposals.html", {"proposals": proposals})

@user_passes_test(lambda u: u.is_superuser)
def event_proposal_json(request, proposal_id):
    p = get_object_or_404(EventProposal, id=proposal_id)
    return JsonResponse({
        "title": getattr(p, 'event_title', getattr(p, 'title', 'Untitled Event')),
        "description": getattr(p, 'description', ''),
        "organization": str(p.organization) if p.organization else None,
        "user_type": getattr(p, 'user_type', ''),
        "status": p.status,
        "status_display": p.get_status_display(),
        "date_submitted": p.created_at.strftime("%Y-%m-%d %H:%M"),
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
    reports = Report.objects.select_related('submitted_by').all().order_by('-created_at')
    context = {"reports": reports}
    return render(request, 'core/admin_reports.html', context)

@user_passes_test(lambda u: u.is_superuser)
@require_POST
def restore_org_role(request, role_id):
    """Restore this role across ALL organizations of the same type (from archived)."""
    role = get_object_or_404(OrganizationRole.all_objects, id=role_id)
    org_type = role.organization.org_type
    role_name = role.name

    roles_qs = OrganizationRole.all_objects.filter(
        organization__org_type=org_type,
        name__iexact=role_name,
        status='archived'
    )
    restored = 0
    for r in roles_qs:
        r.restore()
        restored += 1
    messages.success(request, f"Role '{role_name}' restored for {restored} {org_type.name}(s).")
    return redirect(f"{reverse('admin_role_management')}?org_type_id={org_type.id}&archived=1")

STATUSES = ['submitted', 'under_review', 'approved', 'rejected']

from emt.models import EventProposal

STATUSES = ['submitted', 'under_review', 'rejected', 'finalized']  # ensure this matches your status choices

def iqac_suite_dashboard(request):
    user_proposals = (
        EventProposal.objects
        .filter(submitted_by=request.user)
        .order_by("-created_at")
    )

    for proposal in user_proposals:
        proposal.statuses = STATUSES
        proposal.status_index = STATUSES.index(proposal.status) if proposal.status in STATUSES else -1
        proposal.progress_percent = ((proposal.status_index + 1) / len(STATUSES)) * 100 if proposal.status_index != -1 else 0
        proposal.current_label = proposal.status.replace('_', ' ').title()

    context = {
        "user_proposals": user_proposals,
        "statuses": STATUSES,
    }
    return render(request, "dashboard.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_master_data(request):
    from transcript.models import get_active_academic_year
    import json

    academic_year = get_active_academic_year()

    org_types = OrganizationType.objects.filter(is_active=True).order_by('name')
    orgs_by_type = {}
    orgs_by_type_json = {}

    for org_type in org_types:
        qs = Organization.objects.filter(org_type=org_type).order_by('name')
        orgs_by_type[org_type.name] = qs
        active_orgs = qs.filter(is_active=True)
        orgs_by_type_json[org_type.name.lower()] = [{'id': o.id, 'name': o.name} for o in active_orgs]

    return render(request, "core/admin_master_data.html", {
        "org_types": org_types,
        "orgs_by_type": orgs_by_type,
        "orgs_by_type_json": json.dumps(orgs_by_type_json),
        "academic_year": academic_year,
    })



@login_required
@user_passes_test(lambda u: u.is_superuser)
@csrf_exempt
def admin_master_data_edit(request, model_name, pk):
    MODEL_MAP = {
        "organization": Organization,
        "organization_type": OrganizationType,
    }
    Model = MODEL_MAP.get(model_name)
    if request.method == "POST" and Model:
        try:
            obj = get_object_or_404(Model, pk=pk)
            data = json.loads(request.body)
            name = data.get("name", "").strip()
            is_active = data.get("is_active", True)
            parent_id = data.get("parent")
            
            if not name:
                return JsonResponse({"success": False, "error": "Name is required"})
            
            obj.name = name
            if hasattr(obj, "is_active"):
                obj.is_active = is_active
            
            if model_name == "organization" and hasattr(obj, "parent"):
                if parent_id and parent_id.strip():
                    try:
                        parent_obj = Organization.objects.get(id=parent_id)
                        if obj.org_type.parent_type and parent_obj.org_type != obj.org_type.parent_type:
                            return JsonResponse({
                                "success": False, 
                                "error": f"Invalid parent type. Expected {obj.org_type.parent_type.name}, got {parent_obj.org_type.name}"
                            })
                        obj.parent = parent_obj
                    except Organization.DoesNotExist:
                        return JsonResponse({"success": False, "error": "Parent organization not found"})
                    except ValueError:
                        return JsonResponse({"success": False, "error": "Invalid parent ID"})
                else:
                    obj.parent = None
            
            obj.save()
            
            response_data = {
                "success": True,
                "name": obj.name,
                "is_active": getattr(obj, "is_active", True),
            }
            
            if hasattr(obj, "parent"):
                response_data["parent"] = obj.parent.name if obj.parent else None
            
            return JsonResponse(response_data)
            
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON data"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False, "error": "Invalid request"})

@login_required
@user_passes_test(lambda u: u.is_superuser)
@csrf_exempt
def admin_master_data_add(request, model_name):
    MODEL_MAP = {
        "organization": Organization,
        "organization_type": OrganizationType,
    }
    Model = MODEL_MAP.get(model_name)
    if request.method == "POST" and Model:
        try:
            data = json.loads(request.body)
            name = data.get("name", "").strip()
            
            if not name:
                return JsonResponse({"success": False, "error": "Name is required"})
            
            if model_name == "organization":
                org_type_name = data.get("org_type", "").strip()
                parent_id = data.get("parent")
                
                if not org_type_name:
                    return JsonResponse({"success": False, "error": "Organization type required"})
                
                try:
                    org_type_obj = OrganizationType.objects.get(name__iexact=org_type_name)
                except OrganizationType.DoesNotExist:
                    return JsonResponse({"success": False, "error": f"Organization type '{org_type_name}' does not exist"})
                
                if Organization.objects.filter(name__iexact=name, org_type=org_type_obj).exists():
                    return JsonResponse({"success": False, "error": f"{org_type_obj.name} with name '{name}' already exists"})
                
                parent_obj = None
                if parent_id:
                    try:
                        parent_obj = Organization.objects.get(id=parent_id)
                    except Organization.DoesNotExist:
                        return JsonResponse({"success": False, "error": "Parent organization not found"})
                
                obj = Organization.objects.create(
                    name=name,
                    org_type=org_type_obj,
                    parent=parent_obj,
                    is_active=True
                )
                
            elif model_name == "organization_type":
                parent_id = data.get("parent")
                
                if OrganizationType.objects.filter(name__iexact=name).exists():
                    return JsonResponse({"success": False, "error": f"Organization type '{name}' already exists"})
                
                parent_obj = None
                if parent_id:
                    try:
                        parent_obj = OrganizationType.objects.get(id=parent_id)
                    except OrganizationType.DoesNotExist:
                        return JsonResponse({"success": False, "error": "Parent organization type not found"})
                
                obj = OrganizationType.objects.create(
                    name=name,
                    parent_type=parent_obj,
                    can_have_parent=bool(parent_obj),
                    is_active=True
                )
            else:
                obj, created = Model.objects.get_or_create(name=name, defaults={'is_active': True})
                if not created:
                    return JsonResponse({"success": False, "error": f"{model_name} already exists"})
            
            return JsonResponse({
                "success": True,
                "id": obj.id,
                "name": obj.name,
                "org_type": obj.org_type.name if model_name == "organization" else None,
                "parent": obj.parent.name if hasattr(obj, 'parent') and obj.parent else None,
                "is_active": getattr(obj, 'is_active', True)
            })
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON data"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False, "error": "Invalid request"})


@login_required
@user_passes_test(lambda u: u.is_superuser)
@csrf_exempt
def admin_master_data_delete(request, model_name, pk):
    MODEL_MAP = {
        "organization": Organization,
        "organization_type": OrganizationType,
    }
    Model = MODEL_MAP.get(model_name)
    if request.method == "POST" and Model:
        obj = get_object_or_404(Model, pk=pk)
        obj.delete()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "error": "Invalid request"})

@user_passes_test(lambda u: u.is_superuser)
def admin_proposal_detail(request, proposal_id):
    proposal = get_object_or_404(
        EventProposal.objects.select_related("organization").prefetch_related(
            "faculty_incharges", "speakers", "expense_details", "approval_steps"
        ),
        id=proposal_id,
    )
    logger.debug(
        "Loaded proposal %s '%s' (org=%s, faculty=%d, speakers=%d, expenses=%d, steps=%d)",
        proposal.id,
        proposal.event_title,
        proposal.organization,
        len(proposal.faculty_incharges.all()),
        len(proposal.speakers.all()),
        len(proposal.expense_details.all()),
        len(proposal.approval_steps.all()),
    )
    steps = [
        {"key": "draft", "label": "Draft"},
        {"key": "submitted", "label": "Submitted"},
        {"key": "under_review", "label": "Under Review"},
        {"key": "approved", "label": "Approved"},
        {"key": "rejected", "label": "Rejected"},
        {"key": "returned", "label": "Returned for Revision"},
    ]
    return render(
        request,
        "core/admin_proposal_detail.html",
        {"proposal": proposal, "steps": steps},
    )

@login_required
def proposal_detail(request, proposal_id):
    """Public view for event proposal details - accessible to all logged-in users"""
    proposal = get_object_or_404(
        EventProposal.objects.select_related("organization").prefetch_related(
            "faculty_incharges", "speakers", "expense_details", "approval_steps"
        ),
        id=proposal_id,
    )
    logger.debug(
        "Loaded public proposal %s '%s' (org=%s, faculty=%d, speakers=%d, expenses=%d, steps=%d)",
        proposal.id,
        proposal.event_title,
        proposal.organization,
        len(proposal.faculty_incharges.all()),
        len(proposal.speakers.all()),
        len(proposal.expense_details.all()),
        len(proposal.approval_steps.all()),
    )
    return render(request, "core/admin_proposal_detail.html", {"proposal": proposal})

@user_passes_test(lambda u: u.is_superuser)
def admin_settings_dashboard(request):
    return render(request, "core/admin_settings.html")

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_sidebar_permissions(request):
    """Allow admin to configure sidebar items per user or role."""
    import json
    from django.contrib.auth.models import User
    from django.urls import reverse
    from django.contrib import messages
    from .models import OrganizationType, OrganizationRole, RoleAssignment, SidebarPermission
    from core.navigation import NAV_ITEMS, SIDEBAR_ITEM_IDS
    import logging
    logger = logging.getLogger(__name__)

    # Roles are now OrganizationRole entries (no generic labels)

    # Housekeeping: remove stale records where both user and role are set
    # (we only support either user-specific override (role="") or role-based with user=None)
    SidebarPermission.objects.filter(user__isnull=False).exclude(role__in=["", None]).delete()

    # Filters from query params
    org_type_id = (request.GET.get("org_type") or "").strip()
    org_role_id = (request.GET.get("org_role") or request.GET.get("role") or "").strip()

    # Base users queryset
    users_qs = User.objects.all().order_by("username")
    if org_type_id:
        ra_qs = RoleAssignment.objects.filter(role__organization__org_type_id=org_type_id)
        if org_role_id:
            ra_qs = ra_qs.filter(role_id=org_role_id)
        users_qs = users_qs.filter(id__in=ra_qs.values_list("user_id", flat=True)).distinct()
    users = users_qs

    # Top-level nav items (hierarchical!)
    nav_items = NAV_ITEMS

    # Utility: build assigned tree
    def build_assigned_tree(assigned_ids, items):
        result = []
        for item in items:
            if "children" in item:
                children = build_assigned_tree(assigned_ids, item["children"])
                if children:
                    result.append({
                        "id": item["id"],
                        "label": item["label"],
                        "children": children
                    })
            else:
                if item["id"] in assigned_ids:
                    result.append({"id": item["id"], "label": item["label"]})
        return result

    # Utility: build available = all minus assigned
    def build_available_tree(assigned_ids, items):
        result = []
        for item in items:
            if "children" in item:
                children = build_available_tree(assigned_ids, item["children"])
                if children:
                    result.append({
                        "id": item["id"],
                        "label": item["label"],
                        "children": children
                    })
                elif item["id"] not in assigned_ids:
                    result.append({"id": item["id"], "label": item["label"]})
            else:
                if item["id"] not in assigned_ids:
                    result.append({"id": item["id"], "label": item["label"]})
        return result

    # Load current permission
    selected_user = request.GET.get("user")
    selected_role_id = (request.GET.get("role") or request.GET.get("org_role") or "").strip()

    permission = None
    if selected_user:
        permission = SidebarPermission.objects.filter(user_id=selected_user).first()
    else:
        if selected_role_id and selected_role_id.isdigit():
            role_key = f"orgrole:{selected_role_id}"
            permission = SidebarPermission.objects.filter(
                user__isnull=True, role=role_key
            ).first()

    if request.method == "POST":
        target_users = request.POST.getlist("users") or []
        # Backward compat: single "user" param
        if not target_users:
            u = request.POST.get("user")
            if u:
                target_users = [u]
        target_role_id = (request.POST.get("role") or "").strip()

        assigned_order_raw = request.POST.get("assigned_order")
        try:
            assigned_items = json.loads(assigned_order_raw) if assigned_order_raw else []
        except Exception:
            assigned_items = []

        invalid_ids = [i for i in assigned_items if i not in SIDEBAR_ITEM_IDS]
        if invalid_ids:
            messages.error(request, f"Unknown sidebar item(s): {', '.join(invalid_ids)}")
            return redirect(reverse("admin_sidebar_permissions"))

        if target_users:
            for uid in target_users:
                if User.objects.filter(id=uid, is_superuser=True).exists() and not assigned_items:
                    messages.warning(
                        request,
                        "Admin must always retain full sidebar; ignoring empty assignment.",
                    )
                    continue
                permission, _ = SidebarPermission.objects.get_or_create(
                    user_id=uid,
                    role="",
                )
                permission.items = assigned_items
                permission.save()
        else:
            if target_role_id and target_role_id.isdigit():
                role_key = f"orgrole:{target_role_id}"
                permission, _ = SidebarPermission.objects.get_or_create(
                    user=None,
                    role=role_key,
                )
                permission.items = assigned_items
                permission.save()
            else:
                messages.error(
                    request,
                    "Please select a valid organization role to save permissions.",
                )
                return redirect(reverse("admin_sidebar_permissions"))

        messages.success(request, "Sidebar permissions updated")
        logger.info(
            "Sidebar permissions updated for users=%s role=%s",
            ",".join(target_users) or None,
            target_role_id,
        )

        redirect_url = reverse("admin_sidebar_permissions")
        if len(target_users) == 1:
            redirect_url += f"?user={target_users[0]}"
        elif target_role_id:
            redirect_url += f"?role={target_role_id}"
        if org_type_id:
            redirect_url += f"&org_type={org_type_id}"
        if org_role_id and not target_role_id:
            redirect_url += f"&role={org_role_id}"
        return redirect(redirect_url)

    # Build available/assigned lists
    assigned_set = set(permission.items) if permission else set()
    assigned_permissions = build_assigned_tree(assigned_set, nav_items)
    available_permissions = build_available_tree(assigned_set, nav_items)

    # Build roles list from OrganizationRole (optionally filtered by org type)
    # NOTE: Keep org context in label to distinguish same-named roles across orgs
    roles_qs = OrganizationRole.objects.select_related("organization", "organization__org_type").all()
    if org_type_id:
        roles_qs = roles_qs.filter(organization__org_type_id=org_type_id)

    org_roles = []
    for role in roles_qs.order_by("name", "organization__name"):
        label = role.name
        if role.organization:
            label = f"{role.name} – {role.organization.name} ({role.organization.org_type.name})"
        org_roles.append({"id": role.id, "name": label})

    context = {
        "organization_types": list(OrganizationType.objects.filter(is_active=True).values("id", "name")),
        "org_roles": org_roles,
        "selected_org_type": org_type_id,
        "selected_org_role": org_role_id,
        "users": [{"id": u.id, "name": (u.get_full_name().strip() or u.username)} for u in users],
        "nav_items": nav_items,
        "permission": permission,
        "selected_user": selected_user,
        # Use organization role id for selection; plain role labels are not used in UI
        "selected_role": selected_role_id,
        "selected_user_id": selected_user,
        "selected_role_id": selected_role_id,
        "available_permissions": json.dumps(available_permissions),
        "assigned_permissions": json.dumps(assigned_permissions),
    }
    return render(request, "core_admin/sidebar_permissions.html", context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def enhanced_permissions_management(request):
    """Enhanced permissions management interface"""
    from .models import DashboardAssignment, OrganizationType, OrganizationRole
    from django.contrib.auth.models import User
    import json
    
    # Get all data for the interface
    organization_types = OrganizationType.objects.all()
    roles = OrganizationRole.objects.select_related('organization', 'organization__org_type').all()
    users = User.objects.filter(is_active=True).select_related()
    
    # Add role list to users for filtering
    for user in users:
        user_roles = RoleAssignment.objects.filter(user=user).values_list('role__name', flat=True)
        user.role_list = json.dumps(list(user_roles))
    
    # Dashboard choices
    dashboard_choices = DashboardAssignment.DASHBOARD_CHOICES
    
    # Sidebar items
    sidebar_items = [
        ('dashboard', 'Dashboard'),
        ('events', 'Event Management'),
        ('cdl', 'CDL (Creative & Design Lab)'),
        ('pso_psos', 'PSO & POs Management'),
        ('transcript', 'Transcript Management'),
        ('profile', 'User Profile'),
        ('admin', 'Admin Functions'),
    ]
    
    context = {
        'organization_types': organization_types,
        'roles': roles,
        'users': users,
        'dashboard_choices': json.dumps(dashboard_choices),
        'sidebar_items': json.dumps(sidebar_items),
        'available_permissions': json.dumps([item[0] for item in sidebar_items]),
        'assigned_permissions': json.dumps([]),
    }
    
    return render(request, 'core_admin/enhanced_permissions.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_http_methods(["POST"])
def api_save_dashboard_assignments(request):
    """API endpoint to save dashboard assignments"""
    from .models import DashboardAssignment
    from django.http import JsonResponse
    from django.views.decorators.http import require_http_methods
    import json
    
    try:
        data = json.loads(request.body)
        assignments = data.get('assignments', [])
        user_id = data.get('user')
        role = data.get('role')
        
        if not user_id and not role:
            return JsonResponse({'success': False, 'error': 'Must specify either user or role'})
        
        # Clear existing assignments
        if user_id:
            DashboardAssignment.objects.filter(user_id=user_id, role='').delete()
        elif role:
            DashboardAssignment.objects.filter(user__isnull=True, role=role).delete()
        
        # Create new assignments
        for dashboard in assignments:
            if user_id:
                DashboardAssignment.objects.create(
                    user_id=user_id,
                    role='',
                    dashboard=dashboard
                )
            else:
                DashboardAssignment.objects.create(
                    user=None,
                    role=role,
                    dashboard=dashboard
                )
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_http_methods(["POST"])
def api_save_sidebar_permissions(request):
    """API endpoint to save sidebar permissions"""
    from .models import SidebarPermission
    from django.http import JsonResponse
    from core.navigation import SIDEBAR_ITEM_IDS
    import json

    try:
        data = json.loads(request.body)
        assignments = data.get("assignments", [])
        users = data.get("users") or []
        single_user = data.get("user")
        role = (data.get("role") or "").strip()

        if single_user:
            users = [single_user]

        # Exactly one target: users OR role
        if bool(users) == bool(role):
            return JsonResponse({
                "success": False,
                "error": "Specify exactly one of users or role",
            })

        # Validate IDs
        invalid_ids = [i for i in assignments if i not in SIDEBAR_ITEM_IDS]
        if invalid_ids:
            return JsonResponse({
                "success": False,
                "error": f"Unknown sidebar item(s): {', '.join(invalid_ids)}",
            })

        # Persist
        if users:
            from django.contrib.auth.models import User
            valid_ids = list(User.objects.filter(id__in=users).values_list("id", flat=True))
            if len(valid_ids) != len(users):
                return JsonResponse({"success": False, "error": "Invalid user id"})

            for uid in users:
                perm, created = SidebarPermission.objects.get_or_create(
                    user_id=uid,
                    role="",
                    defaults={"items": assignments},
                )
                if not created:
                    perm.items = assignments
                perm.save()
        else:
            # Accept numeric org role id; store as key orgrole:<id>
            role_key = f"orgrole:{role}" if role.isdigit() else role.lower()
            perm, created = SidebarPermission.objects.get_or_create(
                user=None,
                role=role_key,
                defaults={"items": assignments},
            )
            if not created:
                perm.items = assignments
            perm.save()

        resp = JsonResponse({"success": True})
        resp["Cache-Control"] = "no-store"
        return resp
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def api_get_dashboard_assignments(request):
    """API endpoint to get dashboard assignments for a user or role"""
    from .models import DashboardAssignment
    from django.http import JsonResponse
    
    user_id = request.GET.get('user')
    role = (request.GET.get('role') or '').strip()
    
    assignments = []
    
    if user_id:
        assignments = list(DashboardAssignment.objects.filter(
            user_id=user_id, is_active=True
        ).values_list('dashboard', flat=True))
    elif role:
        assignments = list(DashboardAssignment.objects.filter(
            user__isnull=True, role=role, is_active=True
        ).values_list('dashboard', flat=True))
    
    return JsonResponse({'assignments': assignments})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def api_get_sidebar_permissions(request):
    """API endpoint to get sidebar permissions for a user or role"""
    from .models import SidebarPermission
    from django.http import JsonResponse
    
    user_id = request.GET.get('user')
    role = (request.GET.get('role') or '').strip()
    
    assignments = []
    
    if user_id:
        permission = SidebarPermission.objects.filter(user_id=user_id).first()
        if permission:
            assignments = permission.items
    elif role:
        role_key = f"orgrole:{role}" if role.isdigit() else role.lower()
        permission = SidebarPermission.objects.filter(
            user__isnull=True, role__iexact=role_key
        ).first()
        if permission:
            assignments = permission.items
    
    return JsonResponse({'assignments': assignments})


@login_required
def api_my_sidebar(request):
    """Return computed sidebar permissions for the current user.

    Used by the client to detect changes and refresh the page/sidebar.
    """
    from django.http import JsonResponse
    from .models import SidebarPermission, RoleAssignment
    import logging

    logger = logging.getLogger(__name__)
    items = SidebarPermission.get_allowed_items(request.user)
    unrestricted = False
    allowed = []
    if items == "ALL":
        unrestricted = True
    else:
        allowed = items

    # Debug: user roles/org context
    try:
        roles = (
            RoleAssignment.objects.filter(user=request.user)
            .select_related('role', 'organization', 'organization__org_type')
        )
        roles_dbg = [
            {
                'role': (ra.role.name if ra.role else None),
                'org': (ra.organization.name if ra.organization else None),
                'org_type': (ra.organization.org_type.name if ra.organization and ra.organization.org_type else None),
            }
            for ra in roles
        ]
        logger.debug(
            "api_my_sidebar: user=%s unrestricted=%s allowed_count=%d roles=%s",
            request.user.id, unrestricted, len(allowed), roles_dbg,
        )
    except Exception:
        pass

    return JsonResponse({
        'unrestricted_nav': unrestricted,
        'allowed_nav_items': allowed,
    })


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_academic_year_settings(request):
    """Add and manage academic years.

    Displays existing academic years split into active and archived groups. Allows
    creation of new academic years and editing existing ones using the same
    form. The year string is derived from the provided start and end dates.
    """

    from datetime import datetime
    from transcript.models import AcademicYear

    # Editing existing year if ``id`` provided in POST or ``edit`` in GET
    edit_id = request.GET.get("edit")
    edit_year = None
    if edit_id:
        edit_year = get_object_or_404(AcademicYear, pk=edit_id)

    if request.method == "POST":
        year_id = request.POST.get("id")
        start = request.POST.get("start_date") or None
        end = request.POST.get("end_date") or None

        year_str = None
        if start:
            try:
                start_year = datetime.strptime(start, "%Y-%m-%d").year
                end_year = (
                    datetime.strptime(end, "%Y-%m-%d").year if end else start_year + 1
                )
                year_str = f"{start_year}-{end_year}"
            except ValueError:
                pass

        if year_id:
            obj = get_object_or_404(AcademicYear, pk=year_id)
            obj.year = year_str
            obj.start_date = start
            obj.end_date = end
            obj.save()
        else:
            # Ensure only one academic year is active at any time
            AcademicYear.objects.filter(is_active=True).update(is_active=False)
            AcademicYear.objects.create(
                year=year_str, start_date=start, end_date=end, is_active=True
            )
        return redirect("admin_academic_year_settings")

    active_years = AcademicYear.objects.filter(is_active=True).order_by("-start_date")
    archived_years = AcademicYear.objects.filter(is_active=False).order_by(
        "-start_date"
    )

    return render(
        request,
        "core/admin_academic_year_settings.html",
        {
            "active_years": active_years,
            "archived_years": archived_years,
            "edit_year": edit_year,
        },
    )


@login_required
@user_passes_test(lambda u: u.is_superuser)
def academic_year_archive(request, pk):
    """Archive the selected academic year."""

    from transcript.models import AcademicYear

    year = get_object_or_404(AcademicYear, pk=pk)
    if request.method == "POST":
        year.is_active = False
        year.save()
    return redirect("admin_academic_year_settings")


@login_required
@user_passes_test(lambda u: u.is_superuser)
def academic_year_restore(request, pk):
    """Restore an archived academic year."""

    from transcript.models import AcademicYear

    year = get_object_or_404(AcademicYear, pk=pk)
    if request.method == "POST":
        year.is_active = True
        year.save()
    return redirect("admin_academic_year_settings")

@user_passes_test(lambda u: u.is_superuser)
def master_data_dashboard(request):
    from transcript.models import AcademicYear
    from django.contrib.auth.models import User
    
    stats = {
        'organizations': Organization.objects.count(),
        'org_types': OrganizationType.objects.count(),
        'academic_years': AcademicYear.objects.count(),
        'active_users': User.objects.filter(is_active=True, last_login__isnull=False).count(),
    }
    
    recent_activities = [
        {
            'description': 'System initialized',
            'icon': 'info-circle',
            'created_at': timezone.now(),
        }
    ]
    
    return render(request, "core/master_data_dashboard.html", {
        'stats': stats,
        'recent_activities': recent_activities,
    })

@user_passes_test(lambda u: u.is_superuser)
def admin_approval_flow(request):
    """List all organizations grouped by type for approval flow management."""
    org_types = OrganizationType.objects.filter(is_active=True).order_by("name")
    orgs_by_type = {
        ot.name: Organization.objects.filter(org_type=ot, is_active=True).order_by("name")
        for ot in org_types
    }
    context = {
        "org_types": org_types,
        "orgs_by_type": orgs_by_type,
    }
    return render(request, "core/admin_approval_flow_list.html", context)


@user_passes_test(lambda u: u.is_superuser)
def admin_approval_flow_manage(request, org_id):
    """Display and edit approval flow for a single organization."""
    orgs = (
        Organization.objects.filter(is_active=True)
        .select_related("org_type")
        .order_by("org_type__name", "name")
    )
    org_types = OrganizationType.objects.all().order_by("name")
    selected_org = get_object_or_404(Organization, id=org_id)

    config, _ = ApprovalFlowConfig.objects.get_or_create(organization=selected_org)

    steps = (
        ApprovalFlowTemplate.objects.filter(organization=selected_org)
        .select_related("user")
        .order_by("step_order")
    )

    context = {
        "organizations": orgs,
        "org_types": org_types,
        "selected_org_id": org_id,
        "selected_org": selected_org,
        "existing_steps": steps,
        "require_faculty_incharge_first": config.require_faculty_incharge_first,
    }
    return render(request, "core/admin_approval_flow_manage.html", context)


@user_passes_test(lambda u: u.is_superuser)
def admin_approval_dashboard(request):
    """Intermediate page for approval related settings."""
    return render(request, "core/admin_approval_dashboard.html")


@user_passes_test(lambda u: u.is_superuser)
def admin_outcome_dashboard(request):
    """Intermediate page for outcome and SDG related settings."""
    return render(request, "core/admin_outcome_dashboard.html")


@user_passes_test(lambda u: u.is_superuser)
def admin_sdg_management(request):
    """Display Sustainable Development Goals."""
    from .models import SDGGoal, SDG_GOALS

    goals = SDGGoal.objects.filter(name__in=SDG_GOALS).order_by("id")
    return render(request, "core/admin_sdg_management.html", {"goals": goals})



@user_passes_test(lambda u: u.is_superuser)
def admin_pso_po_management(request):
    import json
    from .models import Program, ProgramOutcome, ProgramSpecificOutcome
    
    # Get dynamic organization types from database
    org_types = OrganizationType.objects.filter(is_active=True).order_by('name')
    orgs_by_type = {}
    orgs_by_type_json = {}

    for org_type in org_types:
        qs = Organization.objects.filter(org_type=org_type, is_active=True).order_by('name')
        orgs_by_type[org_type.name] = qs
        orgs_by_type_json[org_type.name.lower()] = [{'id': o.id, 'name': o.name} for o in qs]
    
    # Get all programs with their outcomes
    programs = Program.objects.prefetch_related('pos', 'psos').all().order_by("name")
    
    # Prepare programs data for frontend
    programs_data = {}
    org_outcome_counts = {}
    
    for program in programs:
        org_id = program.organization.id if program.organization else None
        if org_id:
            if org_id not in org_outcome_counts:
                org_outcome_counts[org_id] = {'po_count': 0, 'pso_count': 0}
            
            org_outcome_counts[org_id]['po_count'] += program.pos.count()
            org_outcome_counts[org_id]['pso_count'] += program.psos.count()
        
        programs_data[program.id] = {
            'id': program.id,
            'name': program.name,
            'organization_id': org_id,
            'organization_name': program.organization.name if program.organization else '',
            'pos': [{'id': po.id, 'description': po.description} for po in program.pos.all()],
            'psos': [{'id': pso.id, 'description': pso.description} for pso in program.psos.all()]
        }
    
    context = {
        "org_types": org_types,
        "orgs_by_type": orgs_by_type,
        "orgs_by_type_json": json.dumps(orgs_by_type_json),
        "programs": programs,
        "programs_data": json.dumps(programs_data),
        "org_outcome_counts": json.dumps(org_outcome_counts),
    }
    return render(request, "core/admin_pso_po_management.html", context)

@user_passes_test(lambda u: u.is_superuser)
def admin_outcomes_for_org(request, org_id: int):
    """Dedicated page to manage POs/PSOs for a single organization.
    The page loads outcomes via existing AJAX endpoints and reuses the
    admin_pso_po_management.js logic for inline add/edit/delete.
    """
    org = get_object_or_404(Organization, id=org_id)
    return render(request, "core/admin_outcomes_for_org.html", {"organization": org})

@user_passes_test(lambda u: u.is_superuser)
@require_http_methods(["GET", "POST", "PUT", "DELETE", "PATCH"])
def manage_program_outcomes(request, program_id=None):
    """API endpoint for managing Program Outcomes (POs and PSOs)"""
    from .models import Program, ProgramOutcome, ProgramSpecificOutcome
    import json
    
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            program = Program.objects.get(id=data['program_id'])
            outcome_type = data.get('type', '').upper()
            
            # Superuser-only for now; non-admin flows removed
            
            if outcome_type == 'PO':
                outcome = ProgramOutcome.objects.create(
                    program=program,
                    description=data['description']
                )
            elif outcome_type == 'PSO':
                outcome = ProgramSpecificOutcome.objects.create(
                    program=program,
                    description=data['description']
                )
            else:
                return JsonResponse({'success': False, 'error': 'Invalid outcome type'})
                
            return JsonResponse({
                'success': True, 
                'outcome': {'id': outcome.id, 'description': outcome.description}
            })
        except (Program.DoesNotExist, KeyError, json.JSONDecodeError) as e:
            return JsonResponse({'success': False, 'error': 'Invalid data: ' + str(e)})
    
    elif request.method == "PUT":
        try:
            data = json.loads(request.body)
            outcome_type = data.get('type', '').upper()
            
            if outcome_type == 'PO':
                outcome = ProgramOutcome.objects.get(id=data['outcome_id'])
                program = outcome.program
            elif outcome_type == 'PSO':
                outcome = ProgramSpecificOutcome.objects.get(id=data['outcome_id'])
                program = outcome.program
            else:
                return JsonResponse({'success': False, 'error': 'Invalid outcome type'})
            
            # Superuser-only for now; non-admin flows removed
                
            outcome.description = data['description']
            outcome.save()
            return JsonResponse({
                'success': True,
                'outcome': {'id': outcome.id, 'description': outcome.description}
            })
        except (ProgramOutcome.DoesNotExist, ProgramSpecificOutcome.DoesNotExist, KeyError, json.JSONDecodeError):
            return JsonResponse({'success': False, 'error': 'Invalid data'})
    
    elif request.method == "DELETE":
        try:
            data = json.loads(request.body)
            outcome_type = data.get('type', '').upper()
            
            if outcome_type == 'PO':
                outcome = ProgramOutcome.objects.get(id=data['outcome_id'])
                program = outcome.program
            elif outcome_type == 'PSO':
                outcome = ProgramSpecificOutcome.objects.get(id=data['outcome_id'])
                program = outcome.program
            else:
                return JsonResponse({'success': False, 'error': 'Invalid outcome type'})
            
            # Superuser-only for now; non-admin flows removed
                
            # Archive instead of permanent delete
            outcome.archive(by=request.user)
            return JsonResponse({'success': True, 'archived': True})
        except (ProgramOutcome.DoesNotExist, ProgramSpecificOutcome.DoesNotExist, KeyError, json.JSONDecodeError):
            return JsonResponse({'success': False, 'error': 'Invalid data'})
    elif request.method == "PATCH":
        # Restore archived outcome
        try:
            data = json.loads(request.body)
            outcome_type = data.get('type', '').upper()
            if outcome_type == 'PO':
                outcome = ProgramOutcome.all_objects.get(id=data['outcome_id'])
            elif outcome_type == 'PSO':
                outcome = ProgramSpecificOutcome.all_objects.get(id=data['outcome_id'])
            else:
                return JsonResponse({'success': False, 'error': 'Invalid outcome type'})

            # Superuser-only for now; non-admin flows removed

            outcome.restore()
            return JsonResponse({'success': True, 'restored': True})
        except (ProgramOutcome.DoesNotExist, ProgramSpecificOutcome.DoesNotExist, KeyError, json.JSONDecodeError):
            return JsonResponse({'success': False, 'error': 'Invalid data'})

@user_passes_test(lambda u: u.is_superuser)
@require_http_methods(["GET", "POST", "PUT", "DELETE"])
def manage_program_specific_outcomes(request, program_id=None):
    """API endpoint for managing Program Specific Outcomes (PSOs)"""
    from .models import Program, ProgramSpecificOutcome
    import json
    
    if request.method == "GET":
        if program_id:
            try:
                program = Program.objects.get(id=program_id)
                psos = list(program.psos.values('id', 'description'))
                return JsonResponse({
                    'success': True,
                    'program': {'id': program.id, 'name': program.name},
                    'outcomes': psos
                })
            except Program.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Program not found'})
        else:
            return JsonResponse({'success': False, 'error': 'Program ID required'})
    
    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            program = Program.objects.get(id=data['program_id'])
            pso = ProgramSpecificOutcome.objects.create(
                program=program,
                description=data['description']
            )
            return JsonResponse({
                'success': True,
                'outcome': {'id': pso.id, 'description': pso.description}
            })
        except (Program.DoesNotExist, KeyError, json.JSONDecodeError):
            return JsonResponse({'success': False, 'error': 'Invalid data'})
    
    elif request.method == "PUT":
        try:
            data = json.loads(request.body)
            pso = ProgramSpecificOutcome.objects.get(id=data['outcome_id'])
            pso.description = data['description']
            pso.save()
            return JsonResponse({
                'success': True,
                'outcome': {'id': pso.id, 'description': pso.description}
            })
        except (ProgramSpecificOutcome.DoesNotExist, KeyError, json.JSONDecodeError):
            return JsonResponse({'success': False, 'error': 'Invalid data'})
    
    elif request.method == "DELETE":
        try:
            data = json.loads(request.body)
            pso = ProgramSpecificOutcome.objects.get(id=data['outcome_id'])
            pso.delete()
            return JsonResponse({'success': True})
        except (ProgramSpecificOutcome.DoesNotExist, KeyError, json.JSONDecodeError):
            return JsonResponse({'success': False, 'error': 'Invalid data'})

@login_required
@require_POST
def create_program_for_organization(request):
    """API endpoint for creating a new program for an organization"""
    from .models import Organization, Program, POPSOAssignment
    import json
    
    try:
        data = json.loads(request.body)
        organization = Organization.objects.get(id=data['organization_id'])
        
        # Authorization: superuser OR assigned POPSO manager for this organization
        if not (
            request.user.is_superuser or 
            POPSOAssignment.objects.filter(
                organization=organization,
                assigned_user=request.user,
                is_active=True
            ).exists()
        ):
            return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
        
        # Check if program already exists for this organization
        existing_program = Program.objects.filter(
            organization=organization,
            name=data.get('program_name', f"{organization.name} Program")
        ).first()
        
        if existing_program:
            return JsonResponse({
                'success': True,
                'program': {
                    'id': existing_program.id,
                    'name': existing_program.name,
                    'organization_id': existing_program.organization.id
                }
            })
        
        # Create new program
        # If program_name key missing or blank, fallback to default name
        provided_name = data.get('program_name')
        program_name = (
            provided_name.strip()
            if (isinstance(provided_name, str) and provided_name.strip())
            else f"{organization.name} Program"
        )
        program = Program.objects.create(name=program_name, organization=organization)
        
        return JsonResponse({
            'success': True,
            'program': {
                'id': program.id,
                'name': program.name,
                'organization_id': program.organization.id
            }
        })
    except (Organization.DoesNotExist, KeyError, json.JSONDecodeError):
        return JsonResponse({'success': False, 'error': 'Invalid data'})

@require_GET
def get_approval_flow(request, org_id):
    steps = ApprovalFlowTemplate.objects.filter(organization_id=org_id).order_by('step_order')
    config = ApprovalFlowConfig.objects.filter(organization_id=org_id).first()
    data = [
        {
            'id': step.id,
            'step_order': step.step_order,
            'role_required': step.role_required,
            'role_display': step.get_role_required_display(),
            'user_id': step.user.id if step.user else None,
            'user_name': step.user.get_full_name() if step.user else '',
            'optional': step.optional,
        } for step in steps
    ]
    return JsonResponse({'success': True, 'steps': data,
                         'require_faculty_incharge_first': config.require_faculty_incharge_first if config else False})

@require_POST
@login_required
@user_passes_test(lambda u: _superuser_check(u))
def save_approval_flow(request, org_id):
    data = json.loads(request.body)
    steps = data.get('steps', [])
    require_first = data.get('require_faculty_incharge_first', False)
    org = Organization.objects.get(id=org_id)
    # Upsert steps to avoid unique_together conflicts and keep history
    existing_steps = {s.step_order: s for s in ApprovalFlowTemplate.all_objects.filter(organization=org)}
    provided_orders = set()
    for idx, step in enumerate(steps, 1):
        if not step.get('role_required'):
            continue
        provided_orders.add(idx)
        current = existing_steps.get(idx)
        if current:
            current.role_required = step.get('role_required')
            current.user_id = step.get('user_id')
            current.optional = step.get('optional', False)
            # If it was archived, restore it
            if getattr(current, 'status', None) == getattr(current, 'Status').ARCHIVED:
                current.restore()
            else:
                current.save(update_fields=['role_required', 'user_id', 'optional'])
        else:
            ApprovalFlowTemplate.objects.create(
                organization=org,
                step_order=idx,
                role_required=step.get('role_required'),
                user_id=step.get('user_id'),
                optional=step.get('optional', False)
            )
    # Archive any steps that are no longer present
    for order, obj in existing_steps.items():
        if order not in provided_orders and obj.status != obj.Status.ARCHIVED:
            obj.archive(by=request.user)

    config, _ = ApprovalFlowConfig.objects.get_or_create(organization=org)
    config.require_faculty_incharge_first = require_first
    config.save()

    return JsonResponse({'success': True})
def api_approval_flow_steps(request, org_id):
    steps = list(
        ApprovalFlowTemplate.objects.filter(organization_id=org_id).order_by('step_order').values(
            'id', 'step_order', 'role_required', 'user_id', 'optional'
        )
    )
    return JsonResponse({'success': True, 'steps': steps})

@require_POST
@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def delete_approval_flow(request, org_id):
    # Archive all approval flow steps for org instead of deleting
    steps = ApprovalFlowTemplate.all_objects.filter(organization_id=org_id)
    count = 0
    for step in steps:
        if step.status != step.Status.ARCHIVED:
            step.archive(by=request.user)
            count += 1
    return JsonResponse({'success': True, 'archived': count})
@login_required
@user_passes_test(lambda u: u.is_superuser)
def search_users(request):
    q = request.GET.get("q", "").strip()
    role = request.GET.get("role", "").strip()
    org_id = request.GET.get("org_id", "").strip()
    org_type_id = request.GET.get("org_type_id", "").strip()

    users = User.objects.all()

    if q:
        users = users.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
        )

    # --- Filter by role ---
    if role:
        users = users.filter(role_assignments__role__name__iexact=role)

    # --- Filter by organization/department ---
    if org_id:
        users = users.filter(role_assignments__organization_id=org_id)

    users = users.distinct()[:10]
    data = [
        {"id": u.id, "name": u.get_full_name() or u.username, "email": u.email}
        for u in users
    ]
    if not data:
        logging.debug(
            "search_users returned no results for q=%r role=%r org_id=%r org_type_id=%r",
            q,
            role,
            org_id,
            org_type_id,
        )
    return JsonResponse({"success": True, "users": data})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def organization_users(request, org_id):
    """Return users for a given organization, optional search by name or role."""
    q = request.GET.get("q", "")
    role = request.GET.get("role", "")
    org_type_id = request.GET.get("org_type_id", "")

    assignments = RoleAssignment.objects.filter(organization_id=org_id)
    if not assignments.exists() and org_type_id:
        assignments = RoleAssignment.objects.filter(organization__org_type_id=org_type_id)
    if role:
        assignments = assignments.filter(role__name__iexact=role)
    if q:
        assignments = assignments.filter(
            Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(user__email__icontains=q)
        )

    assignments = assignments.select_related("user").order_by("user__first_name", "user__last_name")

    users_data = [
        {
            "id": a.user.id,
            "name": a.user.get_full_name() or a.user.username,
            "role": a.role.name,
        }
        for a in assignments
    ]
    return JsonResponse({"success": True, "users": users_data})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def api_org_type_organizations(request, org_type_id):
    """Return active organizations for a given organization type."""
    orgs = Organization.objects.filter(org_type_id=org_type_id, is_active=True).order_by("name")
    data = [{"id": o.id, "name": o.name} for o in orgs]
    return JsonResponse({"success": True, "organizations": data})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def api_org_type_roles(request, org_type_id):
    """Return distinct role names for a given organization type."""
    # First, get all organizations of this type
    organizations = Organization.objects.filter(org_type_id=org_type_id)
    
    if not organizations.exists():
        return JsonResponse({"success": False, "roles": [], "error": "No organizations found for this type"})

    # Get the organization with the most roles (likely Commerce in your case)
    org_with_most_roles = (
        organizations
        .annotate(role_count=models.Count('organizationrole'))
        .order_by('-role_count')
        .first()
    )

    # Get all roles from the organization with the most roles
    template_roles = (
        OrganizationRole.objects
        .filter(organization=org_with_most_roles)
        .values('name', 'is_active')
        .distinct()
        .order_by('name')
    )

    # For each organization that doesn't have all roles, create the missing ones
    with transaction.atomic():
        for org in organizations:
            existing_role_names = set(
                OrganizationRole.objects
                .filter(organization=org)
                .values_list('name', flat=True)
            )
            
            # Create any missing roles
            for template_role in template_roles:
                if template_role['name'] not in existing_role_names:
                    OrganizationRole.objects.create(
                        organization=org,
                        name=template_role['name'],
                        is_active=template_role['is_active']
                    )

    # Now fetch all roles for this organization type
    roles = (
        OrganizationRole.objects
        .filter(organization__org_type_id=org_type_id)
        .values('id', 'name', 'is_active')
        .distinct()
        .order_by('name')
    )

    # Deduplicate by name, preferring active roles
    seen = {}
    unique_roles = []
    for r in roles:
        name = r['name']
        if name not in seen or (not seen[name]['is_active'] and r['is_active']):
            seen[name] = r
            unique_roles.append({
                'id': r['id'],
                'name': r['name'],
                'is_active': r['is_active']
            })

    return JsonResponse({"success": True, "roles": unique_roles})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def api_organization_roles(request, org_id):
    """Return role names for a specific organization."""
    roles = (
        OrganizationRole.objects
        .filter(organization_id=org_id, is_active=True)
        .values("id", "name")
        .order_by("name")
    )
    data = list(roles)
    return JsonResponse({"success": True, "roles": data})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def api_filter_organizations(request):
    """Return organizations filtered by org_type_ids with search support."""
    org_type_ids = request.GET.getlist('org_type_ids[]')
    search = request.GET.get('search', '').strip()
    
    orgs = Organization.objects.filter(is_active=True)
    
    if org_type_ids:
        orgs = orgs.filter(org_type_id__in=org_type_ids)
    
    if search:
        orgs = orgs.filter(name__icontains=search)
    
    orgs = orgs.select_related('org_type').order_by('name')[:50]  # Limit for performance
    
    data = [{"id": o.id, "name": o.name, "org_type": o.org_type.name} for o in orgs]
    return JsonResponse({"success": True, "organizations": data})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def api_filter_roles(request):
    """Return roles filtered by organization_ids with search support."""
    organization_ids = request.GET.getlist('organization_ids[]')
    search = request.GET.get('search', '').strip()
    
    roles = OrganizationRole.objects.filter(is_active=True)
    
    if organization_ids:
        roles = roles.filter(organization_id__in=organization_ids)
    
    if search:
        roles = roles.filter(name__icontains=search)
    
    roles = roles.select_related('organization').order_by('name')[:50]  # Limit for performance
    
    data = [{"id": r.id, "name": r.name, "organization": r.organization.name} for r in roles]
    return JsonResponse({"success": True, "roles": data})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def api_search_org_types(request):
    """Return organization types with search support."""
    search = request.GET.get('search', '').strip()
    
    org_types = OrganizationType.objects.filter(is_active=True)
    
    if search:
        org_types = org_types.filter(name__icontains=search)
    
    org_types = org_types.order_by('name')[:50]  # Limit for performance
    
    data = [{"id": ot.id, "name": ot.name} for ot in org_types]
    return JsonResponse({"success": True, "org_types": data})


# PSO/PO Management API endpoints
from django.views.decorators.http import require_GET, require_POST

@require_GET
@user_passes_test(lambda u: u.is_superuser)
def get_pso_po_data(request, org_type, org_id):
    """Get POs and PSOs for a specific organization"""
    try:
        from .models import Program, ProgramOutcome, ProgramSpecificOutcome
        
        org = Organization.objects.get(id=org_id)
        
        programs = Program.objects.filter(organization=org)
        
        pos = []
        psos = []
        
        if programs.exists():
            program = programs.first()
            pos = list(ProgramOutcome.objects.filter(program=program).values('id', 'description'))
            psos = list(ProgramSpecificOutcome.objects.filter(program=program).values('id', 'description'))
        
        return JsonResponse({
            'success': True,
            'pos': pos,
            'psos': psos,
            'organization': org.name
        })
    except Organization.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Organization not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_POST
@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def add_outcome(request, outcome_type):
    """Add a new PO or PSO"""
    try:
        from .models import Program, ProgramOutcome, ProgramSpecificOutcome
        
        data = json.loads(request.body)
        org_id = data.get('org_id')
        description = data.get('description')
        
        if not org_id or not description:
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
        
        org = Organization.objects.get(id=org_id)
        
        program, created = Program.objects.get_or_create(
            organization=org,
            defaults={'name': f"{org.name} Program"}
        )
        
        if outcome_type == 'po':
            ProgramOutcome.objects.create(program=program, description=description)
        elif outcome_type == 'pso':
            ProgramSpecificOutcome.objects.create(program=program, description=description)
        else:
            return JsonResponse({'success': False, 'error': 'Invalid outcome type'})
        
        return JsonResponse({'success': True})
        
    except Organization.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Organization not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_POST
@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def delete_outcome(request, outcome_type, outcome_id):
    """Archive a PO or PSO (legacy endpoint)."""
    try:
        from .models import ProgramOutcome, ProgramSpecificOutcome
        
        if outcome_type == 'po':
            outcome = ProgramOutcome.all_objects.get(id=outcome_id)
        elif outcome_type == 'pso':
            outcome = ProgramSpecificOutcome.all_objects.get(id=outcome_id)
        else:
            return JsonResponse({'success': False, 'error': 'Invalid outcome type'})
        
        if outcome.status != getattr(outcome, 'Status').ARCHIVED:
            outcome.archive(by=request.user)
        return JsonResponse({'success': True, 'archived': True})
        
    except (ProgramOutcome.DoesNotExist, ProgramSpecificOutcome.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Outcome not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse
from itertools import chain
from operator import attrgetter
from core.models import Report  # instead of SubmittedReport
from emt.models import EventReport

@login_required
def admin_reports_view(request):
    try:
        # Use Report instead of SubmittedReport here:
        submitted_reports = Report.objects.all()

        generated_reports = EventReport.objects.select_related('proposal').all()

        all_reports_list = list(chain(submitted_reports, generated_reports))

        all_reports_list.sort(key=attrgetter('created_at'), reverse=True)

        context = {'reports': all_reports_list}

        return render(request, 'core/admin_reports.html', context)

    except Exception as e:
        print(f"Error in admin_reports_view: {e}")
        return HttpResponse(f"An error occurred: {e}", status=500)


@login_required
@admin_required
def admin_reports_approve(request, report_id: int):
    """Approve a core Report and redirect back to the reports list.

    Template links use GET, so accept GET and POST. Only core Report items
    (without a related proposal) get Approve/Reject actions.
    """
    report = get_object_or_404(Report, id=report_id)
    # Only transition if currently submitted; otherwise just no-op update
    if getattr(report, "status", None) == "submitted":
        report.status = "approved"
        report.save(update_fields=["status"])
    return redirect("admin_reports")


@login_required
@admin_required
def admin_reports_reject(request, report_id: int):
    """Reject a core Report and redirect back to the reports list.

    Template links use GET, so accept GET and POST. Optionally, a feedback
    message could be added later via POST; for now we just set status.
    """
    report = get_object_or_404(Report, id=report_id)
    if getattr(report, "status", None) == "submitted":
        report.status = "rejected"
        report.save(update_fields=["status"])
    return redirect("admin_reports")


@login_required
@admin_required
def admin_history(request):
    """List activity log entries for administrators.

    The history table is intended as an audit log for the whole site, so it
    must display actions performed by **all** users rather than only the
    requesting administrator. We therefore start with a queryset containing
    every :class:`ActivityLog` record and then apply any filtering based on
    the request parameters.
    """

    # Begin with activity from every user.
    logs = ActivityLog.objects.select_related("user")

    # Text search across user name, username, action and description
    query = request.GET.get("q", "").strip()
    if query:
        logs = logs.filter(
            Q(user__username__icontains=query)
            | Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(action__icontains=query)
            | Q(description__icontains=query)
            | Q(ip_address__icontains=query)
        )

    # Date range filtering
    start_date = request.GET.get("start")
    end_date = request.GET.get("end")
    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            logs = logs.filter(timestamp__date__gte=start)
        except ValueError:
            pass
    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            logs = logs.filter(timestamp__date__lte=end)
        except ValueError:
            pass

    # Build type-ahead suggestions from the currently filtered log data
    action_suggestions = logs.values_list("action", flat=True).distinct()
    user_suggestions = logs.values_list("user__username", flat=True).distinct()
    suggestions = sorted(
        set(
            filter(
                None,
                list(action_suggestions) + list(user_suggestions),
            )
        )
    )

    logs = logs.order_by("-timestamp")
    context = {
        "logs": logs,
        "q": query,
        "start": start_date,
        "end": end_date,
        "suggestions": suggestions,
    }
    return render(request, "core/admin_history.html", context)


@login_required
@admin_required
def admin_history_detail(request, pk):
    """Detailed view of a single activity log entry."""
    log = get_object_or_404(ActivityLog, pk=pk)
    return render(request, 'core/admin_history_detail.html', {'log': log})

# ======================== API Endpoints & User Dashboard ========================

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET

@login_required
def api_auth_me(request):
    user = request.user
    role = getattr(getattr(user, "profile", None), "role", None)
    if not role:
        role = "faculty" if user.is_staff else "student"
    initials = "".join([x[0] for x in user.get_full_name().split()]) or user.username[:2].upper()
    return JsonResponse(
        {
            "role": role,
            "name": user.get_full_name(),
            "subtitle": "",
            "initials": initials,
        }
    )

@login_required
def api_faculty_overview(request):
    stats = [
        {
            "label": "Pending Approvals",
            "value": 5,
            "subtitle": "Awaiting",
            "icon": "clock",
            "color": "blue",
        },
        {
            "label": "Events Conducted",
            "value": 3,
            "subtitle": "This Semester",
            "icon": "calendar",
            "color": "green",
        },
    ]
    return JsonResponse(stats, safe=False)


@login_required
def api_faculty_events(request):
    events = [
        {"title": "Orientation", "date": "2024-07-10", "status": "approved"},
        {"title": "Workshop", "date": "2024-08-02", "status": "pending"},
    ]
    return JsonResponse(events, safe=False)


@login_required
def api_faculty_students(request):
    students = [
        {"name": "Alice", "progress": 80},
        {"name": "Bob", "progress": 65},
    ]
    return JsonResponse(students, safe=False)


@login_required
def api_student_overview(request):
    data = {
        "stats": [
            {
                "label": "Events Attended",
                "value": 4,
                "subtitle": "This Year",
                "icon": "calendar",
                "color": "purple",
            }
        ],
        "attributes": [
            {"label": "Leadership", "level": 3},
            {"label": "Communication", "level": 4},
        ],
        "remarks": [
            "Great participation in events",
            "Needs improvement in assignments",
        ],
    }
    return JsonResponse(data)


@login_required
def api_student_events(request):
    data = {
        "participated": [
            {"title": "Orientation", "date": "2024-07-10"},
            {"title": "Workshop", "date": "2024-08-05"},
        ],
        "upcoming": [
            {"title": "Seminar", "date": "2024-09-20"},
        ],
    }
    return JsonResponse(data)


@login_required
def api_student_achievements(request):
    data = {
        "stats": {"total": 5, "this_year": 2},
        "achievements": [
            {"title": "Hackathon Winner", "year": 2024},
            {"title": "Top Speaker", "year": 2023},
        ],
        "peers": [
            {"name": "Jane", "achievement": "Sports Captain"},
            {"name": "Tom", "achievement": "Debate Winner"},
        ],
    }
    return JsonResponse(data)

@login_required
def user_dashboard(request):
    """Render the simplified user dashboard with calendar events.

    Events shown include all approved events that have any associated date.
    """

    user = request.user

    events = (
        EventProposal.objects.filter(status=EventProposal.Status.APPROVED)
        .filter(
            Q(event_datetime__isnull=False)
            | Q(event_start_date__isnull=False)
            | Q(event_end_date__isnull=False)
        )
        .distinct()
    )

    calendar_events = []
    for e in events:
        if e.event_datetime:
            calendar_events.append(
                {
                    "id": e.id,
                    "title": e.event_title,
                    "date": e.event_datetime.date().isoformat(),
                    "datetime": e.event_datetime.isoformat(),
                    "venue": e.venue or "",
                }
            )
        elif e.event_start_date or e.event_end_date:
            start = e.event_start_date or e.event_end_date
            end = e.event_end_date or e.event_start_date
            calendar_events.append(
                {
                    "id": e.id,
                    "title": e.event_title,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "venue": e.venue or "",
                }
            )

    show_settings_tab = False
    try:
        show_settings_tab = user.popso_assignments.filter(is_active=True).exists()
    except Exception:
        pass

    return render(
        request,
        "core/user_dashboard.html",
        {"calendar_events": calendar_events, "show_settings_tab": show_settings_tab},
    )

# ─────────────────────────────────────────────────────────────
#  Dashboard Enhancement APIs
# ─────────────────────────────────────────────────────────────
@login_required
@require_GET
def api_dashboard_places(request):
    """Return places/venues for event/meeting creation."""
    # Get unique venues from existing events
    venues = EventProposal.objects.filter(
        venue__isnull=False
    ).exclude(venue='').values_list('venue', flat=True).distinct()
    
    places = [
        {"id": f"venue_{i}", "name": venue} 
        for i, venue in enumerate(venues, 1)
    ]
    
    # Add some common places if database is empty
    if not places:
        places = [
            {"id": "conf_room_1", "name": "Conference Room 1"},
            {"id": "auditorium", "name": "Main Auditorium"},
            {"id": "seminar_hall", "name": "Seminar Hall"},
            {"id": "lab_1", "name": "Computer Lab 1"},
            {"id": "classroom_101", "name": "Classroom 101"},
        ]
    
    return JsonResponse({"places": places})

@login_required
@require_GET
def api_dashboard_people(request):
    """Return people for meeting invitations."""
    org_id = request.GET.get('org_id')
    user = request.user
    
    people = []
    
    # Get users from same organizations as current user
    user_orgs = user.role_assignments.filter(
        organization__isnull=False
    ).values_list('organization_id', flat=True)
    
    if org_id:
        # Filter by specific organization
        try:
            org_id = int(org_id)
            if org_id in user_orgs:
                users = User.objects.filter(
                    role_assignments__organization_id=org_id
                ).exclude(id=user.id).distinct()
            else:
                users = User.objects.none()
        except (ValueError, TypeError):
            users = User.objects.none()
    else:
        # All users from user's organizations
        users = User.objects.filter(
            role_assignments__organization_id__in=user_orgs
        ).exclude(id=user.id).distinct()
    
    people = [
        {
            "id": u.id,
            "name": u.get_full_name() or u.username,
            "email": u.email,
            "role": getattr(u.profile, 'role', 'user') if hasattr(u, 'profile') else 'user'
        }
        for u in users[:50]  # Limit to 50 for performance
    ]
    
    return JsonResponse({"people": people})

@login_required
@require_GET
def api_user_proposals(request):
    """Return user's proposals for status tracking."""
    proposals = EventProposal.objects.filter(
        submitted_by=request.user
    ).order_by('-created_at')[:50]

    # Deduplicate by title (case-insensitive)
    seen_titles = set()
    proposal_data = []
    for p in proposals:
        title = (p.event_title or "").strip()
        key = title.lower()
        if key in seen_titles:
            continue
        seen_titles.add(key)
        proposal_data.append({
            "id": p.id,
            "title": title or f"Proposal #{p.id}",
            "status": p.status,
            "status_display": p.get_status_display(),
            "created_at": p.created_at.isoformat(),
            # Link to EMT proposal status detail page
            "view_url": reverse('emt:proposal_status_detail', kwargs={'proposal_id': p.id})
        })

    return JsonResponse({"proposals": proposal_data})


@login_required
@require_GET
def api_student_performance_data(request):
    """API endpoint to fetch student performance data"""
    user = request.user
    
    # Get user's organization assignments
    user_orgs = RoleAssignment.objects.filter(user=user).values_list('organization', flat=True)
    
    # Filter events based on user's organizations
    events = EventProposal.objects.filter(
        organization__in=user_orgs,
        status='approved'
    )
    
    total_events = events.count()
    
    # Check if user has a student profile and count participated events
    participated_events = 0
    if hasattr(user, 'student_profile'):
        participated_events = user.student_profile.events.filter(
            organization__in=user_orgs,
            status='approved'
        ).count()
    
    participation_rate = (participated_events / total_events * 100) if total_events > 0 else 0
    
    # Get recent activities
    recent_activities = []
    if hasattr(user, 'student_profile'):
        recent_events = user.student_profile.events.filter(
            organization__in=user_orgs
        ).order_by('-created_at')[:5]
        for activity in recent_events:
            recent_activities.append({
                'title': activity.event_title,
                'date': activity.created_at.strftime('%Y-%m-%d'),
                'type': 'Event Participation'
            })
    
    return JsonResponse({
        'total_events': total_events,
        'participated_events': participated_events,
        'participation_rate': round(participation_rate, 1),
        'recent_activities': recent_activities
    })


@login_required
@require_GET
def api_student_contributions(request):
    """API endpoint to fetch yearly contribution data for GitHub-style graph.

    Includes any EventProposal the user is associated with as:
    - participant (via Student profile),
    - proposer (submitted_by), or
    - faculty-in-charge (M2M).
    """
    user = request.user
    from django.utils import timezone
    from datetime import timedelta

    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=365)

    # Unified queryset across roles using EventProposal with OR conditions
    assoc = (
        models.Q(submitted_by=user) |
        models.Q(faculty_incharges=user) |
        models.Q(participants__user=user)
    )
    # Prefer actual event date (event_datetime/event_start_date); fallback to created_at
    date_window = (
        models.Q(event_datetime__date__gte=start_date, event_datetime__date__lte=end_date)
        | models.Q(event_start_date__gte=start_date, event_start_date__lte=end_date)
        | models.Q(created_at__date__gte=start_date, created_at__date__lte=end_date)
    )
    qs = EventProposal.objects.filter(assoc & date_window).distinct()

    # Compute a date expression choosing event date first
    date_expr = models.Case(
        models.When(event_datetime__isnull=False, then=TruncDate('event_datetime')),
        models.When(event_start_date__isnull=False, then=models.F('event_start_date')),
        default=TruncDate('created_at'),
        output_field=models.DateField(),
    )

    # Aggregate counts per chosen date
    contributions_map = {}
    daily = qs.annotate(date=date_expr).values('date').annotate(count=models.Count('id'))
    for row in daily:
        date_obj = row["date"]
        date_str = date_obj.strftime("%Y-%m-%d") if hasattr(date_obj, "strftime") else str(date_obj)
        contributions_map[date_str] = row["count"]

    # Build full year series with intensity levels 0-4
    series = []
    cur = start_date
    while cur <= end_date:
        dstr = cur.strftime("%Y-%m-%d")
        cnt = int(contributions_map.get(dstr, 0))
        level = 0
        if cnt == 0:
            level = 0
        elif cnt <= 1:
            level = 1
        elif cnt <= 3:
            level = 2
        elif cnt <= 5:
            level = 3
        else:
            level = 4
        series.append({"date": dstr, "count": cnt, "level": level})
        cur += timedelta(days=1)

    return JsonResponse({"contributions": series})


@login_required
@require_GET
def api_user_events_data(request):
    """Return ONLY events proposed by the current user (for tracking)."""
    user = request.user

    # Only include events created/proposed by the logged-in user
    events = EventProposal.objects.filter(submitted_by=user).order_by('-created_at')[:10]

    events_data = []
    for event in events:
        desc = getattr(event, 'description', '') or ''
        events_data.append({
            'id': event.id,
            'title': event.event_title,
            'description': desc[:100] + '...' if len(desc) > 100 else desc,
            'status': event.status,
            'created_at': event.created_at.strftime('%Y-%m-%d %H:%M'),
            'organization': event.organization.name if event.organization else 'N/A'
        })
    
    return JsonResponse({'events': events_data})

@login_required
@require_GET
def api_student_performance_data(request):
    """Return student performance data based on organization and participation."""
    user = request.user
    org_id = request.GET.get('org_id')
    
    # Get user's organizations
    user_orgs = user.role_assignments.filter(
        organization__isnull=False
    ).values_list('organization_id', flat=True)
    
    if org_id:
        try:
            org_id = int(org_id)
            if org_id not in user_orgs:
                return JsonResponse({"error": "Access denied"}, status=403)
            filter_orgs = [org_id]
        except (ValueError, TypeError):
            filter_orgs = list(user_orgs)
    else:
        filter_orgs = list(user_orgs)
    
    # Get events user participated in or organized
    organized_events = EventProposal.objects.filter(
        submitted_by=user,
        organization_id__in=filter_orgs,
        status__in=['approved', 'finalized']
    ).count()
    
    participated_events = EventProposal.objects.filter(
        organization_id__in=filter_orgs,
        status__in=['approved', 'finalized']
    ).exclude(submitted_by=user).count()  # Simplified - in real app you'd have participants table
    
    # Calculate performance metrics
    total_events = organized_events + participated_events
    leadership_score = (organized_events / max(total_events, 1)) * 100
    participation_score = (participated_events / max(total_events, 1)) * 100
    
    # Performance categories
    if total_events >= 10:
        overall = "Excellent"
    elif total_events >= 5:
        overall = "Good"
    elif total_events >= 2:
        overall = "Average"
    else:
        overall = "Needs Improvement"
    
    labels = ["Leadership", "Participation", "Communication", "Teamwork"]
    percentages_raw = [
        min(leadership_score, 100),
        min(participation_score, 100),
        min(75 + (total_events * 2), 100),  # Communication based on activity
        min(65 + (total_events * 3), 100)   # Teamwork based on activity
    ]
    # Round to 1 decimal place as requested
    percentages = [round(v, 1) for v in percentages_raw]
    
    return JsonResponse({
        "labels": labels,
        "percentages": percentages,
        "total_events": total_events,
        "participated_events": participated_events,
        "participation_rate": round(participation_score, 1),
        "total_events": total_events,
        "organized_events": organized_events,
        "participated_events": participated_events,
        "overall_performance": overall
    })

# NOTE: duplicate api_student_contributions removed; see unified implementation above

# Note: Removed duplicate api_user_events_data with different payload shape.

# ─────────────────────────────────────────────────────────────
#  Calendar API (common for student/faculty dashboards)
# ─────────────────────────────────────────────────────────────
@login_required
@require_GET
def api_calendar_events(request):
    """
    Return calendar items based on dropdown category.
    category: one of [all, public, private, faculty]
    - all/public: approved/finalized EventProposals (past + future)
    - private: only returns a marker that clicking opens Google Calendar (no backend tasks stored)
    - faculty: FacultyMeeting within user's organizations (faculty only)
    """
    user = request.user
    category = request.GET.get('category', 'all').lower()

    items = []
    now = timezone.now()

    def build_view_url(item_id):
        """
        Build a details URL per role:
        - Admin: EMT proposal status detail.
        - Non-admin: Old user-facing event details page.
        Fallbacks retained for robustness.
        """
        # Admins should land on EMT proposal status detail
        if request.user.is_superuser:
            try:
                return reverse('emt:proposal_status_detail', kwargs={'proposal_id': item_id})
            except Exception:
                pass

        # Non-admins: prefer the legacy/user-facing event details
        try:
            return reverse('student_event_details', kwargs={'proposal_id': item_id})
        except Exception:
            pass

        # Generic fallback to core proposal detail
        try:
            return reverse('proposal_detail', kwargs={'proposal_id': item_id})
        except Exception:
            pass

        # Last resort legacy path
        return f"/event/{item_id}/details/"

    # public/approved events + user-owned events
    if category in ("all", "public"):
        base_q = Q(event_datetime__isnull=False) | Q(event_start_date__isnull=False) | Q(event_end_date__isnull=False)
        status_q = Q(status__in=[EventProposal.Status.APPROVED, EventProposal.Status.FINALIZED])
        # Admin sees all scheduled events regardless of status
        if user.is_superuser:
            visibility_q = base_q
        else:
            # Include approved/finalized for everyone, plus events owned by the user (submitted_by or faculty_incharges)
            owned_q = Q(submitted_by=user) | Q(faculty_incharges=user)
            visibility_q = base_q & (status_q | owned_q)
        events = EventProposal.objects.filter(visibility_q).distinct()

        for e in events:
            # Unify event data structure for dashboard and CDL
            base_data = {
                "id": e.id,
                "title": e.event_title,
                "status": e.status,
                "status_display": getattr(e, 'get_status_display', lambda: e.status)(),
                "description": getattr(e, 'description', ''),
                "organization": e.organization.name if getattr(e, 'organization', None) else None,
                "submitted_by": e.submitted_by.get_full_name() if getattr(e, 'submitted_by', None) else None,
                "venue": e.venue or "",
                "type": "public",
                "view_url": build_view_url(e.id),
                "gcal_url": build_gcal_link(e),
                "event_start_date": e.event_start_date.isoformat() if e.event_start_date else None,
                "event_end_date": e.event_end_date.isoformat() if e.event_end_date else None,
            }
            # Single-date event with datetime
            if e.event_datetime:
                dt = e.event_datetime
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt, timezone.get_current_timezone())
                dt_local = timezone.localtime(dt)
                event = base_data.copy()
                event.update({
                    "date": dt_local.date().isoformat(),
                    "datetime": dt_local.isoformat(),
                    "past": dt_local < now,
                })
                items.append(event)
                continue

            # All-day or multi-day range: only put dot on start date
            start_date = e.event_start_date or e.event_end_date
            if not start_date:
                continue
            dt_local = timezone.make_aware(datetime.combine(start_date, datetime.min.time()), timezone.get_current_timezone())
            event = base_data.copy()
            event.update({
                "date": start_date.isoformat(),
                "datetime": dt_local.isoformat(),
                "past": dt_local < now,
            })
            items.append(event)

    # CDL Support only
    if category == "cdl":
        base_q = Q(event_datetime__isnull=False) | Q(event_start_date__isnull=False) | Q(event_end_date__isnull=False)
        status_q = Q(status__in=[EventProposal.Status.APPROVED, EventProposal.Status.FINALIZED])
        try:
            needs_cdl = Q(cdl_support__needs_support=True)
        except Exception:
            needs_cdl = Q()
        if user.is_superuser:
            visibility_q = base_q & needs_cdl
        else:
            owned_q = Q(submitted_by=user) | Q(faculty_incharges=user)
            visibility_q = base_q & needs_cdl & (status_q | owned_q)
        events = EventProposal.objects.filter(visibility_q).distinct()

        for e in events:
            if e.event_datetime:
                dt = e.event_datetime
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt, timezone.get_current_timezone())
                dt_local = timezone.localtime(dt)
                items.append({
                    "id": e.id,
                    "title": e.event_title,
                    "date": dt_local.date().isoformat(),
                    "datetime": dt_local.isoformat(),
                    "venue": e.venue or "",
                    "type": "cdl",
                    "past": dt_local < now,
                    "view_url": build_view_url(e.id),
                    "gcal_url": build_gcal_link(e),
                })
                continue
            start_date = e.event_start_date or e.event_end_date
            end_date = e.event_end_date or e.event_start_date
            if not start_date:
                continue
            if not end_date:
                end_date = start_date
            cur = start_date
            while cur <= end_date:
                dt_local = timezone.make_aware(datetime.combine(cur, datetime.min.time()), timezone.get_current_timezone())
                items.append({
                    "id": e.id,
                    "title": e.event_title,
                    "date": cur.isoformat(),
                    "datetime": dt_local.isoformat(),
                    "venue": e.venue or "",
                    "type": "cdl",
                    "past": dt_local < now,
                    "view_url": build_view_url(e.id),
                    "gcal_url": build_gcal_link(e),
                })
                cur += timedelta(days=1)

    # private category: no stored tasks, front-end will open GCal on date click
    if category == "private":
        return JsonResponse({"items": items, "category": category, "private": True})

    # faculty meetings
    if category == "faculty":
        # must be faculty by role assignment
        has_faculty_role = False
        try:
            has_faculty_role = any(
                (ra.role and ra.role.name.lower() == 'faculty') for ra in user.role_assignments.select_related('role')
            )
        except Exception:
            has_faculty_role = False
        if not has_faculty_role and not user.is_superuser:
            return JsonResponse({"items": [], "category": category})

        org_ids = list(
            user.role_assignments.filter(organization__isnull=False).values_list('organization_id', flat=True)
        )
        meetings = FacultyMeeting.objects.filter(organization_id__in=org_ids)
        for m in meetings:
            items.append({
                "id": f"m{m.id}",
                "title": m.title,
                "date": m.scheduled_at.date().isoformat(),
                "datetime": timezone.localtime(m.scheduled_at).isoformat(),
                "venue": getattr(m, 'venue', '') or '',
                "type": "faculty",
                "past": m.scheduled_at < now,
                "view_url": "",
                "gcal_url": gcal_quick_add_link(m.title, m.scheduled_at, None, m.description),
            })

    return JsonResponse({"items": items, "category": category})


def build_gcal_link(e: EventProposal) -> str:
    """Create an Add to Google Calendar URL for an EventProposal."""
    try:
        import urllib.parse as ul
    except Exception:
        return ""
    title = e.event_title or "Event"
    details = []
    if e.organization:
        details.append(f"Organization: {e.organization.name}")
    if e.venue:
        details.append(f"Venue: {e.venue}")
    text = ul.quote(title)
    desc = ul.quote("\n".join(details))
    location = ul.quote(e.venue or "")
    # compute start/end
    if e.event_datetime:
        start = timezone.localtime(e.event_datetime)
        end = start + timedelta(hours=1)
    else:
        start_date = e.event_start_date or e.event_end_date or timezone.localdate()
        start = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.get_current_timezone())
        end = start + timedelta(hours=1)
    def fmt(d):
        return d.strftime('%Y%m%dT%H%M%S')
    dates = f"{fmt(start)}/{fmt(end)}"
    return (
        "https://www.google.com/calendar/render?action=TEMPLATE"
        f"&text={text}&dates={dates}&details={desc}&location={location}&sf=true&output=xml"
    )


def gcal_quick_add_link(title: str, start_dt, end_dt=None, description: str = "") -> str:
    try:
        import urllib.parse as ul
    except Exception:
        return ""
    text = ul.quote(title)
    if end_dt is None:
        end_dt = start_dt + timedelta(hours=1)
    def fmt(d):
        return timezone.localtime(d).strftime('%Y%m%dT%H%M%S')
    dates = f"{fmt(start_dt)}/{fmt(end_dt)}"
    details = ul.quote(description or "")
    return (
        "https://www.google.com/calendar/render?action=TEMPLATE"
        f"&text={text}&dates={dates}&details={details}&sf=true&output=xml"
    )


@login_required
@require_POST
def api_create_faculty_meeting(request):
    """Create a faculty meeting within user's organization. Faculty only."""
    user = request.user
    has_faculty_role = any(
        (ra.role and ra.role.name.lower() == 'faculty') for ra in user.role_assignments.select_related('role')
    )

    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else request.POST
    except Exception:
        payload = request.POST
    
    title = (payload.get('title') or '').strip() or 'Meeting'
    description = (payload.get('description') or '').strip()
    org_id = payload.get('organization_id') or payload.get('org_id')
    when = payload.get('scheduled_at') or payload.get('datetime')
    place = (payload.get('place') or '').strip()
    participants = payload.get('participants', [])
    
    if not org_id or not when:
        return JsonResponse({"success": False, "error": "organization_id and scheduled_at are required"}, status=400)
    # Allow any member of the organization (not just faculty) to create meetings, per requirement
    try:
        org_id_int = int(org_id)
    except Exception:
        return JsonResponse({"success": False, "error": "Invalid organization_id"}, status=400)
    user_org_ids = set(
        user.role_assignments.filter(organization__isnull=False).values_list('organization_id', flat=True)
    )
    if not (has_faculty_role or user.is_superuser or org_id_int in user_org_ids):
        return JsonResponse({"success": False, "error": "Not allowed"}, status=403)
    
    try:
        from django.utils.dateparse import parse_datetime
        dt = parse_datetime(when)
        if dt is None:
            return JsonResponse({"success": False, "error": "Invalid datetime"}, status=400)
        
        meeting = FacultyMeeting.objects.create(
            title=title,
            description=f"{description}\nVenue: {place}\nParticipants: {', '.join(participants) if participants else 'All faculty'}",
            organization_id=org_id_int,
            scheduled_at=dt,
            created_by=user,
        )
        return JsonResponse({"success": True, "id": meeting.id})
    except Exception as ex:
        return JsonResponse({"success": False, "error": str(ex)}, status=500)

@login_required
@require_GET
def api_global_search(request):
    """
    Global search API endpoint for the Central Command Center.
    Searches across Students, Event Proposals, Reports, Organizations, and Users.
    """
    from django.db.models import Q
    from django.contrib.auth.models import User
    import json
    query = request.GET.get('q', '').strip()
    if len(query) < 1:
        return JsonResponse({
            'success': True,
            'results': {
                'students': [],
                'proposals': [],
                'reports': [],
                'organizations': [],
                'users': []
            }
        })
    try:
        results = {'students': [], 'proposals': [], 'reports': [], 'organizations': [], 'users': []}
        try:
            from transcript.models import Student
            students = Student.objects.filter(
                Q(name__icontains=query) |
                Q(roll_no__icontains=query)
            ).select_related('school', 'course')[:5]
            results['students'] = [{
                'id': student.id,
                'name': student.name,
                'roll_no': student.roll_no,
                'school': student.school.name if student.school else 'N/A',
                'course': student.course.name if student.course else 'N/A',
                'url': f'/transcript/{student.roll_no}/'
            } for student in students]
        except ImportError:
            student_users = User.objects.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(username__icontains=query)
            ).filter(
                profile__isnull=False
            )[:5]
            results['students'] = [{
                'id': user.id,
                'name': f"{user.first_name} {user.last_name}".strip() or user.username,
                'roll_no': user.username,
                'school': 'N/A',
                'course': 'N/A',
                'url': f'/core-admin/users/{user.id}/'
            } for user in student_users]
        try:
            from emt.models import EventProposal
            proposals = EventProposal.objects.filter(
                Q(event_title__icontains=query) |
                Q(submitted_by_first_name_icontains=query) |
                Q(submitted_by_last_name_icontains=query) |
                Q(organization_name_icontains=query) |
                Q(event_focus_type__icontains=query)
            ).select_related('submitted_by', 'organization').order_by('-event_datetime')[:5]
            if query.lower() == 'iqac':
                proposals = EventProposal.objects.filter(
                    Q(organization_name_icontains='iqac') |
                    Q(event_focus_type__icontains='iqac')
                ).select_related('submitted_by', 'organization').order_by('-event_datetime')[:5]
            results['proposals'] = [{
                'id': proposal.id,
                'title': proposal.event_title,
                'faculty': proposal.submitted_by.get_full_name() if proposal.submitted_by else 'N/A',
                'organization': proposal.organization.name if proposal.organization else 'N/A',
                'status': getattr(proposal, 'status', 'Unknown'),
                'date': proposal.event_datetime.strftime('%Y-%m-%d') if proposal.event_datetime else 'N/A',
                'url': f'/core-admin/event-proposals/{proposal.id}/'
            } for proposal in proposals]
        except (ImportError, AttributeError):
            results['proposals'] = []
        try:
            from core.models import Report
            reports = Report.objects.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(organization_name_icontains=query)
            ).order_by('-created_at')[:5]
            if query.lower() == 'iqac':
                reports = Report.objects.filter(
                    Q(report_type__iexact='iqac') |
                    Q(title__icontains='iqac') |
                    Q(organization_name_icontains='iqac')
                ).order_by('-created_at')[:5]
            results['reports'] = [{
                'id': report.id,
                'title': report.title,
                'type': getattr(report, 'report_type', 'Report'),
                'organization': report.organization.name if report.organization else 'N/A',
                'date': report.created_at.strftime('%Y-%m-%d'),
                'url': f'/core-admin/reports/{report.id}/'
            } for report in reports]
        except (ImportError, AttributeError):
            results['reports'] = []

        # Organizations
        organizations = Organization.objects.filter(
            Q(name__icontains=query) | Q(org_type__name__icontains=query)
        ).select_related('org_type')[:5]
        results['organizations'] = [
            {
                'id': org.id,
                'name': org.name,
                'org_type': org.org_type.name if org.org_type else 'N/A',
                'url': f'/core-admin/user-roles/{org.id}/'
            }
            for org in organizations
        ]
        if request.user.is_superuser or hasattr(request.user, 'profile'):
            users = User.objects.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(username__icontains=query) |
                Q(email__icontains=query)
            ).exclude(id=request.user.id)[:5]
            results['users'] = [{
                'id': user.id,
                'name': f"{user.first_name} {user.last_name}".strip() or user.username,
                'email': user.email,
                'role': getattr(user.profile, 'role', 'User') if hasattr(user, 'profile') else 'User',
                'last_login': user.last_login.strftime('%Y-%m-%d') if user.last_login else 'Never',
                'url': f'/core-admin/users/{user.id}/edit/'
            } for user in users]
        return JsonResponse({'success': True, 'results': results, 'query': query})
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'results': {
                'students': [],
                'proposals': [],
                'reports': [],
                'organizations': [],
                'users': []
            }
        }, status=500)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard_api(request):
    """
    API endpoint for dashboard analytics - useful for real-time updates.
    """
    from django.contrib.auth.models import User
    stats = {
        'students': User.objects.filter(
            role_assignments__role__name__icontains='student',
            is_active=True,
            last_login__isnull=False,
        ).distinct().count(),
        'faculties': User.objects.filter(
            role_assignments__role__name__icontains='faculty',
            is_active=True,
            last_login__isnull=False,
        ).distinct().count(),
        'hods': User.objects.filter(
            role_assignments__role__name__icontains='hod',
            is_active=True,
            last_login__isnull=False,
        ).distinct().count(),
        'centers': Organization.objects.filter(is_active=True).count(),
        'total_users': User.objects.filter(is_active=True, last_login__isnull=False).count(),
        'total_proposals': EventProposal.objects.count(),
        'pending_proposals': EventProposal.objects.filter(
            status__in=['submitted', 'under_review']
        ).count(),
    }
    return JsonResponse({'success': True, 'stats': stats})


#======================== Data Export and Filter View =======================
# views.py - Add these views to your core app views
# views.py (merged full version with new org-type / org-name filters and expanded search)
# core/views.py  — Part 1
# Dynamic search / filter / export for admin
# ========================
import json
import csv
from io import BytesIO
from datetime import datetime, timedelta

from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone

# Optional Excel writer
try:
    import xlsxwriter
except Exception:
    xlsxwriter = None

# -------------------------
# Import models (core + emt)
# -------------------------
# core app models
from .models import (
    Organization, OrganizationType, OrganizationRole, RoleAssignment,
    Profile, Report, Program, ProgramOutcome, ProgramSpecificOutcome,
    ApprovalFlowTemplate
)

# emt app models — use canonical names used in your repo
from emt.models import (
    EventProposal as EMTEventProposal,   # EMT's main EventProposal model
    EventReport as EMTEventReport,
    ApprovalStep, Student, MediaRequest, CDLSupport
)

# If you also have a core EventProposal model (some setups do), try to import it safely:
try:
    from .models import EventProposal as CoreEventProposal  # optional
    HAS_CORE_EVENT = True
except Exception:
    CoreEventProposal = None
    HAS_CORE_EVENT = False

# -------------------------
# Access control helper
# -------------------------


# -------------------------
# Constants & scope names
# -------------------------
SCOPE_EVENTS = "events"
SCOPE_REPORTS = "reports"
SCOPE_USERS = "users"
SCOPE_ORGS = "organizations"

# -------------------------
# Small utility helpers
# -------------------------
def iso(dt):
    """Return ISO string for datetimes/dates; safe for None."""
    if dt is None:
        return None
    if hasattr(dt, 'isoformat'):
        return dt.isoformat()
    return str(dt)


def _compute_date_range(range_key):
    """Return (start_date, end_date) for common range keys. Both are date objects."""
    if not range_key:
        return (None, None)
    now = timezone.now().date()
    if range_key in ('7_days', '7'):
        return (now - timedelta(days=7), now)
    if range_key in ('30_days', '30'):
        return (now - timedelta(days=30), now)
    if range_key == 'this_month':
        return (now.replace(day=1), now)
    if range_key == 'this_year':
        return (now.replace(month=1, day=1), now)
    if range_key == 'academic_year':
        # default academic year starts June 1; adjust as needed
        if now.month >= 6:
            return (now.replace(month=6, day=1), now)
        else:
            return (now.replace(year=now.year-1, month=6, day=1), now)
    # allow custom 'YYYY-MM-DD__YYYY-MM-DD'
    if '__' in str(range_key):
        try:
            a, b = range_key.split('__', 1)
            start = datetime.strptime(a, '%Y-%m-%d').date()
            end = datetime.strptime(b, '%Y-%m-%d').date()
            return (start, end)
        except Exception:
            return (None, None)
    return (None, None)


# -------------------------
# Serializers (dict representations)
# -------------------------
def _emt_event_to_dict(ev: EMTEventProposal):
    org = getattr(ev, 'organization', None)
    
    submitted_by_name = None
    if getattr(ev, 'submitted_by', None):
        user = ev.submitted_by
        # Attempt to get the user's full name. If it's an empty string,
        # fall back to the username.
        full_name = user.get_full_name().strip()
        if full_name:
            submitted_by_name = full_name
        else:
            submitted_by_name = user.username
            
    return {
        'title': getattr(ev, 'event_title', '') or getattr(ev, 'title', '') or f'Event #{ev.id}',
        'status': getattr(ev, 'status', None) or getattr(ev, 'get_status_display', lambda: '')(),
        'submitted_by': submitted_by_name,
        'organization': org.name if org else None,
        'event_start_date': iso(getattr(ev, 'event_start_date', None))
    }

def _core_event_to_dict(ev):
    """If you have a core EventProposal model (optional), format it similarly."""
    org = getattr(ev, 'organization', None)
    return {
        'title': getattr(ev, 'event_title', None) or getattr(ev, 'title', None) or f'Event #{ev.id}',
        'status': getattr(ev, 'status', None),
        'submitted_by': ev.submitted_by.get_full_name() if getattr(ev, 'submitted_by', None) else None,
        'organization': org.name if org else None
    }


def _user_to_dict(user: User):
    # try to get first role assignment as an indicator
    org = None
    if hasattr(user, 'role_assignments'):
        ra = user.role_assignments.first()
        if ra and getattr(ra, 'organization', None):
            org = ra.organization
    profile = getattr(user, 'profile', None)
    return {
        'username': user.username,
        'full_name': user.get_full_name(),
        'email': user.email,
        'role': getattr(profile, 'role', None) if profile else None,
        'organization': org.name if org else None,
        'date_joined': iso(user.date_joined)
    }


def _report_to_dict(r: Report):
    org = getattr(r, 'organization', None)
    # If r has get_report_type_display or get_status_display, you can use them in the frontend
    return {
        'title': getattr(r, 'title', ''),
        'report_type': getattr(r, 'report_type', None),
        'status': getattr(r, 'status', None),
        'submitted_by': r.submitted_by.get_full_name() if getattr(r, 'submitted_by', None) else None,
        'organization': org.name if org else None,
        'created_at': iso(getattr(r, 'created_at', None))
    }


def _org_to_dict(o: Organization):
    return {
        'name': o.name,
        'org_type': o.org_type.name if getattr(o, 'org_type', None) else None,
        'org_type_id': o.org_type.id if getattr(o, 'org_type', None) else None,
        'is_active': getattr(o, 'is_active', getattr(o, 'active', None))
    }


# -------------------------
# Query builders per category
# -------------------------
def build_event_queryset(q=None, filters=None):
    """
    Build queryset for events.
    Will include EMT events (EMTEventProposal) always.
    If CoreEventProposal exists and client requests it (via filters), we can include it.
    For simplicity the unified search endpoint will merge results from both if requested.
    """
    qs = EMTEventProposal.objects.select_related('organization', 'submitted_by').all()

    if q:
        s = q.strip()
        qs = qs.filter(
            Q(event_title__icontains=s) |
            Q(description__icontains=s) |
            Q(submitted_by__first_name__icontains=s) |
            Q(submitted_by__last_name__icontains=s) |
            Q(organization__name__icontains=s)
        )

    if not filters:
        return qs

    for f in filters:
        t = f.get('type')
        v = f.get('value')
        if t == 'organization_type':
            try:
                ot = int(v)
                qs = qs.filter(organization__org_type_id=ot)
            except Exception:
                qs = qs
        elif t == 'organization':
            try:
                oid = int(v)
                qs = qs.filter(organization_id=oid)
            except Exception:
                qs = qs.filter(organization__name__icontains=str(v))
        elif t == 'status':
            # If you want to treat 'approved' as 'finalized' on frontend, handle there.
            qs = qs.filter(status__iexact=v)
        elif t == 'flag':
            # v expected to be 'is_big_event' or 'needs_finance_approval'
            if v in ('is_big_event', 'needs_finance_approval'):
                qs = qs.filter(**{v: True})
        elif t == 'date_range':
            start, end = _compute_date_range(v)
            if start and end:
                # prefer event_start_date when available
                if hasattr(EMTEventProposal, 'event_start_date'):
                    qs = qs.filter(event_start_date__gte=start, event_start_date__lte=end)
                else:
                    # fallback to created_at or date_submitted
                    if hasattr(EMTEventProposal, 'created_at'):
                        qs = qs.filter(created_at__date__gte=start, created_at__date__lte=end)
        # add more event-like filters as needed

    return qs


from django.db.models import Q

def build_user_queryset(q=None, filters=None):
    qs = User.objects.select_related('profile').all()
    
    if q:
        s = q.strip()
        qs = qs.filter(
            Q(username__icontains=s) |
            Q(first_name__icontains=s) |
            Q(last_name__icontains=s) |
            Q(email__icontains=s)
        )

    if not filters:
        return qs

    for f in filters:
        t = f.get('type')
        v = f.get('value')

        if t == 'organization_type':
            try:
                ot = int(v)
                qs = qs.filter(role_assignments__organization__org_type_id=ot).distinct()
            except Exception:
                pass

        elif t == 'organization':
            try:
                oid = int(v)
                qs = qs.filter(role_assignments__organization_id=oid).distinct()
            except Exception:
                qs = qs.filter(role_assignments__organization__name__icontains=str(v)).distinct()

        elif t == 'role' and v:
            # Split by comma, trim spaces
            roles = [r.strip() for r in str(v).split(',') if r.strip()]
            # Build Q objects for case-insensitive match
            role_q = Q()
            for role in roles:
                role_q |= Q(profile__role__iexact=role)
            qs = qs.filter(role_q)

        elif t == 'active':
            if v in (True, 'true', 'True', '1', 1):
                qs = qs.filter(is_active=True)
            else:
                qs = qs.filter(is_active=False)

    return qs


def build_report_queryset(q=None, filters=None):
    qs = Report.objects.select_related('organization', 'submitted_by').all()
    if q:
        s = q.strip()
        qs = qs.filter(
            Q(title__icontains=s) |
            Q(description__icontains=s) |
            Q(organization__name__icontains=s) |
            Q(submitted_by__first_name__icontains=s) |
            Q(submitted_by__last_name__icontains=s)
        )
    if not filters:
        return qs
    for f in filters:
        t = f.get('type')
        v = f.get('value')
        if t == 'organization_type':
            try:
                ot = int(v)
                qs = qs.filter(organization__org_type_id=ot)
            except Exception:
                pass
        elif t == 'organization':
            try:
                oid = int(v)
                qs = qs.filter(organization_id=oid)
            except Exception:
                qs = qs.filter(organization__name__icontains=str(v))
        elif t == 'report_type':
            qs = qs.filter(report_type=v)
        elif t == 'status':
            qs = qs.filter(status=v)
        elif t == 'date_range':
            start, end = _compute_date_range(v)
            if start and end:
                qs = qs.filter(created_at__date__gte=start, created_at__date__lte=end)
    return qs


def build_organization_queryset(q=None, filters=None):
    qs = Organization.objects.select_related('org_type').all()
    if q:
        s = q.strip()
        qs = qs.filter(
            Q(name__icontains=s) |
            Q(org_type__name__icontains=s)
        )
    if not filters:
        return qs
    for f in filters:
        t = f.get('type')
        v = f.get('value')
        if t == 'organization_type':
            try:
                ot = int(v)
                qs = qs.filter(org_type_id=ot)
            except Exception:
                qs = qs.filter(org_type__name__icontains=str(v))
        elif t == 'active':
            if v in (True, 'true', '1', 1):
                qs = qs.filter(is_active=True)
            else:
                qs = qs.filter(is_active=False)
    return qs


# -------------------------
# Dynamic filter endpoints (AJAX)
# -------------------------
@login_required
@user_passes_test(is_admin)
def data_export_filter_view(request):
    """Render the filter/search page template."""
    return render(request, 'core/data_export_filter.html')


@login_required
@user_passes_test(is_admin)
def api_org_types(request):
    """Return active organization types for the filter panel."""
    qs = OrganizationType.objects.all().order_by('name')
    data = [{'id': ot.id, 'name': ot.name, 'is_active': getattr(ot, 'is_active', True)} for ot in qs]
    return JsonResponse(data, safe=False)


@login_required
@user_passes_test(is_admin)
def api_orgs_by_type(request):
    """
    GET param: org_type_id
    Returns organizations under a given org_type (active ones by default).
    """
    ot = request.GET.get('org_type_id')
    if not ot:
        return JsonResponse([], safe=False)
    try:
        otid = int(ot)
        qs = Organization.objects.filter(org_type_id=otid).order_by('name')
        data = [{'id': o.id, 'name': o.name, 'is_active': getattr(o, 'is_active', True)} for o in qs]
        return JsonResponse(data, safe=False)
    except Exception:
        return JsonResponse([], safe=False)
# ========================
# core/views.py  — Part 2
# (continuation of the same file)
# ========================

from django.views.decorators.http import require_http_methods

# -------------------------
# Filter metadata for each category
# -------------------------
@login_required
@user_passes_test(is_admin)
def api_filter_meta(request, category):
    """
    Returns metadata to help the frontend render the dynamic filter UI for the given category.
    category: 'events' | 'users' | 'reports' | 'organizations'
    """
    category = (category or '').lower()
    if category == 'events':
        statuses = []
        # Try to pull statuses from EMTEventProposal.Status if defined (TextChoices)
        try:
            statuses = [{'value': s.value if hasattr(s, 'value') else s[0], 'label': s.label if hasattr(s, 'label') else s[1]} for s in EMTEventProposal.Status]
        except Exception:
            # fallback: attempt to read tuple-based STATUS_CHOICES
            try:
                statuses = [{'value': s[0], 'label': s[1]} for s in EMTEventProposal.STATUS_CHOICES]
            except Exception:
                statuses = []
        return JsonResponse({
            'category': 'events',
            'filters': {
                'organization_types': [{'id': ot.id, 'name': ot.name} for ot in OrganizationType.objects.filter(is_active=True)],
                'statuses': statuses,
                'boolean_flags': ['is_big_event', 'needs_finance_approval'],
                'date_ranges': ['7_days', '30_days', 'this_month', 'this_year', 'academic_year']
            }
        })
    elif category == 'users':
        role_choices = [{'value': r[0], 'label': r[1]} for r in Profile.ROLE_CHOICES]
        return JsonResponse({
            'category': 'users',
            'filters': {
                'organization_types': [{'id': ot.id, 'name': ot.name} for ot in OrganizationType.objects.filter(is_active=True)],
                'roles': role_choices,
                'active_flags': ['active', 'inactive']
            }
        })
    elif category == 'reports':
        report_types = [{'value': r[0], 'label': r[1]} for r in Report.REPORT_TYPE_CHOICES] if hasattr(Report, 'REPORT_TYPE_CHOICES') else []
        status_choices = [{'value': s[0], 'label': s[1]} for s in Report.STATUS_CHOICES] if hasattr(Report, 'STATUS_CHOICES') else []
        return JsonResponse({
            'category': 'reports',
            'filters': {
                'organization_types': [{'id': ot.id, 'name': ot.name} for ot in OrganizationType.objects.filter(is_active=True)],
                'report_types': report_types,
                'statuses': status_choices,
                'date_ranges': ['7_days', '30_days', 'this_month', 'this_year', 'academic_year']
            }
        })
    elif category == 'organizations':
        return JsonResponse({
            'category': 'organizations',
            'filters': {
                'organization_types': [{'id': ot.id, 'name': ot.name} for ot in OrganizationType.objects.all()],
                'active_flags': ['active', 'inactive']
            }
        })
    else:
        return JsonResponse({'error': 'Unknown category'}, status=400)


# -------------------------
# Unified search endpoint
# -------------------------
@csrf_exempt
@login_required
@user_passes_test(is_admin)
def api_search(request):
    """
    Unified search endpoint.
    Accepts POST JSON:
    {
      "category": "events"|"users"|"reports"|"organizations",
      "q": "free text",
      "filters": [{"type":"organization_type","value":3}, ...],
      "page": 1,
      "page_size": 50
    }
    """
    try:
        payload = json.loads(request.body.decode('utf-8') or "{}")
    except Exception:
        payload = {}

    category = (payload.get('category') or request.GET.get('category') or '').lower()
    q = payload.get('q', payload.get('q', '')).strip() if payload.get('q') is not None else request.GET.get('q', '').strip()
    filters = payload.get('filters', []) or []

    page = int(payload.get('page', request.GET.get('page', 1) or 1))

    # Allow selecting 100, 250, 500, 1000 from frontend, default to 100
    page_size = int(payload.get('page_size', request.GET.get('page_size', 1000000) or 1000000))

    # If page_size is 0 or less, load *all* records
    if page_size <= 0:
        page_size = None  # None means no limit

    # Default empty response
    results = []
    total = 0

    if category == 'events':
        qs = build_event_queryset(q=q or None, filters=filters or None).order_by('-created_at')
        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        results = [_emt_event_to_dict(e) for e in qs[start:end]]

        # If caller wanted core events included (rare), they can pass a filter: {"type":"include_core","value":true}
        include_core = any(f.get('type') == 'include_core' and f.get('value') in (True, 'true', 'True', 1, '1') for f in filters)
        if include_core and HAS_CORE_EVENT:
            qs_core = CoreEventProposal.objects.all()
            # apply q and basic filters on core as well (you can expand)
            if q:
                s = q.strip()
                qs_core = qs_core.filter(Q(title__icontains=s) | Q(description__icontains=s) | Q(submitted_by__first_name__icontains=s) | Q(organization__name__icontains=s))
            # merge core results
            core_items = [_core_event_to_dict(e) for e in qs_core[start:end]]
            results += core_items

    elif category == 'users':
        qs = build_user_queryset(q=q or None, filters=filters or None).order_by('-date_joined')
        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        results = [_user_to_dict(u) for u in qs[start:end]]

    elif category == 'reports':
        # Core Reports
        qs = build_report_queryset(q=q or None, filters=filters or None).order_by('-created_at')
        total = qs.count()

        start = (page - 1) * page_size if page_size else 0
        end = start + page_size if page_size else None

        results = []
        for r in qs[start:end]:
            results.append({
                'id': r.id,
                'title': r.title,
                'report_type': r.get_report_type_display(),
                'organization': r.organization.name if r.organization else None,
                'submitted_by': r.submitted_by.get_full_name() if r.submitted_by else None,
                'status': r.status,
                'file': r.file.url if r.file else None,
                'is_proposal_report': False,
            })

        # EMT Event Reports
        evr_qs = EMTEventReport.objects.select_related('proposal', 'proposal__organization', 'proposal__submitted_by')

        # Apply search query
        if q:
            s = q.strip()
            evr_qs = evr_qs.filter(
                Q(proposal__event_title__icontains=s) |
                Q(proposal__organization__name__icontains=s) |
                Q(proposal__submitted_by__first_name__icontains=s) |
                Q(proposal__submitted_by__last_name__icontains=s)
            )

        # Apply filters
        for f in filters:
            f_type = f.get('type')
            f_val = f.get('value')

            if f_type == 'organization_type' and f_val:
                evr_qs = evr_qs.filter(proposal__organization__org_type_id=f_val)

            elif f_type == 'organization' and f_val:
                evr_qs = evr_qs.filter(proposal__organization_id=f_val)

            elif f_type == 'status' and f_val:
                # Only "Generated" is valid for event reports
                if str(f_val).lower() != "generated":
                    evr_qs = evr_qs.none()

        total += evr_qs.count()

        evr_qs = evr_qs[start:end] if page_size else evr_qs
        for evr in evr_qs:
            results.append({
                'title': evr.proposal.event_title if evr.proposal else "Untitled Event",
                'report_type': "Event Report",
                'organization': evr.proposal.organization.name if evr.proposal and evr.proposal.organization else None,
                'submitted_by': evr.proposal.submitted_by.get_full_name() if evr.proposal and evr.proposal.submitted_by else None,
                'status': "Generated",
                'file': None,
                'is_proposal_report': True,
            })


    elif category == 'organizations':
        qs = build_organization_queryset(q=q or None, filters=filters or None).order_by('org_type__name', 'name')
        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        results = [_org_to_dict(o) for o in qs[start:end]]

    else:
        return JsonResponse({'error': 'Invalid category. Choose events/users/reports/organizations'}, status=400)

    return JsonResponse({
        'category': category,
        'q': q,
        'page': page,
        'page_size': page_size,
        'total': total,
        'results': results
    }, safe=False)


# -------------------------
# Export endpoints (CSV / Excel)
# -------------------------
@csrf_exempt
@login_required
@user_passes_test(is_admin)
def api_export_csv(request):
    """
    Export results as CSV. Accepts same payload as api_search.
    POST JSON payload recommended.
    """
    try:
        payload = json.loads(request.body.decode('utf-8') or "{}")
    except Exception:
        payload = {}

    # Reuse search logic to build list
    payload.setdefault('page', 1)
    payload.setdefault('page_size', 1000000)  # export everything by default (cap by server memory)
    # For export we want all rows, so we set a large page_size; you may prefer streaming for huge datasets.

    # call api_search-like logic but not via another HTTP call — reuse functions directly
    category = (payload.get('category') or '').lower()
    q = payload.get('q', '') or ''
    filters = payload.get('filters', []) or []

    # pick queryset & serializer
    if category == 'events':
        qs = build_event_queryset(q=q or None, filters=filters or None).order_by('-created_at')
        items = [_emt_event_to_dict(e) for e in qs]
    elif category == 'users':
        qs = build_user_queryset(q=q or None, filters=filters or None).order_by('-date_joined')
        items = [_user_to_dict(u) for u in qs]
    elif category == 'reports':
        qs = build_report_queryset(q=q or None, filters=filters or None).order_by('-created_at')
        items = [_report_to_dict(r) for r in qs]
    elif category == 'organizations':
        qs = build_organization_queryset(q=q or None, filters=filters or None).order_by('org_type__name', 'name')
        items = [_org_to_dict(o) for o in qs]
    else:
        return JsonResponse({'error': 'Invalid category for export'}, status=400)

    if not items:
        # small CSV with message
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="export_{category}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        response.write('No data found for selected filters')
        return response

    # determine fieldnames (union)
    fieldnames = sorted({k for it in items for k in it.keys()})
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="export_{category}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    writer = csv.DictWriter(response, fieldnames=fieldnames)
    writer.writeheader()
    for it in items:
        writer.writerow({k: it.get(k, '') for k in fieldnames})
    return response


@csrf_exempt
@login_required
@user_passes_test(is_admin)
def api_export_excel(request):
    """
    Export results as XLSX (requires xlsxwriter).
    Accepts same payload as api_search.
    """
    if xlsxwriter is None:
        return JsonResponse({'error': 'XLSX export not available (xlsxwriter missing)'}, status=501)
    try:
        payload = json.loads(request.body.decode('utf-8') or "{}")
    except Exception:
        payload = {}
    category = (payload.get('category') or '').lower()
    q = payload.get('q', '') or ''
    filters = payload.get('filters', []) or []

    if category == 'events':
        objs = [_emt_event_to_dict(e) for e in build_event_queryset(q=q or None, filters=filters or None).order_by('-created_at')]
    elif category == 'users':
        objs = [_user_to_dict(u) for u in build_user_queryset(q=q or None, filters=filters or None).order_by('-date_joined')]
    elif category == 'reports':
        objs = [_report_to_dict(r) for r in build_report_queryset(q=q or None, filters=filters or None).order_by('-created_at')]
    elif category == 'organizations':
        objs = [_org_to_dict(o) for o in build_organization_queryset(q=q or None, filters=filters or None).order_by('org_type__name', 'name')]
    else:
        return JsonResponse({'error': 'Invalid category for export'}, status=400)

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    sheet_name = category[:31] if category else 'Export'
    worksheet = workbook.add_worksheet(sheet_name)

    if not objs:
        worksheet.write(0, 0, 'No data found')
    else:
        fieldnames = sorted({k for it in objs for k in it.keys()})
        # header
        for col, header in enumerate(fieldnames):
            worksheet.write(0, col, header)
        # rows
        for row_idx, it in enumerate(objs, start=1):
            for col_idx, field in enumerate(fieldnames):
                worksheet.write(row_idx, col_idx, str(it.get(field, '')))
    workbook.close()
    output.seek(0)
    response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="export_{category}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    return response


# -------------------------
# Quick summary endpoint for badges
# -------------------------
@login_required
@user_passes_test(is_admin)
def api_quick_summary(request):
    """Return counts for each category to display small badges in UI."""
    ot = request.GET.get('org_type')
    if ot:
        try:
            otid = int(ot)
            ev_count = EMTEventProposal.objects.filter(organization__org_type_id=otid).count()
            rep_count = Report.objects.filter(organization__org_type_id=otid).count()
            org_count = Organization.objects.filter(org_type_id=otid).count()
            user_count = User.objects.filter(role_assignments__organization__org_type_id=otid).distinct().count()
        except Exception:
            ev_count = EMTEventProposal.objects.count()
            rep_count = Report.objects.count()
            org_count = Organization.objects.count()
            user_count = User.objects.count()
    else:
        ev_count = EMTEventProposal.objects.count()
        rep_count = Report.objects.count()
        org_count = Organization.objects.count()
        user_count = User.objects.count()

    return JsonResponse({
        'events': ev_count,
        'reports': rep_count,
        'organizations': org_count,
        'users': user_count
    })


# ---------------------------------------------
#           Switch View (Admin)
# ---------------------------------------------

@login_required
def stop_impersonation(request):
    """Stop impersonating and return to original user"""
    if 'impersonate_user_id' in request.session:
        from core.models import log_impersonation_end

        log_impersonation_end(request)
        del request.session['impersonate_user_id']
        if 'original_user_id' in request.session:
            del request.session['original_user_id']
        messages.success(request, 'Stopped impersonation')

    return redirect('admin_dashboard')

@login_required
def admin_impersonate_user(request, user_id):
    """Start impersonating a user from admin pages."""
    if not is_admin(request.user):
        raise PermissionDenied("You are not authorized to impersonate users.")

    # Allow impersonation of any existing user regardless of ``is_active`` status.
    # Previously we restricted to ``is_active=True`` which resulted in a 404
    # when attempting to impersonate inactive users from the user management
    # page. By removing that filter the view will locate the user record and
    # proceed with impersonation.
    target_user = get_object_or_404(User, id=user_id)
    request.session['impersonate_user_id'] = target_user.id
    request.session['original_user_id'] = request.user.id

    from core.models import log_impersonation_start

    log_impersonation_start(request, target_user)
    messages.success(request, f"Now impersonating {target_user.get_full_name() or target_user.username}")
    next_url = safe_next(request, fallback=reverse('dashboard'))
    return redirect(next_url)

@login_required
def get_recent_users_api(request):
    """Get recently switched users"""
    if not is_admin(request.user):
        raise PermissionDenied("Admin access required")
    try:
        # Get recent impersonation history (you might want to store this in a model)
        # For now, returning some sample data
        recent_users = [
            {
                'id': 1,
                'name': 'John Doe',
                'email': 'john@example.com',
                'last_switch': '2024-01-15'
            }
        ]

        return JsonResponse({'recent_users': recent_users})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    
@login_required
def switch_user_view(request):
    """Display the switch user interface"""
    if not is_admin(request.user):
        raise PermissionDenied("Admin access required")
    users = User.objects.filter(is_active=True, last_login__isnull=False).select_related().order_by('username')
    
    # Get current impersonated user if any
    impersonated_user = None
    if 'impersonate_user_id' in request.session:
        try:
            impersonated_user = User.objects.get(id=request.session['impersonate_user_id'])
        except User.DoesNotExist:
            # Clean up invalid session data
            del request.session['impersonate_user_id']
    
    context = {
        'users': users,
        'impersonated_user': impersonated_user,
        'original_user': request.user,
    }
    return render(request, 'core/switch_user.html', context)

@login_required
def search_users_api(request):
    """API endpoint for quick user search"""
    if not is_admin(request.user):
        raise PermissionDenied("Admin access required")
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            search_term = data.get('search', '').strip()
            
            if len(search_term) < 2:
                return JsonResponse({'users': []})
            
            # Search users by name, username, or email
            users = User.objects.filter(
                Q(username__icontains=search_term) |
                Q(first_name__icontains=search_term) |
                Q(last_name__icontains=search_term) |
                Q(email__icontains=search_term),
                is_active=True
            ).exclude(
                id=request.user.id  # Don't include current user
            ).order_by('first_name', 'last_name', 'username')[:10]  # Limit to 10 results
            
            users_data = []
            for user in users:
                users_data.append({
                    'id': user.id,
                    'username': user.username,
                    'full_name': user.get_full_name(),
                    'email': user.email,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser
                })
            
            return JsonResponse({'users': users_data})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
@require_POST
def impersonate_user(request):
    """Start impersonating a user"""
    if not is_admin(request.user):
        raise PermissionDenied("Admin access required")
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        
        if not user_id:
            return JsonResponse({'success': False, 'error': 'User ID is required'})
        
        target_user = get_object_or_404(
            User, id=user_id, is_active=True, last_login__isnull=False
        )
        
        # Store the impersonation in session
        request.session['impersonate_user_id'] = target_user.id
        request.session['original_user_id'] = request.user.id
        
        messages.success(request, f'Now viewing as: {target_user.get_full_name() or target_user.username}')
        
        return JsonResponse({
            'success': True,
            'message': f'Now impersonating {target_user.get_full_name() or target_user.username}',
            'user': {
                'id': target_user.id,
                'username': target_user.username,
                'full_name': target_user.get_full_name(),
                'email': target_user.email
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# ─────────────────────────────────────────────────────────────
#  Student Event Details View
# ─────────────────────────────────────────────────────────────
@login_required
def student_event_details(request, proposal_id):
    """Display event details in student-friendly format"""
    proposal = get_object_or_404(EventProposal, id=proposal_id)
    
    # Check if user has permission to view this proposal
    # Allow if: user is the submitter, faculty in charge, or superuser
    user_can_view = (
        request.user == proposal.submitted_by or
        request.user in proposal.faculty_incharges.all() or
        request.user.is_superuser or
        proposal.status == 'finalized'  # Anyone can view finalized events
    )
    
    if not user_can_view:
        messages.error(request, "You don't have permission to view this event.")
        return redirect('dashboard')
    
    context = {
        'proposal': proposal,
    }
    
    return render(request, 'core/student_event_details.html', context)


# ─────────────────────────────────────────────────────────────
#  PSO & PO Management API Endpoints
# ─────────────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def api_organization_programs(request, org_id):
    """API endpoint to get programs for an organization"""
    try:
        programs = Program.objects.filter(organization_id=org_id).values(
            'id', 'name'
        )
        
        return JsonResponse(list(programs), safe=False)
    
    except Exception as e:
        logger.error(f"Error fetching programs for organization {org_id}: {str(e)}")
        return JsonResponse({'error': 'Failed to fetch programs'}, status=500)

@user_passes_test(lambda u: u.is_superuser)
@require_http_methods(["GET"])
def api_program_outcomes(request, program_id):
    """API endpoint to get outcomes for a program - Enhanced for assigned users"""
    from .models import Program, ProgramOutcome, ProgramSpecificOutcome
    try:
        outcome_type = request.GET.get('type', '').upper()
        show_archived = request.GET.get('archived') in ("1", "true", "True")

        if outcome_type == 'PO':
            base_qs = ProgramOutcome.all_objects if show_archived else ProgramOutcome.objects
            outcomes = base_qs.filter(program_id=program_id)
            if show_archived:
                outcomes = outcomes.filter(status='archived')
            outcomes = outcomes.values('id', 'description', 'status')
            return JsonResponse(list(outcomes), safe=False)
        elif outcome_type == 'PSO':
            base_qs = ProgramSpecificOutcome.all_objects if show_archived else ProgramSpecificOutcome.objects
            outcomes = base_qs.filter(program_id=program_id)
            if show_archived:
                outcomes = outcomes.filter(status='archived')
            outcomes = outcomes.values('id', 'description', 'status')
            return JsonResponse(list(outcomes), safe=False)
        else:
            # If no type specified, return both POs and PSOs
            program = Program.objects.get(id=program_id)
            if show_archived:
                pos_qs = ProgramOutcome.all_objects.filter(program=program, status='archived')
                pso_qs = ProgramSpecificOutcome.all_objects.filter(program=program, status='archived')
            else:
                pos_qs = program.pos.all()
                pso_qs = program.psos.all()
            pos = [
                {'id': po.id, 'description': po.description, 'status': getattr(po, 'status', 'active')}
                for po in pos_qs
            ]
            psos = [
                {'id': pso.id, 'description': pso.description, 'status': getattr(pso, 'status', 'active')}
                for pso in pso_qs
            ]
            return JsonResponse({
                'program': {
                    'id': program.id,
                    'name': program.name,
                    'organization': program.organization.name if program.organization else None
                },
                'pos': pos,
                'psos': psos
            })
    except Exception as e:
        logger.error(f"Error fetching program outcomes for program {program_id}: {str(e)}")
        return JsonResponse({'error': 'Failed to fetch outcomes'}, status=500)

def is_superuser(u):
    return u.is_superuser


@login_required
@user_passes_test(is_superuser)
def class_rosters(request, org_id):
    org = get_object_or_404(Organization, pk=org_id)
    year = request.GET.get("year")
    if year:
        request.session["active_year"] = year
    else:
        year = request.session.get("active_year")

    qs = RoleAssignment.objects.filter(
        organization=org,
        role__name__iexact="student",
    )
    if year:
        qs = qs.filter(academic_year=year)

    classes = (
        qs.values("class_name")
        .annotate(student_count=Count("id"))
        .order_by("class_name")
    )

    context = {
        "organization": org,
        "academic_year": year,
        "classes": classes,
    }
    return render(request, "core/admin/class_rosters.html", context)


@login_required
@user_passes_test(is_superuser)
def class_roster_detail(request, org_id, class_name):
    org = get_object_or_404(Organization, pk=org_id)
    year = request.GET.get("year")
    if year:
        request.session["active_year"] = year
    else:
        year = request.session.get("active_year")
    q = request.GET.get("q", "").strip()

    ras = RoleAssignment.objects.select_related("user", "role").filter(
        organization=org,
        role__name__iexact="student",
        class_name=class_name,
    )
    if year:
        ras = ras.filter(academic_year=year)

    if q:
        ras = ras.filter(
            Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(user__email__icontains=q)
            | Q(user__username__icontains=q)
        )

    ras = ras.order_by("user__first_name", "user__last_name")
    paginator = Paginator(ras, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "organization": org,
        "academic_year": year,
        "class_name": class_name,
        "page_obj": page_obj,
        "q": q,
    }
    return render(request, "core/admin/class_roster_detail.html", context)

# ─────────────────────────────────────────────────────────────
#  PO/PSO Assignment Management API Views
# ─────────────────────────────────────────────────────────────

@user_passes_test(lambda u: u.is_superuser)
@require_http_methods(["GET"])
def api_available_faculty_users(request, org_id):
    """Get faculty users available for assignment to an organization - STRICT FACULTY ONLY with Department Filtering"""
    try:
        from .models import Organization, RoleAssignment
        
        organization = Organization.objects.get(id=org_id)
        search_query = request.GET.get('search', '').strip()
        
        # Enhanced Department-based Filtering Logic
        # If organization is a Department, only show faculty assigned to that department
        # If organization has parent, also include faculty from parent organization
        
        logger.info(f"Loading faculty for org: {organization.name} (Type: {organization.org_type.name})")
        
        # Build organization filter for faculty role assignments
        org_filter = Q(role_assignments__organization=organization)
        
        # Include parent organization if exists (for hierarchical access)
        if organization.parent:
            org_filter |= Q(role_assignments__organization=organization.parent)
            logger.info(f"Including parent org: {organization.parent.name}")
        
        # For Department type organizations, ensure strict department filtering
        if organization.org_type.name.lower() in ['department', 'dept']:
            # Only show faculty specifically assigned to this department
            # Don't include broader university-level faculty unless explicitly assigned
            org_filter = Q(role_assignments__organization=organization)
            logger.info(f"Strict department filtering for: {organization.name}")
        
        # Get all active users with Faculty role assignments
        faculty_users = User.objects.select_related('profile').prefetch_related(
            'role_assignments__organization', 
            'role_assignments__role',
            'role_assignments__organization__org_type'
        ).filter(
            is_active=True,
            role_assignments__role__name__iexact='Faculty'  # STRICT: Only Faculty role
        ).filter(org_filter).distinct()
        
        # Apply search filter if provided (search by name, username, email)
        if search_query:
            search_filter = (
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query)
            )
            faculty_users = faculty_users.filter(search_filter).distinct()
            logger.info(f"Applied search filter: '{search_query}'")
        
        # Prepare user data with enhanced role information
        users_data = []
        for user in faculty_users:
            # Build RoleAssignment-level filter (do NOT reuse User-level org_filter)
            if organization.org_type.name.lower() in ['department', 'dept']:
                ra_filter = Q(organization=organization)
            else:
                org_ids = [organization.id]
                if organization.parent_id:
                    org_ids.append(organization.parent_id)
                ra_filter = Q(organization_id__in=org_ids)

            # Get user's faculty role assignments for this org/parent
            faculty_assignments = user.role_assignments.filter(
                role__name__iexact='Faculty'
            ).filter(ra_filter)

            # Skip if no faculty assignments found
            if not faculty_assignments.exists():
                continue

            # Get organizations and roles for display
            org_names = []
            role_names = []

            for assignment in faculty_assignments:
                if assignment.organization:
                    org_names.append(assignment.organization.name)
                if assignment.role:
                    role_names.append(assignment.role.name)

            # Remove duplicates while preserving order
            org_names = list(dict.fromkeys(org_names))
            role_names = list(dict.fromkeys(role_names))

            # True if any assignment is directly in this department
            is_dept_faculty = any(
                (assignment.organization_id == organization.id)
                for assignment in faculty_assignments
            )

            users_data.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.get_full_name() or user.username,
                'email': user.email,
                'roles': role_names,
                'organizations': org_names,
                'is_department_faculty': is_dept_faculty
            })
        
        logger.info(f"Found {len(users_data)} FACULTY users for org {org_id} ('{organization.name}') with search '{search_query}'")
        return JsonResponse(users_data, safe=False)
        
    except Organization.DoesNotExist:
        return JsonResponse({'error': 'Organization not found'}, status=404)
    except Exception as e:
        logger.error(f"Error fetching faculty users for org {org_id}: {str(e)}")
        return JsonResponse({'error': f'Failed to fetch users: {str(e)}'}, status=500)

@user_passes_test(lambda u: u.is_superuser)
@require_http_methods(["GET"])
def api_debug_org_users(request, org_id):
    """Debug endpoint to see what users and roles exist for an organization"""
    try:
        from .models import Organization, RoleAssignment
        
        organization = Organization.objects.get(id=org_id)
        
        # Get all users with any role in this organization
        all_users = User.objects.filter(
            role_assignments__organization=organization,
            is_active=True
        ).distinct()
        
        # Get all role assignments for this org
        role_assignments = RoleAssignment.objects.filter(
            organization=organization
        ).select_related('user', 'role')
        
        debug_data = {
            'organization': {
                'id': organization.id,
                'name': organization.name,
                'type': organization.org_type.name,
                'parent': organization.parent.name if organization.parent else None
            },
            'total_users_in_org': all_users.count(),
            'total_role_assignments': role_assignments.count(),
            'users': [],
            'role_assignments': []
        }
        
        for user in all_users:
            user_roles = list(user.role_assignments.filter(
                organization=organization
            ).values_list('role__name', flat=True))
            
            debug_data['users'].append({
                'id': user.id,
                'username': user.username,
                'full_name': user.get_full_name() or user.username,
                'email': user.email,
                'roles': user_roles
            })
        
        for ra in role_assignments:
            debug_data['role_assignments'].append({
                'user': ra.user.username,
                'role': ra.role.name if ra.role else 'No role',
                'org': ra.organization.name if ra.organization else 'No org'
            })
        
        return JsonResponse(debug_data, safe=False)
        
    except Organization.DoesNotExist:
        return JsonResponse({'error': 'Organization not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Debug failed: {str(e)}'}, status=500)

@user_passes_test(lambda u: u.is_superuser)
@require_http_methods(["GET", "POST", "DELETE"])
def api_popso_assignments(request, org_id=None):
    """Manage PO/PSO assignments for organizations"""
    from .models import Organization, POPSOAssignment
    import json
    
    if request.method == "GET":
        try:
            if org_id:
                # Get assignment for specific organization
                try:
                    assignment = POPSOAssignment.objects.get(
                        organization_id=org_id, 
                        is_active=True
                    )
                    return JsonResponse({
                        'assigned_user': {
                            'id': assignment.assigned_user.id,
                            'full_name': assignment.assigned_user.get_full_name() or assignment.assigned_user.username,
                            'email': assignment.assigned_user.email
                        },
                        'assigned_at': assignment.assigned_at.isoformat(),
                        'assigned_by': assignment.assigned_by.get_full_name() or assignment.assigned_by.username
                    })
                except POPSOAssignment.DoesNotExist:
                    return JsonResponse({'assigned_user': None})
            else:
                # Get all assignments
                assignments = POPSOAssignment.objects.filter(is_active=True).select_related(
                    'organization', 'assigned_user', 'assigned_by'
                )
                
                assignments_data = {}
                for assignment in assignments:
                    assignments_data[assignment.organization.id] = {
                        'assigned_user': {
                            'id': assignment.assigned_user.id,
                            'full_name': assignment.assigned_user.get_full_name() or assignment.assigned_user.username,
                            'email': assignment.assigned_user.email
                        },
                        'assigned_at': assignment.assigned_at.isoformat(),
                        'assigned_by': assignment.assigned_by.get_full_name() or assignment.assigned_by.username
                    }
                
                return JsonResponse(assignments_data)
                
        except Exception as e:
            logger.error(f"Error fetching assignments: {str(e)}")
            return JsonResponse({'error': 'Failed to fetch assignments'}, status=500)
    
    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            organization = Organization.objects.get(id=data['organization_id'])
            assigned_user = User.objects.get(id=data['user_id'])
            
            # Deactivate existing assignment if any
            POPSOAssignment.objects.filter(
                organization=organization,
                is_active=True
            ).update(is_active=False)
            
            # Create new assignment
            assignment = POPSOAssignment.objects.create(
                organization=organization,
                assigned_user=assigned_user,
                assigned_by=request.user,
                is_active=True
            )
            
            return JsonResponse({
                'success': True,
                'assignment': {
                    'assigned_user': {
                        'id': assignment.assigned_user.id,
                        'full_name': assignment.assigned_user.get_full_name() or assignment.assigned_user.username,
                        'email': assignment.assigned_user.email
                    },
                    'assigned_at': assignment.assigned_at.isoformat(),
                    'assigned_by': assignment.assigned_by.get_full_name() or assignment.assigned_by.username
                }
            })
            
        except (Organization.DoesNotExist, User.DoesNotExist, KeyError, json.JSONDecodeError) as e:
            return JsonResponse({'success': False, 'error': 'Invalid data'}, status=400)
        except Exception as e:
            logger.error(f"Error creating assignment: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Failed to create assignment'}, status=500)
    
    elif request.method == "DELETE":
        try:
            if not org_id:
                return JsonResponse({'success': False, 'error': 'Organization ID required'}, status=400)
                
            POPSOAssignment.objects.filter(
                organization_id=org_id,
                is_active=True
            ).update(is_active=False)
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            logger.error(f"Error removing assignment: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Failed to remove assignment'}, status=500)

@login_required
@require_http_methods(["POST"])
def api_log_popso_change(request):
    """Log PO/PSO changes made by assigned users"""
    from .models import POPSOChangeNotification
    import json
    
    try:
        data = json.loads(request.body)
        
        notification = POPSOChangeNotification.objects.create(
            user=request.user,
            organization_id=data['organization_id'],
            action=data['action'],
            outcome_type=data['outcome_type'],
            outcome_description=data['outcome_description']
        )
        
        return JsonResponse({'success': True, 'notification_id': notification.id})
        
    except (KeyError, json.JSONDecodeError) as e:
        return JsonResponse({'success': False, 'error': 'Invalid data'}, status=400)
    except Exception as e:
        logger.error(f"Error logging PO/PSO change: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Failed to log change'}, status=500)

## Deprecated with removal of settings PSO/PO page
# @login_required
# @require_http_methods(["GET"])
# def api_popso_manager_status(request):
#     """Check if the current user is assigned as a PO/PSO manager"""
#     from .models import POPSOAssignment
#     try:
#         is_manager = POPSOAssignment.objects.filter(
#             assigned_user=request.user,
#             is_active=True
#         ).exists()
#         assignments = []
#         if is_manager:
#             assignments = POPSOAssignment.objects.filter(
#                 assigned_user=request.user,
#                 is_active=True
#             ).select_related('organization').values(
#                 'organization__id',
#                 'organization__name',
#                 'organization__org_type__name'
#             )
#         return JsonResponse({'is_manager': is_manager,'assignments': list(assignments)})
#     except Exception as e:
#         logger.error(f"Error checking manager status for user {request.user.id}: {str(e)}")
#         return JsonResponse({'error': 'Failed to check manager status'}, status=500)

## Removed: settings_pso_po_management page has been deleted.

@login_required
def cdl_head_dashboard(request):
    # Allow superusers, group CDL_HEAD, or users with CDL Admin/Head org roles in CDL orgs
    is_allowed = False
    if request.user.is_superuser or request.user.groups.filter(name="CDL_HEAD").exists():
        is_allowed = True
    else:
        try:
            from .models import RoleAssignment
            ras = (
                RoleAssignment.objects.filter(user=request.user)
                .select_related('role', 'organization', 'organization__org_type')
            )
            for ra in ras:
                role_name = (ra.role.name if ra.role else '').lower()
                org_type = (ra.organization.org_type.name if ra.organization and ra.organization.org_type else '').lower()
                if org_type == 'cdl' and role_name in {"cdl admin", "cdl head"}:
                    is_allowed = True
                    break
        except Exception:
            pass
    if not is_allowed:
        logger.warning("cdl_head_dashboard: access denied for user=%s", request.user.id)
        return HttpResponseForbidden()
    
    from emt.models import EventProposal, CDLSupport
    from django.db.models import Q, Count
    from django.utils import timezone
    from datetime import datetime, timedelta
    
    # Calculate KPIs from proposal data
    # Total Active Requests - Count of proposals with status "Active" (submitted, under_review, waiting)
    active_statuses = ['submitted', 'under_review', 'waiting']
    total_active_requests = EventProposal.objects.filter(status__in=active_statuses).count()
    
    # Assets Delivery Pending - Events with CDL support where assets are not yet delivered
    assets_pending = CDLSupport.objects.filter(
        proposal__status__in=['approved', 'finalized'],
        needs_support=True
    ).filter(
        Q(poster_required=True) | Q(certificates_required=True)
    ).count()
    
    # Unassigned Tasks - Events that need CDL support but don't have assignees yet
    unassigned_tasks = CDLSupport.objects.filter(
        needs_support=True,
        proposal__status__in=active_statuses
    ).count()  # You can add assignee field logic here when implemented
    
    # Total Events Supported - Count of proposals where CDL Support = Yes
    total_events_supported = CDLSupport.objects.filter(needs_support=True).count()
    
    # Get calendar events from proposals with CDL support
    calendar_events = []
    proposals_with_cdl = EventProposal.objects.filter(
        cdl_support__needs_support=True
    ).select_related('cdl_support').order_by('event_start_date')
    
    for proposal in proposals_with_cdl:
        if proposal.event_start_date:
            calendar_events.append({
                'id': proposal.id,
                'title': proposal.event_title,
                'date': proposal.event_start_date.strftime('%Y-%m-%d'),
                'status': proposal.status,
                'venue': proposal.venue,
                'organization': proposal.organization.name if proposal.organization else '',
                'type': 'cdl_support',
                'poster_required': proposal.cdl_support.poster_required if hasattr(proposal, 'cdl_support') else False,
                'certificates_required': proposal.cdl_support.certificates_required if hasattr(proposal, 'cdl_support') else False,
            })
    
    # Get event details for notifications section
    event_details = []
    recent_proposals = EventProposal.objects.filter(
        cdl_support__needs_support=True
    ).select_related('cdl_support', 'organization').order_by('-created_at')[:10]
    
    for proposal in recent_proposals:
        event_details.append({
            'id': proposal.id,
            'title': proposal.event_title,
            'status': proposal.get_status_display(),
            'date': proposal.event_start_date,
            'organization': proposal.organization.name if proposal.organization else '',
            'created_at': proposal.created_at,
            'poster_required': proposal.cdl_support.poster_required if hasattr(proposal, 'cdl_support') else False,
            'certificates_required': proposal.cdl_support.certificates_required if hasattr(proposal, 'cdl_support') else False,
        })
    
    # Get workload distribution data (placeholder for now)
    workload_data = {
        'members': ['CDL Member 1', 'CDL Member 2', 'CDL Member 3'],
        'assignments': [5, 3, 7]  # Number of assignments per member
    }
    
    context = {
        'total_active_requests': total_active_requests,
        'assets_pending': assets_pending,
        'unassigned_tasks': unassigned_tasks,
        'total_events_supported': total_events_supported,
        'calendar_events': calendar_events,
        'event_details': event_details,
        'workload_data': workload_data,
    }
    
    return render(request, "core/cdl_head_dashboard.html", context)


@login_required
def cdl_member_dashboard(request):
    if not (request.user.is_superuser or request.user.groups.filter(name="CDL_MEMBER").exists()):
        return HttpResponseForbidden()
    ctx = {
        "member_inbox": [],
        "member_work": [],
        "member_events": [],
        "member_stats_30d": {"ontime": None, "firstpass": None, "availability": None},
    }
    return render(request, "cdl/cdl_member_dashboard.html", ctx)

@login_required
def cdl_work_dashboard(request):
    # Allow superusers, group CDL_MEMBER, or users with CDL Employee/Member/Team org roles in CDL orgs
    is_allowed = False
    if request.user.is_superuser or request.user.groups.filter(name="CDL_MEMBER").exists():
        is_allowed = True
    else:
        try:
            from .models import RoleAssignment
            ras = (
                RoleAssignment.objects.filter(user=request.user)
                .select_related('role', 'organization', 'organization__org_type')
            )
            for ra in ras:
                role_name = (ra.role.name if ra.role else '').lower()
                org_type = (ra.organization.org_type.name if ra.organization and ra.organization.org_type else '').lower()
                if org_type == 'cdl' and role_name in {"cdl employee", "cdl member", "cdl team"}:
                    is_allowed = True
                    break
        except Exception:
            pass
    if not is_allowed:
        logger.warning("cdl_work_dashboard: access denied for user=%s", request.user.id)
        return HttpResponseForbidden()
    return render(request, "core/cdl_work_dashboard.html")

def cdl_create_availability(request):
    return HttpResponse("Create Availability (stub)")

def cdl_brand_kit(request):
    return HttpResponse("Brand Kit (stub)")

def cdl_templates_posters(request):
    return HttpResponse("Poster Templates (stub)")

@login_required
def cdl_dashboard(request):
    """Entry point for CDL dashboard; default to head dashboard for now."""
    return render(request, "core/cdl_head_dashboard.html")

def cdl_templates_certificates(request):
    return HttpResponse("Certificate Templates (stub)")

def cdl_media_guide(request):
    return HttpResponse("Media Naming Guide (stub)")

# ────────────────────────────────────────────────────────────────
#  CDL SUPPORT DETAIL PAGE + APIS
# ────────────────────────────────────────────────────────────────
from django.views.decorators.http import require_http_methods

@login_required
def cdl_support_detail_page(request):
    """Render support details shell; data loaded via AJAX using query param eventId.
    Also mark a session hint if user is CDL Head to control Assign button visibility.
    """
    try:
        from .models import OrganizationType, RoleAssignment
        heads = RoleAssignment.objects.filter(organization__org_type__name__iexact='CDL', role__name__icontains='head', user=request.user)
        if heads.exists():
            request.session['role'] = 'cdl_head'
    except Exception:
        pass
    return render(request, "core/cdl_support.html")

@login_required
def cdl_assign_tasks_page(request, proposal_id:int):
    """Assign Tasks page.
    - Heads/Admins: full board to assign members and create/edit tasks.
    - Employees/Members: restricted "employee mode" to update ONLY their task status.

    Accepts query param eventId (redundant with proposal_id) and optional mode=employee to force employee POV.
    """
    # Figure out if current user is CDL Head/Admin
    is_cdl_head = False
    try:
        from .models import OrganizationType, RoleAssignment
        heads = RoleAssignment.objects.filter(
            organization__org_type__name__iexact='CDL',
            role__name__icontains='head',
            user=request.user,
        )
        is_cdl_head = heads.exists() or request.user.is_superuser
        if is_cdl_head:
            request.session['role'] = 'cdl_head'
            request.session['cdl_assign_board'] = True
    except Exception:
        is_cdl_head = request.user.is_superuser

    # Employee POV either when explicitly requested or when user isn't a head
    employee_mode = (request.GET.get('mode') == 'employee') or (not is_cdl_head)
    return render(request, "core/cdl_assign_tasks.html", {
        'proposal_id': proposal_id,
        'employee_mode': employee_mode,
    })

# ────────────────────────────────────────────────────────────────
#  CDL Communication Page & APIs
# ────────────────────────────────────────────────────────────────
@login_required
def cdl_communication_page(request):
    """Render the communication log page. Accessible to CDL head and employees/members."""
    # Basic role check similar to work dashboard
    is_allowed = request.user.is_superuser or request.user.groups.filter(name="CDL_MEMBER").exists()
    if not is_allowed:
        try:
            from .models import RoleAssignment
            for ra in RoleAssignment.objects.filter(user=request.user).select_related('role','organization','organization__org_type'):
                role_name = (ra.role.name if ra.role else '').lower()
                org_type = (ra.organization.org_type.name if ra.organization and ra.organization.org_type else '').lower()
                if org_type == 'cdl' and any(k in role_name for k in ['head','employee','member','team']):
                    is_allowed = True; break
        except Exception:
            pass

    # Additional conditional: allow event proposer or faculty-incharge for a specific event
    # if the event has any CDL related support requirements (poster/certificates) so they can coordinate.
    if not is_allowed:
        event_id = request.GET.get('eventId') or request.GET.get('proposal_id')
        if event_id and event_id.isdigit():
            from emt.models import EventProposal  # local import to avoid circulars when app not loaded
            try:
                ep = (EventProposal.objects
                      .select_related('organization')
                      .prefetch_related('faculty_incharges')
                      .get(id=int(event_id)))
                # Determine if CDL support flags exist via related cdl_support (if present) or fallbacks used earlier in APIs
                cdl_flags = False
                try:
                    cs = getattr(ep, 'cdl_support', None)
                    if cs and (getattr(cs, 'poster_required', False) or getattr(cs, 'certificates_required', False)):
                        cdl_flags = True
                except Exception:
                    pass
                # If we cannot find cdl_support, still allow if proposal status is finalized (assuming potential design assets)
                if not cdl_flags and ep.status in ('finalized','approved'):
                    cdl_flags = True
                if cdl_flags:
                    # Is the user proposer or faculty incharge?
                    if ep.submitted_by_id == request.user.id or ep.faculty_incharges.filter(id=request.user.id).exists():
                        is_allowed = True
            except EventProposal.DoesNotExist:
                pass
    if not is_allowed:
        return HttpResponseForbidden()
    return render(request, 'core/cdl_communication.html')

from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.forms.models import model_to_dict
from .models import CDLCommunicationMessage

@login_required
@require_http_methods(["GET","POST"])
def api_cdl_communication(request):
    """List or create communication messages.
    GET params: page (optional), page_size (default 100 to return most recent quickly)
    POST expects: comment (text) and optional attachment file
    Returns JSON suitable for frontend consumption.
    """
    if request.method == 'POST':
        comment = (request.POST.get('comment') or '').strip()
        if not comment and 'attachment' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'Empty message'}, status=400)
        msg = CDLCommunicationMessage.objects.create(
            user=request.user,
            comment=comment or '(attachment)',
            attachment=request.FILES.get('attachment')
        )
        return JsonResponse(_comm_dict(msg), status=201)
    # GET
    qs = CDLCommunicationMessage.objects.all().order_by('-created_at')
    page = int(request.GET.get('page',1))
    page_size = min(int(request.GET.get('page_size',100)), 500)
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)
    return JsonResponse({
        'success': True,
        'messages': [_comm_dict(m) for m in page_obj.object_list],
        'page': page_obj.number,
        'num_pages': paginator.num_pages,
        'has_next': page_obj.has_next(),
    })

def _comm_dict(m:CDLCommunicationMessage):
    return {
        'id': m.id,
        'user_id': m.user_id,
        'user_username': m.user.username,
        'comment': m.comment,
        'created_at': m.created_at.isoformat(),
        'attachment_url': m.attachment.url if m.attachment else None,
    }

@login_required
@require_http_methods(["GET"])  # /api/cdl/support/<proposal_id>/
def api_cdl_support_detail(request, proposal_id:int):
    from django.shortcuts import get_object_or_404
    try:
        p = (
            EMTEventProposal.objects
            .select_related('organization', 'submitted_by', 'cdl_support')
            .prefetch_related('faculty_incharges', 'speakers')
            .get(id=proposal_id)
        )
    except EMTEventProposal.DoesNotExist:
        return JsonResponse({"success": False, "error": "Event not found"}, status=404)

    s = getattr(p, 'cdl_support', None)
    # Speakers (from Submit Proposal form)
    speakers = []
    try:
        for sp in getattr(p, 'speakers', []).all():
            speakers.append({
                'full_name': sp.full_name,
                'designation': sp.designation,
                'affiliation': sp.affiliation,
                'contact_email': sp.contact_email,
                'contact_number': sp.contact_number,
                'linkedin_url': sp.linkedin_url,
                'profile': sp.detailed_profile,
            })
    except Exception:
        speakers = []

    # CDL assignment details (if present)
    from emt.models import CDLAssignment as _CDLAssignment
    asg = getattr(p, 'cdl_assignment', None)

    data = {
        'id': p.id,
        'title': p.event_title,
        'status': p.status,
        'organization': p.organization.name if p.organization else None,
        'venue': p.venue,
        'date': (p.event_datetime.date().isoformat() if p.event_datetime else (p.event_start_date.isoformat() if p.event_start_date else None)),
        'submitted_by': p.submitted_by.get_full_name() or p.submitted_by.username,
        'submitter_email': p.submitted_by.email,
        'faculty_incharges': [u.get_full_name() or u.username for u in p.faculty_incharges.all()],
        'speakers': speakers,
        # support details
        'needs_support': bool(getattr(s, 'needs_support', False)),
        'poster_required': bool(getattr(s, 'poster_required', False)),
        'certificates_required': bool(getattr(s, 'certificates_required', False)),
        'poster_choice': getattr(s, 'poster_choice', None),
        'certificate_choice': getattr(s, 'certificate_choice', None),
        'poster_design_link': getattr(s, 'poster_design_link', None),
        'certificate_design_link': getattr(s, 'certificate_design_link', None),
        'other_services': getattr(s, 'other_services', []) or [],
    # assignment details
    'assigned_to_id': (asg.assignee_id if asg else getattr(p, 'report_assigned_to_id', None)),
    'assigned_to_name': ((asg.assignee.get_full_name() or asg.assignee.username) if asg else (p.report_assigned_to.get_full_name() if p.report_assigned_to else None)),
    'assigned_role': (asg.role if asg else None),
    'assigned_status': (asg.status if asg else None),
    }
    return JsonResponse({"success": True, "data": data})

@login_required
@require_http_methods(["POST"])  # /api/cdl/support/<proposal_id>/assign/
def api_cdl_support_assign(request, proposal_id:int):
    """Assign a proposal to a CDL member. Reuses report_assigned_to as assignment field.
    Also logs assignment time; member dashboard can pull from this.
    """
    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else request.POST
    except Exception:
        payload = request.POST
    member_id = payload.get('member_id') or payload.get('user_id')
    role_name = (payload.get('role') or '').strip()
    if not member_id:
        return JsonResponse({"success": False, "error": "member_id is required"}, status=400)

    try:
        p = EMTEventProposal.objects.get(id=proposal_id)
    except EMTEventProposal.DoesNotExist:
        return JsonResponse({"success": False, "error": "Event not found"}, status=404)

    try:
        member = User.objects.get(id=int(member_id))
    except Exception:
        return JsonResponse({"success": False, "error": "Invalid member"}, status=400)

    # Simple permission: admins or CDL members can assign
    is_cdl_member = request.user.groups.filter(name="CDL_MEMBER").exists()
    if not (request.user.is_superuser or is_cdl_member):
        return JsonResponse({"success": False, "error": "Not allowed"}, status=403)

    # Create or update CDLAssignment
    from emt.models import CDLAssignment as _CDLAssignment
    asg, _ = _CDLAssignment.objects.update_or_create(
        proposal=p,
        defaults={
            'assignee': member,
            'assigned_by': request.user,
            'role': role_name,
            'status': _CDLAssignment.Status.ASSIGNED,
        }
    )
    # Keep legacy field for compatibility
    p.report_assigned_to = member
    p.report_assigned_at = timezone.now()
    p.save(update_fields=["report_assigned_to", "report_assigned_at", "updated_at"])

    return JsonResponse({"success": True})

@login_required
@require_http_methods(["GET"])  # /api/cdl/support/<proposal_id>/resources/
def api_cdl_support_resources(request, proposal_id:int):
    """Return dynamic resource list for an event, CDL members, and existing assignments.
    Sources:
      - CDLSupport.poster_required/certificates_required/other_services
      - Members: RoleAssignment where organization.org_type.name == 'CDL' and role like employee/member
      - Existing per-resource assignments (emt.CDLTaskAssignment)
    """
    try:
        p = EMTEventProposal.objects.select_related('cdl_support').get(id=proposal_id)
    except EMTEventProposal.DoesNotExist:
        return JsonResponse({"success": False, "error": "Event not found"}, status=404)

    s = getattr(p, 'cdl_support', None)
    resources = []
    if getattr(s, 'poster_required', False):
        resources.append({ 'key':'poster', 'label':'Poster' })
    if getattr(s, 'certificates_required', False):
        resources.append({ 'key':'certificates', 'label':'Certificates' })
    try:
        for item in (getattr(s, 'other_services', []) or []):
            key = str(item).strip().lower().replace(' ', '_')
            label = str(item).strip()
            if key:
                resources.append({ 'key': key, 'label': label })
    except Exception:
        pass

    # CDL members via RoleAssignment
    from .models import OrganizationType, RoleAssignment
    org_types = OrganizationType.objects.filter(name__iexact="CDL")
    role_asg = RoleAssignment.objects.filter(organization__org_type__in=org_types).select_related('user','role')
    members = []
    seen = set()
    for ra in role_asg:
        rn = (ra.role.name or '').lower()
        if ('employee' in rn) or ('member' in rn):
            uid = ra.user.id
            if uid in seen:
                continue
            seen.add(uid)
            members.append({ 'id': uid, 'name': ra.user.get_full_name() or ra.user.username })

    # Existing assignments
    from emt.models import CDLTaskAssignment as _Task
    existing = {}
    task_objs = []
    qs_tasks = _Task.objects.filter(proposal=p).select_related('assignee')
    # Optional filter: employee POV should see only their tasks
    mode = (request.GET.get('mode') or '').lower()
    assignee = (request.GET.get('assignee') or '').lower()
    if mode == 'employee' or assignee in ('me', 'self'):
        qs_tasks = qs_tasks.filter(assignee=request.user)

    for t in qs_tasks:
        existing[t.resource_key] = { 'user_id': t.assignee_id, 'name': (t.assignee.get_full_name() or t.assignee.username) if t.assignee_id else None }
        task_objs.append({
            'id': t.id,
            'resource': t.resource_key,
            'label': t.label or t.resource_key.replace('_',' ').title(),
            'status': t.status,
            'assignee_id': t.assignee_id,
            'assignee_name': ((t.assignee.get_full_name() or t.assignee.username) if t.assignee_id else None),
        })
    # Merge any custom task keys into resources list (non-destructive for clients already merging)
    for key in list(existing.keys()):
        if not any(r['key']==key for r in resources):
            resources.append({ 'key': key, 'label': key.replace('_',' ').title(), 'custom': True })

    # If employee POV, restrict members to self only (UI safety; server also enforces in CRUD)
    if mode == 'employee' or assignee in ('me', 'self'):
        members = [{ 'id': request.user.id, 'name': request.user.get_full_name() or request.user.username }]

    return JsonResponse({ 'success': True, 'resources': resources, 'members': members, 'assignments': existing, 'tasks': task_objs })

@login_required
@require_http_methods(["POST"])  # /api/cdl/support/<proposal_id>/task-assignments/
def api_cdl_save_task_assignments(request, proposal_id:int):
    """Save per-resource assignments. Payload:
      { assignments: [ { resource: 'poster', user_id: 123 }, ... ] }
    Upsert by (proposal, resource).
    """
    try:
        p = EMTEventProposal.objects.get(id=proposal_id)
    except EMTEventProposal.DoesNotExist:
        return JsonResponse({"success": False, "error": "Event not found"}, status=404)

    try:
        payload = json.loads(request.body or '{}')
    except Exception:
        payload = {}
    items = payload.get('assignments') or []
    to_unassign = payload.get('unassign') or []  # list of resource keys to remove

    # Permission: CDL Head / Admin only
    is_cdl_head = False
    try:
        from .models import OrganizationType, RoleAssignment
        heads = RoleAssignment.objects.filter(organization__org_type__name__iexact='CDL', role__name__icontains='head', user=request.user)
        is_cdl_head = heads.exists() or request.user.is_superuser
    except Exception:
        is_cdl_head = request.user.is_superuser
    if not is_cdl_head:
        return JsonResponse({"success": False, "error": "Not allowed"}, status=403)

    from django.contrib.auth.models import User
    from emt.models import CDLTaskAssignment as _Task
    saved = []
    for it in items:
        res_key = (it.get('resource') or '').strip()
        uid = it.get('user_id')
        if not res_key or not uid:
            continue
        try:
            user = User.objects.get(id=int(uid))
        except Exception:
            continue
        obj, _ = _Task.objects.update_or_create(
            proposal=p,
            resource_key=res_key,
            defaults={ 'assignee': user, 'assigned_by': request.user },
        )
        saved.append({ 'resource': res_key, 'user_id': user.id })

    # Handle unassign deletions
    removed = []
    if isinstance(to_unassign, list) and to_unassign:
        qs = _Task.objects.filter(proposal=p, resource_key__in=[(str(k) or '').strip() for k in to_unassign])
        removed = list(qs.values_list('resource_key', flat=True))
        qs.delete()

    return JsonResponse({ 'success': True, 'saved': saved, 'removed': removed })

@login_required
@require_http_methods(["POST","PUT","DELETE"])  # /api/cdl/support/<proposal_id>/tasks/
def api_cdl_tasks_crud(request, proposal_id:int):
    """CRUD for CDL per-resource tasks.
    POST {resource, label?, assignee_id?, status?} -> create/update (by resource key)
    PUT  {id, label?, assignee_id?, status?} -> update
    DELETE {id} or {resource} -> delete
    """
    try:
        p = EMTEventProposal.objects.get(id=proposal_id)
    except EMTEventProposal.DoesNotExist:
        return JsonResponse({"success": False, "error": "Event not found"}, status=404)

    from emt.models import CDLTaskAssignment as _Task
    from django.contrib.auth.models import User
    payload = {}
    try:
        payload = json.loads(request.body or '{}')
    except Exception:
        payload = {}

    # Permission model: Heads/Admins can create/update/delete; Employees can only update STATUS of their own tasks
    is_cdl_head = False
    try:
        from .models import OrganizationType, RoleAssignment
        heads = RoleAssignment.objects.filter(organization__org_type__name__iexact='CDL', role__name__icontains='head', user=request.user)
        is_cdl_head = heads.exists() or request.user.is_superuser
    except Exception:
        is_cdl_head = request.user.is_superuser

    if request.method == 'POST':
        if not is_cdl_head:
            return JsonResponse({'success': False, 'error': 'Not allowed'}, status=403)
        res_key = (payload.get('resource') or '').strip()
        if not res_key:
            return JsonResponse({'success': False, 'error': 'resource is required'}, status=400)
        label = (payload.get('label') or '').strip()
        assignee_id = payload.get('assignee_id')
        status = (payload.get('status') or _Task.Status.ASSIGNED)
        assignee = None
        if assignee_id:
            try: assignee = User.objects.get(id=int(assignee_id))
            except Exception: assignee = None
        obj, _ = _Task.objects.update_or_create(
            proposal=p, resource_key=res_key,
            defaults={'label': label, 'assignee': assignee, 'status': status, 'assigned_by': request.user}
        )
        return JsonResponse({'success': True, 'task': {
            'id': obj.id, 'resource': obj.resource_key, 'label': obj.label or obj.resource_key, 'status': obj.status,
            'assignee_id': obj.assignee_id, 'assignee_name': (obj.assignee.get_full_name() or obj.assignee.username) if obj.assignee_id else None
        }})

    if request.method == 'PUT':
        tid = payload.get('id')
        try:
            obj = _Task.objects.get(id=int(tid), proposal=p)
        except Exception:
            return JsonResponse({'success': False, 'error': 'Task not found'}, status=404)
        if not is_cdl_head:
            # Employees can only update their own task status
            if obj.assignee_id != request.user.id:
                return JsonResponse({'success': False, 'error': 'Not allowed'}, status=403)
            if 'status' in payload and payload['status'] is not None:
                obj.status = payload['status']
        else:
            for fld in ('label','status'):
                if fld in payload and payload[fld] is not None:
                    setattr(obj, fld, payload[fld])
            if 'assignee_id' in payload:
                aid = payload.get('assignee_id')
                if aid:
                    try: obj.assignee = User.objects.get(id=int(aid))
                    except Exception: obj.assignee = None
                else:
                    obj.assignee = None
        obj.save()
        return JsonResponse({'success': True})

    if request.method == 'DELETE':
        if not is_cdl_head:
            return JsonResponse({'success': False, 'error': 'Not allowed'}, status=403)
        tid = payload.get('id'); res_key = payload.get('resource')
        qs = _Task.objects.filter(proposal=p)
        if tid: qs = qs.filter(id=int(tid))
        elif res_key: qs = qs.filter(resource_key=str(res_key))
        else: return JsonResponse({'success': False, 'error': 'id or resource required'}, status=400)
        deleted = list(qs.values_list('id', flat=True)); qs.delete()
        return JsonResponse({'success': True, 'deleted': deleted})

@login_required
@require_http_methods(["GET"])  # /api/cdl/member/work/
def api_cdl_member_work(request):
    """Return proposals assigned to the logged-in member via report_assigned_to.
    This powers the CDL Team Dashboard 'Assigned Events' list.
    """
    me = request.user
    qs = EMTEventProposal.objects.filter(report_assigned_to=me).select_related('organization')[:100]
    items = []
    for p in qs:
        items.append({
            'id': p.id,
            'event': p.event_title,
            'type': 'poster' if getattr(getattr(p,'cdl_support',None),'poster_required',False) else ('certificate' if getattr(getattr(p,'cdl_support',None),'certificates_required',False) else 'coverage'),
            'priority': 'Medium',
            'due_date': (p.event_start_date.isoformat() if p.event_start_date else None) or (p.event_datetime.date().isoformat() if p.event_datetime else None),
            'status': 'pending',
            'rev': 0,
            'created_at': p.created_at.isoformat(),
            'assigned_at': p.report_assigned_at.isoformat() if p.report_assigned_at else None,
        })
    return JsonResponse({'success': True, 'items': items})

@login_required
@require_http_methods(["GET"])  # /api/cdl/members/
def api_cdl_members(request):
    from django.contrib.auth.models import User, Group
    qs = User.objects.filter(groups__name="CDL_MEMBER", is_active=True).order_by('first_name','last_name')
    members = [{'id':u.id,'name':u.get_full_name() or u.username} for u in qs]
    return JsonResponse({'success': True, 'members': members})

@login_required
@require_http_methods(["GET"])  # /api/cdl/users/
def api_cdl_users(request):
    """Return CDL users grouped by role for org_type = 'CDL'.

    Output example:
      { success: true, users: { head: [ {id,name}... ], employee: [ ... ] } }
    """
    from django.contrib.auth.models import User
    from .models import OrganizationType, RoleAssignment

    # Find org_type "CDL"
    org_types = OrganizationType.objects.filter(name__iexact="CDL")
    role_asg = RoleAssignment.objects.filter(organization__org_type__in=org_types).select_related('user', 'role', 'organization')
    users = {'head': [], 'employee': []}
    seen = set()
    for ra in role_asg:
        key = None
        rn = (ra.role.name or '').strip().lower()
        if 'head' in rn:
            key = 'head'
        elif 'employee' in rn or 'member' in rn:
            key = 'employee'
        if key:
            uid = ra.user.id
            if (key, uid) in seen:
                continue
            seen.add((key, uid))
            users[key].append({'id': uid, 'name': ra.user.get_full_name() or ra.user.username, 'role': ra.role.name})
    return JsonResponse({'success': True, 'users': users})

@login_required
@require_GET
def api_cdl_member_data(request):
    """Unified data feed for CDL Member dashboard.

    Returns:
      {
        success: true,
        stats: { assigned: int, due_today: int, waiting: int, rework: int, ontime: null, firstpass: null },
        inbox: [ {id,title,event,type,priority,due_date} ... ],
        work:  [ {id,event,type,priority,due_date,status,rev,created_at,assigned_at} ... ],
        events_all: [ {id,title,date,status} ... ],
        events_assigned: [ {id,title,date,status} ... ]
      }
    """
    user = request.user

    def best_date(p):
        if getattr(p, 'event_start_date', None):
            return p.event_start_date
        if getattr(p, 'event_datetime', None):
            try:
                return p.event_datetime.date()
            except Exception:
                return None
        return None

    # Assigned work via CDLAssignment fallback to legacy report_assigned_to
    from emt.models import CDLAssignment as _CDLAssignment
    asg_ids = list(_CDLAssignment.objects.filter(assignee=user).values_list('proposal_id', flat=True))
    legacy_qs = EMTEventProposal.objects.filter(report_assigned_to=user).values_list('id', flat=True)
    proposal_ids = list(set(asg_ids) | set(legacy_qs))
    work_qs = EMTEventProposal.objects.filter(id__in=proposal_ids).select_related('organization')[:200]
    work = []
    due_today = 0
    from datetime import date as _date
    today = _date.today()
    # Also include per-resource assignments (fine-grained tasks)
    from emt.models import CDLTaskAssignment as _Task
    task_qs = _Task.objects.filter(assignee=user).select_related('proposal')
    task_by_proposal = {}
    for t in task_qs:
        d = best_date(t.proposal)
        due_iso = d.isoformat() if d else None
        label = (t.resource_key or '').replace('_',' ').title()
        work.append({
            'id': t.proposal_id,
            'event': t.proposal.event_title,
            'type': t.resource_key or 'task',
            'priority': 'Medium',
            'due_date': due_iso,
            'status': (t.status or 'assigned'),
            'rev': 0,
            'created_at': t.proposal.created_at.isoformat(),
            'assigned_at': t.assigned_at.isoformat() if t.assigned_at else None,
            'assigned_role': label,
            'assigned_by': (t.assigned_by.get_full_name() or t.assigned_by.username) if t.assigned_by else None,
        })
        task_by_proposal.setdefault(t.proposal_id, set()).add(t.resource_key)

    for p in work_qs:
        d = best_date(p)
        due_iso = d.isoformat() if d else None
        if d == today:
            due_today += 1
        # Pull assignment info if present
        _asg = getattr(p, 'cdl_assignment', None)
        # If detailed resource tasks exist for this proposal, skip generic item to avoid duplicates
        if p.id in task_by_proposal:
            continue
        work.append({
            'id': p.id,
            'event': p.event_title,
            'type': 'poster' if getattr(getattr(p,'cdl_support',None),'poster_required',False) else ('certificate' if getattr(getattr(p,'cdl_support',None),'certificates_required',False) else 'coverage'),
            'priority': 'Medium',
            'due_date': due_iso,
            'status': (_asg.status if _asg else 'assigned'),
            'rev': 0,
            'created_at': p.created_at.isoformat(),
            'assigned_at': (_asg.assigned_at.isoformat() if _asg else (p.report_assigned_at.isoformat() if p.report_assigned_at else None)),
            'assigned_role': (_asg.role if _asg else None),
            'assigned_by': ((_asg.assigned_by.get_full_name() or _asg.assigned_by.username) if (_asg and _asg.assigned_by) else None),
        })

    # Inbox: show only items not yet accepted (status == 'assigned')
    inbox = []
    for w in work:
        if (w.get('status') or '').lower() == 'assigned':
            inbox.append({
                'id': w['id'],
                'title': w['event'],
                'event': w['event'],
                'type': w['type'],
                'priority': w['priority'],
                'due_date': w['due_date'],
                'status': 'assigned',
            })

    # Calendar datasets
    events_all_qs = (
        EMTEventProposal.objects.filter(status=EMTEventProposal.Status.FINALIZED)
        .filter(models.Q(event_datetime__isnull=False) | models.Q(event_start_date__isnull=False))
        .select_related('organization')
        .order_by('-updated_at')[:600]
    )
    events_all = []
    for p in events_all_qs:
        d = best_date(p)
        events_all.append({
            'id': p.id,
            'title': p.event_title,
            'date': d.isoformat() if d else None,
            'status': (p.status or '').lower(),
        })

    # Build assigned events list from "work" so we can include role/assigned_by metadata
    events_assigned = []
    for w in work:
        events_assigned.append({
            'id': w['id'],
            'title': w['event'],
            'date': w.get('due_date'),
            'status': (w.get('status') or '').lower(),
            'assigned_role': w.get('assigned_role'),
            'assigned_by': w.get('assigned_by'),
        })

    data = {
        'success': True,
        'stats': {
            'assigned': len(work),
            'due_today': due_today,
            'waiting': 0,
            'rework': 0,
            'ontime': None,
            'firstpass': None,
        },
        'inbox': inbox,
        'work': work,
        'events_all': events_all,
        'events_assigned': events_assigned,
    }
    return JsonResponse(data)


@login_required
@require_http_methods(["POST"])  # /api/cdl/member/accept/
def api_cdl_member_accept(request):
    """Mark a CDL assignment as accepted by the logged-in member.

    Body JSON: { "proposal_id": <int> }
    Transitions CDLAssignment.status from 'assigned' -> 'pending'.
    If no CDLAssignment exists but legacy report_assigned_to matches the user,
    create one for consistency and set to 'pending'.
    """
    import json
    try:
        payload = json.loads(request.body or '{}')
        pid = int(payload.get('proposal_id'))
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid payload'}, status=400)

    from emt.models import EMTEventProposal as _Proposal, CDLAssignment as _CDLAssignment
    try:
        prop = _Proposal.objects.get(id=pid)
    except _Proposal.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Proposal not found'}, status=404)

    # The acting user must be the assignee (via CDLAssignment or legacy field)
    me = request.user
    asg = _CDLAssignment.objects.filter(proposal=prop, assignee=me).first()
    if not asg:
        # Allow legacy fallback if proposal.report_assigned_to == me
        if getattr(prop, 'report_assigned_to_id', None) == me.id:
            asg = _CDLAssignment.objects.create(
                proposal=prop,
                assignee=me,
                assigned_by=None,
                role=None,
                status=_CDLAssignment.Status.ASSIGNED,
            )
        else:
            # NEW: Allow accept if user has any per-resource task for this proposal
            try:
                from emt.models import CDLTaskAssignment as _Task
                has_task = _Task.objects.filter(proposal=prop, assignee=me).exists()
            except Exception:
                has_task = False
            if has_task:
                asg = _CDLAssignment.objects.create(
                    proposal=prop,
                    assignee=me,
                    assigned_by=None,
                    role=None,
                    status=_CDLAssignment.Status.ASSIGNED,
                )
            else:
                return JsonResponse({'success': False, 'error': 'Not assigned to you'}, status=403)

    # Transition to 'pending' when accepted
    asg.status = _CDLAssignment.Status.PENDING
    asg.save(update_fields=['status'])

    return JsonResponse({'success': True, 'status': asg.status})


# ────────────────────────────────────────────────────────────────
#  CDL WORKFLOWS
# ────────────────────────────────────────────────────────────────

def user_can_access_proposal(request, proposal):
    return request.user.is_superuser or proposal.submitted_by == request.user


@login_required
def submit_proposal_cdl(request, proposal_id):
    proposal = get_object_or_404(EventProposal, pk=proposal_id)
    if not user_can_access_proposal(request, proposal):
        return HttpResponseForbidden()

    cdl_req, _ = CDLRequest.objects.get_or_create(proposal=proposal)

    if request.method == "POST":
        form = CDLRequestForm(request.POST, instance=cdl_req)
        if form.is_valid():
            form.save()
            if form.cleaned_data.get("wants_cdl"):
                CDLCommunicationThread.objects.get_or_create(proposal=proposal)
            messages.success(request, "CDL details saved")
            return redirect("proposal_detail", proposal_id=proposal.id)
    else:
        form = CDLRequestForm(instance=cdl_req)

    return render(
        request,
        "cdl/submit_proposal_cdl.html",
        {"form": form, "proposal": proposal},
    )


def run_ai_validation(batch):
    """Simple synchronous validator for certificate entries."""
    status = CertificateBatch.AIStatus.PASSED
    for entry in batch.entries.all():
        errors = []
        if not entry.name.strip():
            errors.append("Name is empty")
        if entry.role not in CertificateEntry.Role.values:
            errors.append("Invalid role")
        if errors:
            entry.ai_valid = False
            entry.ai_errors = ", ".join(errors)
            status = CertificateBatch.AIStatus.FAILED
        else:
            entry.ai_valid = True
            entry.ai_errors = ""
        entry.save()
    batch.ai_check_status = status
    batch.save()


@login_required


@login_required
def cdl_thread(request, proposal_id):
    proposal = get_object_or_404(EventProposal, pk=proposal_id)
    if not user_can_access_proposal(request, proposal) and not (
        request.user.is_superuser
        or request.user.groups.filter(name__in=["CDL_HEAD", "CDL_MEMBER"]).exists()
    ):
        return HttpResponseForbidden()

    thread, _ = CDLCommunicationThread.objects.get_or_create(proposal=proposal)

    if request.method == "POST":
        form = CDLMessageForm(request.POST, request.FILES)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.thread = thread
            msg.author = request.user
            msg.save()
            messages.success(request, "Message posted")
            return redirect("cdl_thread", proposal_id=proposal.id)
    else:
        form = CDLMessageForm()

    return render(
        request,
        "cdl/thread.html",
        {
            "thread": thread,
            "messages": thread.messages.select_related("author"),
            "form": form,
            "proposal": proposal,
        },
    )


# ====================================================================
# Profile API Endpoints
# ====================================================================

@login_required
@require_http_methods(["POST"])
def api_update_profile(request):
    """Update user profile basic information"""
    try:
        data = json.loads(request.body)
        user = request.user
        profile = user.profile
        
        # Update user fields
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'email' in data:
            user.email = data['email']
        user.save()
        
        # Update profile fields
        if 'phone' in data:
            profile.phone = data['phone']
        if 'date_of_birth' in data:
            if data['date_of_birth']:
                profile.date_of_birth = data['date_of_birth']
        if 'bio' in data:
            profile.bio = data['bio']
        if 'emergency_contact' in data:
            profile.emergency_contact = data['emergency_contact']
        profile.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Profile updated successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
def api_update_avatar(request):
    """Update user profile picture"""
    try:
        if 'avatar' not in request.FILES:
            return JsonResponse({
                'success': False,
                'message': 'No file provided'
            }, status=400)
        
        avatar = request.FILES['avatar']
        profile = request.user.profile
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
        if avatar.content_type not in allowed_types:
            return JsonResponse({
                'success': False,
                'message': 'Only JPEG and PNG files are allowed'
            }, status=400)
        
        # Validate file size (max 5MB)
        if avatar.size > 5 * 1024 * 1024:
            return JsonResponse({
                'success': False,
                'message': 'File too large. Maximum size is 5MB'
            }, status=400)
        
        # Delete old avatar if exists
        if profile.profile_picture:
            old_path = profile.profile_picture.path
            if os.path.exists(old_path):
                os.remove(old_path)
        
        # Save new avatar
        profile.profile_picture = avatar
        profile.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Avatar updated successfully',
            'avatar_url': profile.profile_picture.url if profile.profile_picture else None
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@login_required
@require_http_methods(["GET"])
def api_get_user_events(request):
    """Get user's events based on their role"""
    try:
        user = request.user
        events_data = []
        
        # Get events based on user role
        if hasattr(user, 'student'):
            # Student events - events they've registered for or attended
            student = user.student
            events = EventProposal.objects.filter(
                Q(students=student) | Q(created_by=user)
            ).distinct().order_by('-created_at')
            
            for event in events:
                events_data.append({
                    'id': event.id,
                    'title': event.title,
                    'description': event.description,
                    'event_date': event.event_date.isoformat() if event.event_date else None,
                    'status': event.status,
                    'is_creator': event.created_by == user,
                    'type': 'student_event'
                })
        else:
            # Faculty/Staff events - events they've created or are managing
            events = EventProposal.objects.filter(
                created_by=user
            ).order_by('-created_at')
            
            for event in events:
                events_data.append({
                    'id': event.id,
                    'title': event.title,
                    'description': event.description,
                    'event_date': event.event_date.isoformat() if event.event_date else None,
                    'status': event.status,
                    'participants_count': event.students.count(),
                    'type': 'faculty_event'
                })
        
        return JsonResponse({
            'success': True,
            'events': events_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@login_required
@require_http_methods(["GET", "POST", "DELETE"])
def api_manage_achievements(request):
    """Manage user achievements"""
    try:
        user = request.user
        profile = user.profile
        
        if request.method == 'GET':
            # Get achievements
            achievements = profile.achievements if profile.achievements else []
            return JsonResponse({
                'success': True,
                'achievements': achievements
            })
            
        elif request.method == 'POST':
            # Add achievement
            data = json.loads(request.body)
            achievement = {
                'title': data.get('title', ''),
                'description': data.get('description', ''),
                'date': data.get('date', ''),
                'category': data.get('category', 'academic'),
                'id': len(profile.achievements) + 1 if profile.achievements else 1
            }
            
            if not profile.achievements:
                profile.achievements = []
            
            profile.achievements.append(achievement)
            profile.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Achievement added successfully',
                'achievement': achievement
            })
            
        elif request.method == 'DELETE':
            # Delete achievement
            achievement_id = request.GET.get('id')
            if not achievement_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Achievement ID required'
                }, status=400)
            
            try:
                achievement_id = int(achievement_id)
                if profile.achievements:
                    profile.achievements = [
                        ach for ach in profile.achievements 
                        if ach.get('id') != achievement_id
                    ]
                    profile.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Achievement deleted successfully'
                })
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid achievement ID'
                }, status=400)
                
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
def api_update_student_academic(request):
    """Update student academic information"""
    try:
        if not hasattr(request.user, 'student'):
            return JsonResponse({
                'success': False,
                'message': 'Access denied. Student account required.'
            }, status=403)
        
        data = json.loads(request.body)
        student = request.user.student
        
        # Update student fields
        if 'registration_number' in data:
            student.registration_number = data['registration_number']
        if 'current_semester' in data:
            student.current_semester = data['current_semester']
        if 'gpa' in data:
            student.gpa = float(data['gpa']) if data['gpa'] else None
        if 'major' in data:
            student.major = data['major']
        if 'enrollment_year' in data:
            student.enrollment_year = int(data['enrollment_year']) if data['enrollment_year'] else None
        
        student.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Academic information updated successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
def api_update_faculty_professional(request):
    """Update faculty professional information"""
    try:
        # Check if user is faculty/staff using same logic as my_profile
        user = request.user
        roles = RoleAssignment.objects.filter(user=user).select_related('role', 'organization')
        role_lc = [ra.role.name.lower() for ra in roles]
        email = (user.email or "").lower()
        is_student = ('student' in role_lc) or email.endswith('@christuniversity.in')
        
        if is_student:
            return JsonResponse({
                'success': False,
                'message': 'Access denied. Faculty/Staff account required.'
            }, status=403)
        
        data = json.loads(request.body)
        profile = request.user.profile
        
        # Update profile fields for faculty
        if 'department' in data:
            profile.department = data['department']
        if 'position' in data:
            profile.position = data['position']
        if 'office_location' in data:
            profile.office_location = data['office_location']
        if 'office_hours' in data:
            profile.office_hours = data['office_hours']
        if 'research_interests' in data:
            profile.research_interests = data['research_interests']
        
        profile.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Professional information updated successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)
#test
