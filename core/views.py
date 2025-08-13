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
from django.utils import timezone
import json
import logging
logger = logging.getLogger(__name__)
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
)
from emt.models import EventProposal, Student
from django.views.decorators.http import require_GET, require_POST
from .models import ApprovalFlowTemplate, ApprovalFlowConfig
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────
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
    return render(request, "core/login.html")
    if user is not None:
        login(request, user)
        
        # Log the successful login
        logger.info(f"User '{user.username}' logged in successfully.")
        
        return redirect('dashboard')

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

    # ---- role / domain detection ----
    roles = RoleAssignment.objects.filter(user=user).select_related('role', 'organization')
    role_lc = [ra.role.name.lower() for ra in roles]

    if user.is_superuser:
        return redirect('admin_dashboard')

    email = (user.email or "").lower()
    is_student = ('student' in role_lc) or email.endswith('@christuniversity.in')
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

        upcoming_events_count = finalized_events.filter(
            event_datetime__gte=timezone.now()
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
    }

        # --- robust template selection + debug ---
    from django.conf import settings
    from django.template.loader import select_template
    import os

    # quick runtime checks (remove after verifying)
    print("TEMPLATE_DIRS:", settings.TEMPLATES[0]['DIRS'])
    exp1 = os.path.join(settings.BASE_DIR, "templates", "core", "student_dashboard.html")
    exp2 = os.path.join(settings.BASE_DIR, "templates", "student_dashboard.html")
    print("EXPECTS:", exp1, "EXISTS:", os.path.exists(exp1))
    print("EXPECTS:", exp2, "EXISTS:", os.path.exists(exp2))

    candidates = ["core/student_dashboard.html", "student_dashboard.html"] if is_student else ["core/dashboard.html", "dashboard.html"]
    tpl = select_template(candidates)  # picks the first that actually exists
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
def admin_dashboard(request):
    """
    Render the admin dashboard with dynamic analytics from the backend.
    """
    from django.contrib.auth.models import User
    from django.db.models import Q
    from datetime import timedelta

    # Calculate role statistics (manual count for accuracy)
    all_assignments = RoleAssignment.objects.select_related('role', 'user').filter(
        user__is_active=True,
        user__last_login__isnull=False,
    )
    counted_users = {'faculty': set(), 'student': set(), 'hod': set()}
    for assignment in all_assignments:
        role_name = assignment.role.name.lower()
        user_id = assignment.user.id
        if 'faculty' in role_name:
            counted_users['faculty'].add(user_id)
        elif 'student' in role_name:
            counted_users['student'].add(user_id)
        elif 'hod' in role_name or 'head' in role_name:
            counted_users['hod'].add(user_id)
    stats = {
        'students': len(counted_users['student']),
        'faculties': len(counted_users['faculty']),
        'hods': len(counted_users['hod']),
        'centers': Organization.objects.filter(is_active=True).count(),
        'departments': Organization.objects.filter(org_type__name__icontains='department', is_active=True).count(),
        'clubs': Organization.objects.filter(org_type__name__icontains='club', is_active=True).count(),
        'total_proposals': EventProposal.objects.count(),
        'pending_proposals': EventProposal.objects.filter(status__in=['submitted', 'under_review']).count(),
        'approved_proposals': EventProposal.objects.filter(status='approved').count(),
        'rejected_proposals': EventProposal.objects.filter(status='rejected').count(),
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True, last_login__isnull=False).count(),
        'new_users_this_week': User.objects.filter(
            is_active=True,
            last_login__isnull=False,
            date_joined__gte=timezone.now() - timedelta(days=7),
        ).count(),
        'total_reports': Report.objects.count(),
        'database_status': 'Operational',
        'email_status': 'Active',
        'storage_status': '45% Used',
        'last_backup': timezone.now().strftime("%b %d, %Y"),
    }
    # Recent activity feed (proposals and reports)
    recent_activities = []
    recent_proposals = EventProposal.objects.select_related('submitted_by').order_by('-created_at')[:5]
    for proposal in recent_proposals:
        recent_activities.append({
            'type': 'proposal',
            'description': f"New event proposal: {getattr(proposal, 'event_title', getattr(proposal, 'title', 'Untitled Event'))}",
            'user': proposal.submitted_by.get_full_name() if proposal.submitted_by else '',
            'timestamp': proposal.created_at,
            'status': proposal.status
        })
    recent_reports = Report.objects.select_related('submitted_by').order_by('-created_at')[:3]
    for report in recent_reports:
        recent_activities.append({
            'type': 'report',
            'description': f"Report submitted: {report.title}",
            'user': report.submitted_by.get_full_name() if report.submitted_by else 'System',
            'timestamp': report.created_at,
            'status': getattr(report, 'status', '')
        })
    recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activities = recent_activities[:8]
    context = {
        'stats': stats,
        'recent_activities': recent_activities,
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
        roles = OrganizationRole.objects.filter(organization=org).order_by('name')
        assignments = (
            RoleAssignment.objects.filter(organization=org)
            .select_related("user", "role")
            .order_by("user__username")
        )

        context = {
            'selected_organization': org,
            'roles': roles,
            'role_assignments': assignments,
            'step': 'single_org_roles'
        }
        return render(request, "core/admin_role_management.html", context)
    
    else:
        org_type_id = request.GET.get('org_type_id')
        
        if org_type_id:
            # Show UNIQUE roles from this org type (no duplicates)
            org_type = get_object_or_404(OrganizationType, id=org_type_id)
            
            # Get all organizations of this type for the add form
            organizations = Organization.objects.filter(
                org_type=org_type, 
                is_active=True
            ).order_by('name')
            
            # Get UNIQUE role names (deduplicated) from all organizations of this type
            unique_role_names = OrganizationRole.objects.filter(
                organization__org_type=org_type,
                organization__is_active=True
            ).values_list('name', flat=True).distinct().order_by('name')
            
            # For each unique role name, get one representative role object
            unique_roles = []
            for role_name in unique_role_names:
                # Get the first role with this name from this org type
                role = OrganizationRole.objects.filter(
                    organization__org_type=org_type,
                    organization__is_active=True,
                    name=role_name
                ).select_related('organization').first()
                if role:
                    unique_roles.append(role)
            
            context = {
                'selected_org_type': org_type,
                'roles': unique_roles,  # Now deduplicated
                'organizations': organizations,
                'step': 'org_type_roles'
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
    description = request.POST.get("description", "").strip()

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
                # Remove description if not in model
            )
    return redirect(f"{reverse('admin_role_management')}?org_type_id={org.org_type.id}")


@user_passes_test(lambda u: u.is_superuser)
@require_POST
def add_role(request):
    """Add a role by organization or organization type (used by tests)."""
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
        if not OrganizationRole.objects.filter(organization=org, name__iexact=name).exists():
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
    """Delete this role from ALL organizations of the same type"""
    role = get_object_or_404(OrganizationRole, id=role_id)
    org_type = role.organization.org_type
    role_name = role.name
    
    # Delete all roles with this name from all organizations of this type
    deleted_count = OrganizationRole.objects.filter(
        organization__org_type=org_type,
        name__iexact=role_name
    ).delete()[0]
    
    messages.success(request, f"Role '{role_name}' deleted from {deleted_count} {org_type.name}(s).")
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
    users_list = User.objects.select_related('profile').prefetch_related(
        'role_assignments__organization', 
        'role_assignments__role',
        'role_assignments__organization__org_type'
    ).order_by('-date_joined')

    # Filter parameters - support both single and multiple values
    q = request.GET.get('q', '').strip()
    role_ids = request.GET.getlist('role[]') or ([request.GET.get('role')] if request.GET.get('role') else [])
    org_ids = request.GET.getlist('organization[]') or ([request.GET.get('organization')] if request.GET.get('organization') else [])
    org_type_ids = request.GET.getlist('org_type[]') or ([request.GET.get('org_type')] if request.GET.get('org_type') else [])
    status = request.GET.get('status')
    
    # Clean empty values
    role_ids = [r for r in role_ids if r and r.strip()]
    org_ids = [o for o in org_ids if o and o.strip()]
    org_type_ids = [ot for ot in org_type_ids if ot and ot.strip()]
    
    # Apply filters
    if q:
        users_list = users_list.filter(
            Q(email__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(username__icontains=q)
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

    # Pagination
    paginator = Paginator(users_list, 25)
    page_number = request.GET.get('page')
    try:
        users = paginator.page(page_number)
    except PageNotAnInteger:
        users = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages)

    # Filter options data
    all_roles = OrganizationRole.objects.filter(is_active=True)
    if org_ids:
        # Restrict roles to those belonging to the selected organizations
        all_roles = all_roles.filter(organization_id__in=org_ids)
    if role_ids:
        # Ensure currently selected roles remain available in the dropdown
        all_roles = all_roles | OrganizationRole.objects.filter(id__in=role_ids)
    all_roles = all_roles.select_related('organization').order_by('name').distinct()
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
    }
    
    return render(request, "core/admin_user_management.html", context)

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
    from transcript.models import AcademicYear
    import datetime
    import json

    current_year = datetime.datetime.now().year
    academic_year = AcademicYear.objects.first()
    if not academic_year:
        academic_year = AcademicYear.objects.create(year=f"{current_year}-{current_year + 1}")

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
    return render(request, "core/admin_proposal_detail.html", {"proposal": proposal})

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
def admin_academic_year_settings(request):
    from transcript.models import AcademicYear

    academic_year = AcademicYear.objects.first()

    if request.method == "POST":
        year = request.POST.get('year')
        if year and '-' not in year:
            try:
                y = int(year)
                year = f"{y}-{y + 1}"
            except ValueError:
                pass
        start = request.POST.get('start_date') or None
        end = request.POST.get('end_date') or None
        if academic_year:
            academic_year.year = year
            academic_year.start_date = start
            academic_year.end_date = end
            academic_year.save()
        else:
            AcademicYear.objects.create(year=year, start_date=start, end_date=end)
        return redirect('admin_academic_year_settings')

    return render(
        request,
        'core/admin_academic_year_settings.html',
        {
            'academic_year': academic_year,
        },
    )

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
@require_http_methods(["GET", "POST", "PUT", "DELETE"])
def manage_program_outcomes(request, program_id=None):
    """API endpoint for managing Program Outcomes (POs and PSOs)"""
    from .models import Program, ProgramOutcome, ProgramSpecificOutcome
    import json
    
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            program = Program.objects.get(id=data['program_id'])
            outcome_type = data.get('type', '').upper()
            
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
            elif outcome_type == 'PSO':
                outcome = ProgramSpecificOutcome.objects.get(id=data['outcome_id'])
            else:
                return JsonResponse({'success': False, 'error': 'Invalid outcome type'})
                
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
            elif outcome_type == 'PSO':
                outcome = ProgramSpecificOutcome.objects.get(id=data['outcome_id'])
            else:
                return JsonResponse({'success': False, 'error': 'Invalid outcome type'})
                
            outcome.delete()
            return JsonResponse({'success': True})
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

@user_passes_test(lambda u: u.is_superuser)
@require_POST
def create_program_for_organization(request):
    """API endpoint for creating a new program for an organization"""
    from .models import Organization, Program
    import json
    
    try:
        data = json.loads(request.body)
        organization = Organization.objects.get(id=data['organization_id'])
        
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
        program = Program.objects.create(
            name=data.get('program_name', f"{organization.name} Program"),
            organization=organization
        )
        
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
    ApprovalFlowTemplate.objects.filter(organization=org).delete()
    for idx, step in enumerate(steps, 1):
        if not step.get('role_required'):
            continue
        ApprovalFlowTemplate.objects.create(
            organization=org,
            step_order=idx,
            role_required=step['role_required'],
            user_id=step.get('user_id'),
            optional=step.get('optional', False)
        )

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
    ApprovalFlowTemplate.objects.filter(organization_id=org_id).delete()
    return JsonResponse({'success': True})
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
    """Delete a PO or PSO"""
    try:
        from .models import ProgramOutcome, ProgramSpecificOutcome
        
        if outcome_type == 'po':
            outcome = ProgramOutcome.objects.get(id=outcome_id)
        elif outcome_type == 'pso':
            outcome = ProgramSpecificOutcome.objects.get(id=outcome_id)
        else:
            return JsonResponse({'success': False, 'error': 'Invalid outcome type'})
        
        outcome.delete()
        return JsonResponse({'success': True})
        
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
    return render(request, 'core/user_dashboard.html')

@login_required
@require_GET
def api_global_search(request):
    """
    Global search API endpoint for the Central Command Center.
    Searches across Students, Event Proposals, Reports, and Users.
    """
    from django.db.models import Q
    from django.contrib.auth.models import User
    import json
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({
            'success': True,
            'results': {
                'students': [],
                'proposals': [],
                'reports': [],
                'users': []
            }
        })
    try:
        results = {'students': [], 'proposals': [], 'reports': [], 'users': []}
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
import json
import csv
from datetime import datetime, timedelta
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.utils import timezone
from io import StringIO, BytesIO
# xlsxwriter is optional; used only for Excel export
try:
    import xlsxwriter
except ImportError:  # pragma: no cover - optional dependency
    xlsxwriter = None

from itertools import chain
from operator import attrgetter

from .models import (
    Organization, OrganizationType, OrganizationRole, RoleAssignment,
    Profile, Report, Program, ProgramOutcome, 
    ProgramSpecificOutcome, ApprovalFlowTemplate
)
from emt.models import (
    EventProposal as EMTEventProposal, ApprovalStep, EventReport,
    Student, MediaRequest, CDLSupport
)


def is_admin(user):
    """Check if user is admin"""
    return user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'admin')


@login_required
@user_passes_test(is_admin)
def data_export_filter_view(request):
    """Main data export filter page"""
    return render(request, 'core/data_export_filter.html')


@login_required
@user_passes_test(is_admin)
def filter_suggestions_api(request):
    """API endpoint to get filter suggestions"""
    
    # Get dynamic organization types
    org_types = OrganizationType.objects.filter(is_active=True)
    organizations = Organization.objects.filter(is_active=True).select_related('org_type')
    roles = OrganizationRole.objects.filter(is_active=True).select_related('organization')
    
    suggestions = []
    
    # User Profile Filters
    profile_choices = Profile.ROLE_CHOICES
    for choice_value, choice_display in profile_choices:
        suggestions.append({
            'category': 'Users',
            'label': f'{choice_display}s',
            'filter': f'profile_role:{choice_value}',
            'description': f'All users with {choice_display} role'
        })
    
    # Organization Type Filters
    for org_type in org_types:
        suggestions.append({
            'category': 'Organization Types',
            'label': org_type.name,
            'filter': f'organization_type:{org_type.id}',
            'description': f'Organizations of type {org_type.name}'
        })
        # NEW: Events by organization type suggestion
        suggestions.append({
            'category': 'Events by Org Type',
            'label': f'Events – {org_type.name}',
            'filter': f'emt_org_type:{org_type.id}',
            'description': f'All events submitted under {org_type.name} org type'
        })
        # NEW: Reports by organization type suggestion
        suggestions.append({
            'category': 'Reports by Org Type',
            'label': f'Reports – {org_type.name}',
            'filter': f'reports_by_org_type:{org_type.id}',
            'description': f'All reports for organizations of type {org_type.name}'
        })
    
    # Specific Organizations
    for org in organizations:
        suggestions.append({
            'category': f'{org.org_type.name}s',
            'label': org.name,
            'filter': f'organization:{org.id}',
            'description': f'{org.name} ({org.org_type.name})'
        })
        # NEW: Events by organization name suggestion
        suggestions.append({
            'category': 'Events by Org Name',
            'label': f'Events – {org.name}',
            'filter': f'emt_org_name:{org.name}',
            'description': f'All events submitted under organization {org.name}'
        })
        # NEW: Reports by organization name suggestion
        suggestions.append({
            'category': 'Reports by Org Name',
            'label': f'Reports – {org.name}',
            'filter': f'reports_by_org_name:{org.name}',
            'description': f'All reports for organization {org.name}'
        })
    
    # Organization Roles
    for role in roles:
        suggestions.append({
            'category': 'Roles',
            'label': f'{role.name} - {role.organization.name}',
            'filter': f'organization_role:{role.id}',
            'description': f'{role.name} role in {role.organization.name}'
        })
    
    # Event Proposal Status Filters (EMT)
    emt_status_choices = EMTEventProposal.Status.choices
    for choice_value, choice_display in emt_status_choices:
        suggestions.append({
            'category': 'Event Status',
            'label': f'{choice_display} Events',
            'filter': f'emt_proposal_status:{choice_value}',
            'description': f'Events with {choice_display} status'
        })
    
    # Core Event Proposal Status Filters
    core_status_choices = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('returned', 'Returned for Revision'),
    ]
    for choice_value, choice_display in core_status_choices:
        suggestions.append({
            'category': 'Core Event Status',
            'label': f'{choice_display} Proposals',
            'filter': f'core_proposal_status:{choice_value}',
            'description': f'Core proposals with {choice_display} status'
        })
    
    # Report Type Filters (core Report model)
    try:
        report_choices = Report.REPORT_TYPE_CHOICES
        for choice_value, choice_display in report_choices:
            suggestions.append({
                'category': 'Reports',
                'label': f'{choice_display} Reports',
                'filter': f'report_type:{choice_value}',
                'description': f'{choice_display} type reports'
            })
    except Exception:
        # If Report model doesn't have choices or isn't loaded, ignore
        pass
    
    # Report Status Filters
    try:
        report_status_choices = Report.STATUS_CHOICES
        for choice_value, choice_display in report_status_choices:
            suggestions.append({
                'category': 'Report Status',
                'label': f'{choice_display} Reports',
                'filter': f'report_status:{choice_value}',
                'description': f'Reports with {choice_display} status'
            })
    except Exception:
        pass
    
    # Special Filters
    suggestions.extend([
        # Active/Inactive Filters
        {'category': 'Status', 'label': 'Active Organizations', 'filter': 'organization_active:true', 'description': 'Currently active organizations'},
        {'category': 'Status', 'label': 'Inactive Organizations', 'filter': 'organization_active:false', 'description': 'Inactive organizations'},
        {'category': 'Status', 'label': 'Active Roles', 'filter': 'role_active:true', 'description': 'Currently active organization roles'},
        
        # Event Special Filters
        {'category': 'Event Flags', 'label': 'Big Events', 'filter': 'emt_big_event:true', 'description': 'Events marked as big events'},
        {'category': 'Event Flags', 'label': 'Finance Approval Needed', 'filter': 'emt_finance_approval:true', 'description': 'Events requiring finance approval'},
        {'category': 'Event Flags', 'label': 'Report Generated', 'filter': 'emt_report_generated:true', 'description': 'Events with generated reports'},
        
        # User Assignment Filters
        {'category': 'Assignments', 'label': 'Users with Role Assignments', 'filter': 'has_role_assignment:true', 'description': 'Users assigned to organization roles'},
        {'category': 'Assignments', 'label': 'Users without Role Assignments', 'filter': 'has_role_assignment:false', 'description': 'Users not assigned to any organization role'},
        
        # Date Range Filters
        {'category': 'Date Range', 'label': 'This Academic Year', 'filter': 'date_range:academic_year', 'description': 'Data from current academic year'},
        {'category': 'Date Range', 'label': 'Last 30 Days', 'filter': 'date_range:30_days', 'description': 'Data from last 30 days'},
        {'category': 'Date Range', 'label': 'Last 7 Days', 'filter': 'date_range:7_days', 'description': 'Data from last 7 days'},
        {'category': 'Date Range', 'label': 'This Month', 'filter': 'date_range:this_month', 'description': 'Data from current month'},
        {'category': 'Date Range', 'label': 'This Year', 'filter': 'date_range:this_year', 'description': 'Data from current calendar year'},
        
        # Program Filters
        {'category': 'Programs', 'label': 'Programs with Outcomes', 'filter': 'program_has_outcomes:true', 'description': 'Programs with defined outcomes'},
        {'category': 'Programs', 'label': 'Programs with PSOs', 'filter': 'program_has_pso:true', 'description': 'Programs with program-specific outcomes'},
    ])
    
    return JsonResponse(suggestions, safe=False)


@csrf_exempt
@login_required
@user_passes_test(is_admin)
def execute_filter_api(request):
    """API endpoint to execute filters and return results"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        data = json.loads(request.body)
        filters = data.get('filters', [])
        logic = data.get('logic', 'AND')
        
        results = process_filters(filters, logic)
        
        return JsonResponse({
            'results': results,
            'count': len(results)
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def process_filters(filters, logic='AND'):
    """Process filters and return combined results"""
    if not filters:
        return []
    
    all_results = []
    
    for filter_item in filters:
        filter_type = filter_item['type']
        filter_value = filter_item['value']
        
        # Process each filter type
        if filter_type == 'profile_role':
            results = get_users_by_profile_role(filter_value)
        elif filter_type == 'organization_type':
            results = get_users_by_organization_type(filter_value)
        elif filter_type == 'organization':
            results = get_users_by_organization(filter_value)
        elif filter_type == 'organization_role':
            results = get_users_by_organization_role(filter_value)
        elif filter_type == 'emt_proposal_status':
            results = get_emt_proposals_by_status(filter_value)
        elif filter_type == 'core_proposal_status':
            results = get_core_proposals_by_status(filter_value)
        # REPORT HANDLING (NEW unified approach)
        elif filter_type == 'all_reports':
            results = get_all_reports()
        elif filter_type == 'reports_by_org_type':
            try:
                results = get_reports_by_org_type(int(filter_value))
            except Exception:
                results = []
        elif filter_type == 'reports_by_org_name':
            results = get_reports_by_org_name(filter_value)
        elif filter_type == 'report_type':
            # Filter core Report by type and also include EventReports for type 'event' if requested
            results = get_reports_by_type(filter_value)
        elif filter_type == 'report_status':
            results = get_reports_by_status(filter_value)
        elif filter_type == 'report_search':
            # generic free-text search across reports
            results = search_reports_text(filter_value)
        elif filter_type == 'report_generated':
            # backward compatibility: map to emt_report_generated
            results = get_events_with_reports(filter_value == 'true')
        elif filter_type == 'report_id':
            # fetch specific report id (could be core Report or EventReport)
            results = get_report_by_id(filter_value)
        elif filter_type == 'report_organization':
            # filter by organization id for reports
            try:
                org_id = int(filter_value)
                results = get_reports_by_org_id(org_id)
            except Exception:
                results = []
        elif filter_type == 'report_date_range':
            results = get_reports_by_date_range(filter_value)
        elif filter_type == 'report_has_file':
            results = get_reports_with_or_without_file(filter_value == 'true')
        elif filter_type == 'report_proposal_event':
            # filter EventReports by matching proposal title or id
            results = get_event_reports_by_proposal(filter_value)
        elif filter_type == 'report_core_or_event':
            # value "core" or "event" to select only core Reports or only EventReports
            if filter_value == 'core':
                results = get_core_reports_only()
            elif filter_value == 'event':
                results = get_event_reports_only()
            else:
                results = []
        elif filter_type == 'report_generated_by_emt':
            # alias for emt_report_generated
            results = get_events_with_reports(filter_value == 'true')
        elif filter_type == 'report_organization_type_or_name':
            # Accepts either id or name, try int first
            try:
                results = get_reports_by_org_type(int(filter_value))
            except Exception:
                results = get_reports_by_org_name(filter_value)
        elif filter_type == 'report_combined_search':
            # combined search: uses global search but returns only report-like results
            results = [r for r in perform_global_search(filter_value) if r.get('type') in ('report', 'emt_proposal', 'core_proposal')]
        elif filter_type == 'report_custom':
            # placeholder for custom client-side report filters (keeps backward compat)
            results = []
        elif filter_type == 'report_recent':
            # default: last N days where value is N (int)
            try:
                n = int(filter_value)
                results = get_reports_by_date_range(f'{n}_days')
            except Exception:
                results = []
        elif filter_type == 'report_author':
            # find reports by submitted_by username or name
            results = get_reports_by_author(filter_value)
        elif filter_type == 'search':
            results = perform_global_search(filter_value)
        elif filter_type == 'report_from_export':
            # support when export asks specifically for reports
            results = get_all_reports()
        elif filter_type == 'report_summary':
            # placeholder for summarized reports
            results = []
        elif filter_type == 'organization_active':
            results = get_organizations_by_active_status(filter_value == 'true')
        elif filter_type == 'emt_big_event':
            results = get_emt_events_by_big_event(filter_value == 'true')
        elif filter_type == 'emt_finance_approval':
            results = get_emt_events_by_finance_approval(filter_value == 'true')
        elif filter_type == 'has_role_assignment':
            results = get_users_by_role_assignment_status(filter_value == 'true')
        elif filter_type == 'date_range':
            results = get_data_by_date_range(filter_value)
        else:
            results = []
        
        all_results.append(results)
    
    # Combine results based on logic
    if logic == 'OR':
        # Union of all results
        combined_results = []
        seen_ids = set()
        
        for result_set in all_results:
            for item in result_set:
                item_id = f"{item.get('type', '')}_{item.get('id', '')}"
                if item_id not in seen_ids:
                    combined_results.append(item)
                    seen_ids.add(item_id)
        
        return combined_results
    
    else:  # AND logic
        # Intersection of all results
        if not all_results:
            return []
        
        combined_results = all_results[0]
        
        for result_set in all_results[1:]:
            # Find intersection
            result_ids = {f"{item.get('type', '')}_{item.get('id', '')}" for item in result_set}
            combined_results = [
                item for item in combined_results 
                if f"{item.get('type', '')}_{item.get('id', '')}" in result_ids
            ]
        
        return combined_results


# Filter processing functions
def get_users_by_profile_role(role):
    """Get users by profile role"""
    users = User.objects.filter(profile__role=role).select_related('profile')
    return [
        {
            'type': 'user',
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'email': user.email,
            'role': user.profile.role if hasattr(user, 'profile') else 'N/A',
            'date_joined': user.date_joined.strftime('%Y-%m-%d'),
            'is_active': user.is_active
        }
        for user in users
    ]


def get_users_by_organization_type(org_type_id):
    """Get users by organization type"""
    users = User.objects.filter(
        role_assignments__organization__org_type_id=org_type_id
    ).distinct().select_related('profile')
    
    return [
        {
            'type': 'user',
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'email': user.email,
            'role': user.profile.role if hasattr(user, 'profile') else 'N/A',
            'organization_type': user.role_assignments.first().organization.org_type.name if user.role_assignments.exists() else 'N/A',
            'date_joined': user.date_joined.strftime('%Y-%m-%d')
        }
        for user in users
    ]


def get_users_by_organization(org_id):
    """Get users by specific organization"""
    users = User.objects.filter(
        role_assignments__organization_id=org_id
    ).distinct().select_related('profile')
    
    return [
        {
            'type': 'user',
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'email': user.email,
            'role': user.profile.role if hasattr(user, 'profile') else 'N/A',
            'organization': user.role_assignments.first().organization.name if user.role_assignments.exists() else 'N/A',
            'date_joined': user.date_joined.strftime('%Y-%m-%d')
        }
        for user in users
    ]


def get_users_by_organization_role(role_id):
    """Get users by organization role"""
    users = User.objects.filter(
        role_assignments__role_id=role_id
    ).distinct().select_related('profile')
    
    return [
        {
            'type': 'user',
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'email': user.email,
            'profile_role': user.profile.role if hasattr(user, 'profile') else 'N/A',
            'organization_role': user.role_assignments.first().role.name if user.role_assignments.exists() else 'N/A',
            'organization': user.role_assignments.first().organization.name if user.role_assignments.exists() else 'N/A',
            'date_joined': user.date_joined.strftime('%Y-%m-%d')
        }
        for user in users
    ]


def get_emt_proposals_by_status(status):
    """Get EMT event proposals by status"""
    proposals = EMTEventProposal.objects.filter(status=status).select_related('submitted_by', 'organization')
    
    return [
        {
            'type': 'emt_proposal',
            'id': proposal.id,
            'title': proposal.event_title or 'Untitled',
            'status': proposal.get_status_display(),
            'submitted_by': proposal.submitted_by.get_full_name() or proposal.submitted_by.username,
            'organization': proposal.organization.name if proposal.organization else 'N/A',
            'start_date': proposal.event_start_date.strftime('%Y-%m-%d') if proposal.event_start_date else 'N/A',
            'created_at': proposal.created_at.strftime('%Y-%m-%d %H:%M'),
            'needs_finance_approval': proposal.needs_finance_approval,
            'is_big_event': proposal.is_big_event
        }
        for proposal in proposals
    ]


def get_core_proposals_by_status(status):
    """Get core event proposals by status"""
    proposals = EventProposal.objects.filter(status=status).select_related('submitted_by', 'organization')
    
    return [
        {
            'type': 'core_proposal',
            'id': proposal.id,
            'title': getattr(proposal, 'event_title', getattr(proposal, 'title', 'Untitled Event')),
            'status': proposal.get_status_display(),
            'submitted_by': proposal.submitted_by.get_full_name() or proposal.submitted_by.username,
            'organization': proposal.organization.name if proposal.organization else 'N/A',
            'date_submitted': proposal.created_at.strftime('%Y-%m-%d %H:%M'),
            'user_type': getattr(proposal, 'user_type', '')
        }
        for proposal in proposals
    ]


# Note: get_reports_by_type and get_reports_by_status previously existed in your file.
# We'll keep helper functions but make them robust and integrate them into the unified report layer below.


def get_reports_by_type(report_type):
    """
    Return core Reports matching report_type and include EventReports only if report_type == 'event' or similar alias.
    """
    results = []

    # Core Reports filtered by report_type
    core_reports = Report.objects.filter(report_type=report_type).select_related('organization', 'submitted_by')
    for r in core_reports:
        date_field = getattr(r, 'date_submitted', getattr(r, 'created_at', None))
        results.append({
            'type': 'report',  # core report
            'id': r.id,
            'title': r.title,
            'report_type': r.get_report_type_display() if hasattr(r, 'get_report_type_display') else getattr(r, 'report_type', 'N/A'),
            'status': r.get_status_display() if hasattr(r, 'get_status_display') else getattr(r, 'status', 'N/A'),
            'submitted_by': r.submitted_by.get_full_name() if r.submitted_by else 'N/A',
            'organization': r.organization.name if r.organization else 'N/A',
            'date_created': date_field.strftime('%Y-%m-%d %H:%M') if date_field else 'N/A'
        })

    # Optionally include EventReport (generated reports) if caller asked for events via type 'event' or 'generated'
    if report_type in ('event', 'generated', 'emt'):
        gen_reports = EventReport.objects.select_related('proposal', 'proposal__organization', 'proposal__submitted_by').all()
        for gr in gen_reports:
            results.append({
                'type': 'event_report',
                'id': gr.id,
                'title': gr.proposal.event_title if getattr(gr, 'proposal', None) else getattr(gr, 'title', 'Untitled'),
                'report_type': 'Event Report',
                'status': 'Generated',
                'submitted_by': gr.proposal.submitted_by.get_full_name() if getattr(gr, 'proposal', None) and gr.proposal.submitted_by else 'N/A',
                'organization': gr.proposal.organization.name if getattr(gr, 'proposal', None) and gr.proposal.organization else 'N/A',
                'date_created': gr.created_at.strftime('%Y-%m-%d %H:%M') if getattr(gr, 'created_at', None) else 'N/A'
            })

    return results


def get_reports_by_status(status):
    """Return core Reports filtered by status (EventReports are generated and may not have status)."""
    results = []
    core_reports = Report.objects.filter(status=status).select_related('organization', 'submitted_by')
    for r in core_reports:
        date_field = getattr(r, 'date_submitted', getattr(r, 'created_at', None))
        results.append({
            'type': 'report',
            'id': r.id,
            'title': r.title,
            'report_type': r.get_report_type_display() if hasattr(r, 'get_report_type_display') else getattr(r, 'report_type', 'N/A'),
            'status': r.get_status_display() if hasattr(r, 'get_status_display') else getattr(r, 'status', 'N/A'),
            'submitted_by': r.submitted_by.get_full_name() if r.submitted_by else 'N/A',
            'organization': r.organization.name if r.organization else 'N/A',
            'date_created': date_field.strftime('%Y-%m-%d %H:%M') if date_field else 'N/A'
        })
    # EventReport doesn't have status field in your model; skip including them here.
    return results


def get_organizations_by_active_status(is_active):
    """Get organizations by active status"""
    organizations = Organization.objects.filter(is_active=is_active).select_related('org_type')
    
    return [
        {
            'type': 'organization',
            'id': org.id,
            'name': org.name,
            'org_type': org.org_type.name,
            'is_active': org.is_active,
            'parent': org.parent.name if org.parent else 'N/A'
        }
        for org in organizations
    ]


def get_emt_events_by_big_event(is_big):
    """Get EMT events by big event flag"""
    proposals = EMTEventProposal.objects.filter(is_big_event=is_big).select_related('submitted_by', 'organization')
    
    return [
        {
            'type': 'emt_proposal',
            'id': proposal.id,
            'title': proposal.event_title or 'Untitled',
            'status': proposal.get_status_display(),
            'submitted_by': proposal.submitted_by.get_full_name() or proposal.submitted_by.username,
            'organization': proposal.organization.name if proposal.organization else 'N/A',
            'is_big_event': proposal.is_big_event,
            'needs_finance_approval': proposal.needs_finance_approval,
            'created_at': proposal.created_at.strftime('%Y-%m-%d %H:%M')
        }
        for proposal in proposals
    ]


def get_emt_events_by_finance_approval(needs_approval):
    """Get EMT events by finance approval requirement"""
    proposals = EMTEventProposal.objects.filter(needs_finance_approval=needs_approval).select_related('submitted_by', 'organization')
    
    return [
        {
            'type': 'emt_proposal',
            'id': proposal.id,
            'title': proposal.event_title or 'Untitled',
            'status': proposal.get_status_display(),
            'submitted_by': proposal.submitted_by.get_full_name() or proposal.submitted_by.username,
            'organization': proposal.organization.name if proposal.organization else 'N/A',
            'needs_finance_approval': proposal.needs_finance_approval,
            'is_big_event': proposal.is_big_event,
            'created_at': proposal.created_at.strftime('%Y-%m-%d %H:%M')
        }
        for proposal in proposals
    ]


def get_users_by_role_assignment_status(has_assignment):
    """Get users by role assignment status"""
    if has_assignment:
        users = User.objects.filter(role_assignments__isnull=False).distinct().select_related('profile')
    else:
        users = User.objects.filter(role_assignments__isnull=True).select_related('profile')
    
    return [
        {
            'type': 'user',
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'email': user.email,
            'role': user.profile.role if hasattr(user, 'profile') else 'N/A',
            'has_role_assignment': user.role_assignments.exists(),
            'date_joined': user.date_joined.strftime('%Y-%m-%d')
        }
        for user in users
    ]


def get_data_by_date_range(date_range):
    """Get data by date range"""
    today = timezone.now().date()
    
    if date_range == '7_days' or date_range == '7':
        start_date = today - timedelta(days=7)
    elif date_range == '30_days' or date_range == '30':
        start_date = today - timedelta(days=30)
    elif date_range == 'this_month':
        start_date = today.replace(day=1)
    elif date_range == 'this_year':
        start_date = today.replace(month=1, day=1)
    elif date_range == 'academic_year':
        # Assuming academic year starts in June
        if today.month >= 6:
            start_date = today.replace(month=6, day=1)
        else:
            start_date = today.replace(year=today.year-1, month=6, day=1)
    elif isinstance(date_range, str) and date_range.endswith('_days'):
        try:
            n = int(date_range.split('_')[0])
            start_date = today - timedelta(days=n)
        except Exception:
            start_date = today - timedelta(days=30)
    else:
        start_date = today - timedelta(days=30)  # Default to 30 days
    
    # Get various data types within date range
    results = []
    
    # EMT Proposals
    emt_proposals = EMTEventProposal.objects.filter(
        created_at__date__gte=start_date
    ).select_related('submitted_by', 'organization')
    
    for proposal in emt_proposals:
        results.append({
            'type': 'emt_proposal',
            'id': proposal.id,
            'title': proposal.event_title or 'Untitled',
            'status': proposal.get_status_display(),
            'submitted_by': proposal.submitted_by.get_full_name() or proposal.submitted_by.username,
            'organization': proposal.organization.name if proposal.organization else 'N/A',
            'created_at': proposal.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    # Core Proposals
    core_proposals = EventProposal.objects.filter(
        created_at__date__gte=start_date
    ).select_related('submitted_by', 'organization')
    
    for proposal in core_proposals:
        results.append({
            'type': 'core_proposal',
            'id': proposal.id,
            'title': getattr(proposal, 'event_title', getattr(proposal, 'title', 'Untitled Event')),
            'status': proposal.get_status_display(),
            'submitted_by': proposal.submitted_by.get_full_name() or proposal.submitted_by.username,
            'organization': proposal.organization.name if proposal.organization else 'N/A',
            'date_submitted': proposal.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    # Reports - Use appropriate date field
    try:
        # Try to determine the correct date field for Report model
        report_date_field = 'date_submitted'
        # Check if the field exists by attempting a simple query
        Report.objects.filter(**{f'{report_date_field}__isnull': False}).exists()
    except:
        try:
            report_date_field = 'created_at'
            Report.objects.filter(**{f'{report_date_field}__isnull': False}).exists()
        except:
            report_date_field = None
    
    if report_date_field:
        reports = Report.objects.filter(
            **{f'{report_date_field}__date__gte': start_date}
        ).select_related('submitted_by', 'organization')
        
        for report in reports:
            date_value = getattr(report, report_date_field, None)
            results.append({
                'type': 'report',
                'id': report.id,
                'title': report.title,
                'report_type': report.get_report_type_display(),
                'status': report.get_status_display(),
                'submitted_by': report.submitted_by.get_full_name() if report.submitted_by else 'N/A',
                'organization': report.organization.name if report.organization else 'N/A',
                'date_created': date_value.strftime('%Y-%m-%d %H:%M') if date_value else 'N/A'
            })
    
    # New Users
    new_users = User.objects.filter(
        date_joined__date__gte=start_date
    ).select_related('profile')
    
    for user in new_users:
        results.append({
            'type': 'user',
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'email': user.email,
            'role': user.profile.role if hasattr(user, 'profile') else 'N/A',
            'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M')
        })
    
    return results


def perform_global_search(query):
    """Perform global search across multiple models"""
    results = []
    query = query.lower()
    
    # Search Users
    users = User.objects.filter(
        Q(username__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query)
    ).select_related('profile')[:20]
    
    for user in users:
        results.append({
            'type': 'user',
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'email': user.email,
            'role': user.profile.role if hasattr(user, 'profile') else 'N/A',
            'date_joined': user.date_joined.strftime('%Y-%m-%d')
        })
    
    # Search Organizations
    organizations = Organization.objects.filter(
        name__icontains=query
    ).select_related('org_type')[:20]
    
    for org in organizations:
        results.append({
            'type': 'organization',
            'id': org.id,
            'name': org.name,
            'org_type': org.org_type.name,
            'is_active': org.is_active
        })
    
    # Search EMT Proposals
    emt_proposals = EMTEventProposal.objects.filter(
        event_title__icontains=query
    ).select_related('submitted_by', 'organization')[:20]
    
    for proposal in emt_proposals:
        results.append({
            'type': 'emt_proposal',
            'id': proposal.id,
            'title': proposal.event_title or 'Untitled',
            'status': proposal.get_status_display(),
            'submitted_by': proposal.submitted_by.get_full_name() or proposal.submitted_by.username,
            'organization': proposal.organization.name if proposal.organization else 'N/A',
            'created_at': proposal.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    # Search Core Proposals
    core_proposals = EventProposal.objects.filter(
        title__icontains=query
    ).select_related('submitted_by', 'organization')[:20]
    
    for proposal in core_proposals:
        results.append({
            'type': 'core_proposal',
            'id': proposal.id,
            'title': getattr(proposal, 'event_title', getattr(proposal, 'title', 'Untitled Event')),
            'status': proposal.get_status_display(),
            'submitted_by': proposal.submitted_by.get_full_name() or proposal.submitted_by.username,
            'organization': proposal.organization.name if proposal.organization else 'N/A',
            'date_submitted': proposal.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    # Search Reports
    reports = Report.objects.filter(
        title__icontains=query
    ).select_related('submitted_by', 'organization')[:20]
    
    for report in reports:
        # Get the appropriate date field
        date_field = getattr(report, 'date_submitted', getattr(report, 'created_at', None))
        results.append({
            'type': 'report',
            'id': report.id,
            'title': report.title,
            'report_type': report.get_report_type_display(),
            'status': report.get_status_display(),
            'submitted_by': report.submitted_by.get_full_name() if report.submitted_by else 'N/A',
            'organization': report.organization.name if report.organization else 'N/A',
            'date_created': date_field.strftime('%Y-%m-%d %H:%M') if date_field else 'N/A'
        })
    
    return results


# ────────────────────────────────────────────────
# NEW: Unified report helpers (submitted core Reports + EMT EventReports)
# ────────────────────────────────────────────────

def _core_report_to_dict(r):
    date_field = getattr(r, 'date_submitted', getattr(r, 'created_at', None))
    return {
        'type': 'report',
        'id': r.id,
        'title': r.title,
        'report_type': r.get_report_type_display() if hasattr(r, 'get_report_type_display') else getattr(r, 'report_type', 'N/A'),
        'status': r.get_status_display() if hasattr(r, 'get_status_display') else getattr(r, 'status', 'N/A'),
        'submitted_by': r.submitted_by.get_full_name() if r.submitted_by else 'N/A',
        'organization': r.organization.name if r.organization else 'N/A',
        'created_at': date_field.strftime('%Y-%m-%d %H:%M') if date_field else 'N/A'
    }


def _event_report_to_dict(er):
    # EventReport linked to proposal
    title = er.proposal.event_title if getattr(er, 'proposal', None) and getattr(er.proposal, 'event_title', None) else getattr(er, 'title', 'Untitled')
    submitted_by = er.proposal.submitted_by.get_full_name() if getattr(er, 'proposal', None) and getattr(er.proposal, 'submitted_by', None) else 'N/A'
    org_name = er.proposal.organization.name if getattr(er, 'proposal', None) and getattr(er.proposal.organization, 'name', None) else 'N/A'
    return {
        'type': 'event_report',
        'id': er.id,
        'title': title,
        'report_type': 'Event Report',
        'status': 'Generated',
        'submitted_by': submitted_by,
        'organization': org_name,
        'created_at': er.created_at.strftime('%Y-%m-%d %H:%M') if getattr(er, 'created_at', None) else 'N/A'
    }


def get_all_reports():
    """Return all core Reports and EMT-generated EventReports combined, newest first."""
    core_qs = Report.objects.select_related('organization', 'submitted_by').all()
    event_qs = EventReport.objects.select_related('proposal', 'proposal__organization', 'proposal__submitted_by').all()

    combined = [ _core_report_to_dict(r) for r in core_qs ] + [ _event_report_to_dict(e) for e in event_qs ]
    # Sort by created_at descending (string dates parseable in format)
    combined.sort(key=lambda x: x.get('created_at') or '', reverse=True)
    return combined


def get_reports_by_org_type(org_type_id):
    """Return combined reports where the organization (core) or proposal.organization (event) has org_type_id."""
    core_qs = Report.objects.filter(organization__org_type_id=org_type_id).select_related('organization', 'submitted_by')
    event_qs = EventReport.objects.filter(proposal__organization__org_type_id=org_type_id).select_related('proposal', 'proposal__organization', 'proposal__submitted_by')

    combined = [ _core_report_to_dict(r) for r in core_qs ] + [ _event_report_to_dict(e) for e in event_qs ]
    combined.sort(key=lambda x: x.get('created_at') or '', reverse=True)
    return combined


def get_reports_by_org_name(name_query):
    """Return combined reports where organization name contains name_query (case-insensitive)."""
    core_qs = Report.objects.filter(organization__name__icontains=name_query).select_related('organization', 'submitted_by')
    event_qs = EventReport.objects.filter(proposal__organization__name__icontains=name_query).select_related('proposal', 'proposal__organization', 'proposal__submitted_by')

    combined = [ _core_report_to_dict(r) for r in core_qs ] + [ _event_report_to_dict(e) for e in event_qs ]
    combined.sort(key=lambda x: x.get('created_at') or '', reverse=True)
    return combined


def get_report_by_id(id_value):
    """Fetch a single report by id; check core Report first, then EventReport."""
    results = []
    try:
        rid = int(id_value)
    except Exception:
        rid = None

    if rid:
        core = Report.objects.filter(id=rid).select_related('organization', 'submitted_by').first()
        if core:
            results.append(_core_report_to_dict(core))
            return results

        ev = EventReport.objects.filter(id=rid).select_related('proposal', 'proposal__organization', 'proposal__submitted_by').first()
        if ev:
            results.append(_event_report_to_dict(ev))
            return results

    return results


def get_reports_by_org_id(org_id):
    """Get reports by organization id (core reports) and proposal.organization (event reports)."""
    core_qs = Report.objects.filter(organization_id=org_id).select_related('organization', 'submitted_by')
    event_qs = EventReport.objects.filter(proposal__organization_id=org_id).select_related('proposal', 'proposal__organization', 'proposal__submitted_by')
    combined = [ _core_report_to_dict(r) for r in core_qs ] + [ _event_report_to_dict(e) for e in event_qs ]
    combined.sort(key=lambda x: x.get('created_at') or '', reverse=True)
    return combined


def get_reports_by_date_range(date_range):
    """Get reports within a date range. date_range can be '7_days', '30_days', 'this_month', etc."""
    today = timezone.now().date()
    if date_range == '7_days':
        start_date = today - timedelta(days=7)
    elif date_range == '30_days':
        start_date = today - timedelta(days=30)
    elif date_range == 'this_month':
        start_date = today.replace(day=1)
    elif date_range == 'this_year':
        start_date = today.replace(month=1, day=1)
    elif isinstance(date_range, str) and date_range.endswith('_days'):
        try:
            n = int(date_range.split('_')[0])
            start_date = today - timedelta(days=n)
        except Exception:
            start_date = today - timedelta(days=30)
    else:
        start_date = today - timedelta(days=30)

    # core reports
    core_qs = Report.objects.filter(created_at__date__gte=start_date).select_related('organization', 'submitted_by')
    # event reports
    event_qs = EventReport.objects.filter(created_at__date__gte=start_date).select_related('proposal', 'proposal__organization', 'proposal__submitted_by')
    combined = [ _core_report_to_dict(r) for r in core_qs ] + [ _event_report_to_dict(e) for e in event_qs ]
    combined.sort(key=lambda x: x.get('created_at') or '', reverse=True)
    return combined


def get_reports_with_or_without_file(has_file):
    """Return core Reports that have file or not, and include EventReports always (they may have no file field)."""
    core_qs = Report.objects.filter(file__isnull=not has_file) if has_file else Report.objects.filter(file__isnull=True)
    core_qs = core_qs.select_related('organization', 'submitted_by')
    event_qs = EventReport.objects.select_related('proposal', 'proposal__organization', 'proposal__submitted_by').all()
    combined = [ _core_report_to_dict(r) for r in core_qs ] + [ _event_report_to_dict(e) for e in event_qs ]
    combined.sort(key=lambda x: x.get('created_at') or '', reverse=True)
    return combined


def get_event_reports_by_proposal(query):
    """Find EventReports by proposal title or id."""
    results = []
    try:
        pid = int(query)
    except Exception:
        pid = None

    if pid:
        event_qs = EventReport.objects.filter(proposal_id=pid).select_related('proposal', 'proposal__organization', 'proposal__submitted_by')
    else:
        event_qs = EventReport.objects.filter(proposal__event_title__icontains=query).select_related('proposal', 'proposal__organization', 'proposal__submitted_by')
    results = [ _event_report_to_dict(e) for e in event_qs ]
    return results


def get_core_reports_only():
    qs = Report.objects.select_related('organization', 'submitted_by').all()
    return [ _core_report_to_dict(r) for r in qs ]


def get_event_reports_only():
    qs = EventReport.objects.select_related('proposal', 'proposal__organization', 'proposal__submitted_by').all()
    return [ _event_report_to_dict(e) for e in qs ]


def search_reports_text(text_query):
    """Free-text search across core Report title and EventReport proposal title."""
    results = []
    core_qs = Report.objects.filter(title__icontains=text_query).select_related('organization', 'submitted_by')
    event_qs = EventReport.objects.filter(proposal__event_title__icontains=text_query).select_related('proposal', 'proposal__organization', 'proposal__submitted_by')
    results = [ _core_report_to_dict(r) for r in core_qs ] + [ _event_report_to_dict(e) for e in event_qs ]
    results.sort(key=lambda x: x.get('created_at') or '', reverse=True)
    return results


def get_reports_by_author(author_query):
    """Return reports submitted by a user matching username or name or id."""
    results = []
    # try username or name
    users = User.objects.filter(Q(username__icontains=author_query) | Q(first_name__icontains=author_query) | Q(last_name__icontains=author_query))
    if users.exists():
        core_qs = Report.objects.filter(submitted_by__in=users).select_related('organization', 'submitted_by')
        event_qs = EventReport.objects.filter(proposal__submitted_by__in=users).select_related('proposal', 'proposal__organization', 'proposal__submitted_by')
        results = [ _core_report_to_dict(r) for r in core_qs ] + [ _event_report_to_dict(e) for e in event_qs ]
    else:
        # fallback: maybe author_query is user id
        try:
            uid = int(author_query)
            core_qs = Report.objects.filter(submitted_by_id=uid).select_related('organization', 'submitted_by')
            event_qs = EventReport.objects.filter(proposal__submitted_by_id=uid).select_related('proposal', 'proposal__organization', 'proposal__submitted_by')
            results = [ _core_report_to_dict(r) for r in core_qs ] + [ _event_report_to_dict(e) for e in event_qs ]
        except Exception:
            results = []
    results.sort(key=lambda x: x.get('created_at') or '', reverse=True)
    return results


# Additional helper functions for advanced filtering (unchanged)
def get_programs_with_outcomes(has_outcomes):
    """Get programs based on whether they have outcomes"""
    if has_outcomes:
        programs = Program.objects.filter(programoutcome__isnull=False).distinct()
    else:
        programs = Program.objects.filter(programoutcome__isnull=True)
    
    return [
        {
            'type': 'program',
            'id': program.id,
            'name': program.name,
            'code': program.code if hasattr(program, 'code') else 'N/A',
            'has_outcomes': program.programoutcome_set.exists()
        }
        for program in programs
    ]


def get_programs_with_pso(has_pso):
    """Get programs based on whether they have PSOs"""
    if has_pso:
        programs = Program.objects.filter(programspecificoutcome__isnull=False).distinct()
    else:
        programs = Program.objects.filter(programspecificoutcome__isnull=True)
    
    return [
        {
            'type': 'program',
            'id': program.id,
            'name': program.name,
            'code': program.code if hasattr(program, 'code') else 'N/A',
            'has_pso': program.programspecificoutcome_set.exists()
        }
        for program in programs
    ]


def get_events_with_reports(has_reports):
    """Get events based on whether they have reports generated"""
    if has_reports:
        # Get EMT events that have reports
        emt_proposals = EMTEventProposal.objects.filter(
            eventreport__isnull=False
        ).distinct().select_related('submitted_by', 'organization')
    else:
        # Get EMT events without reports
        emt_proposals = EMTEventProposal.objects.filter(
            eventreport__isnull=True
        ).select_related('submitted_by', 'organization')
    
    return [
        {
            'type': 'emt_proposal',
            'id': proposal.id,
            'title': proposal.event_title or 'Untitled',
            'status': proposal.get_status_display(),
            'submitted_by': proposal.submitted_by.get_full_name() or proposal.submitted_by.username,
            'organization': proposal.organization.name if proposal.organization else 'N/A',
            'has_report': hasattr(proposal, 'eventreport'),
            'created_at': proposal.created_at.strftime('%Y-%m-%d %H:%M')
        }
        for proposal in emt_proposals
    ]


# Update process_filters function to include new report filter types: (This is the extended processor)
def process_filters_extended(filters, logic='AND'):
    """Extended process_filters function with additional filter types"""
    if not filters:
        return []
    
    all_results = []
    
    for filter_item in filters:
        filter_type = filter_item['type']
        filter_value = filter_item['value']
        
        # Process each filter type (existing filters)
        if filter_type == 'profile_role':
            results = get_users_by_profile_role(filter_value)
        elif filter_type == 'organization_type':
            results = get_users_by_organization_type(filter_value)
        elif filter_type == 'organization':
            results = get_users_by_organization(filter_value)
        elif filter_type == 'organization_role':
            results = get_users_by_organization_role(filter_value)
        elif filter_type == 'emt_proposal_status':
            results = get_emt_proposals_by_status(filter_value)
        elif filter_type == 'core_proposal_status':
            results = get_core_proposals_by_status(filter_value)
        # Reports: use unified handlers (replacing older broken sections)
        elif filter_type == 'all_reports':
            results = get_all_reports()
        elif filter_type == 'reports_by_org_type':
            try:
                results = get_reports_by_org_type(int(filter_value))
            except Exception:
                results = []
        elif filter_type == 'reports_by_org_name':
            results = get_reports_by_org_name(filter_value)
        elif filter_type == 'report_type':
            results = get_reports_by_type(filter_value)
        elif filter_type == 'report_status':
            results = get_reports_by_status(filter_value)
        elif filter_type == 'report_search':
            results = search_reports_text(filter_value)
        elif filter_type == 'report_date_range':
            results = get_reports_by_date_range(filter_value)
        elif filter_type == 'report_author':
            results = get_reports_by_author(filter_value)
        # existing non-report filters preserved
        elif filter_type == 'report_generated':
            results = get_events_with_reports(filter_value == 'true')
        elif filter_type == 'report_proposal_event':
            results = get_event_reports_by_proposal(filter_value)
        elif filter_type == 'report_core_or_event':
            if filter_value == 'core':
                results = get_core_reports_only()
            elif filter_value == 'event':
                results = get_event_reports_only()
            else:
                results = []
        elif filter_type == 'report_combined_search':
            results = [r for r in perform_global_search(filter_value) if r.get('type') in ('report', 'event_report', 'emt_proposal', 'core_proposal')]
        elif filter_type == 'program_has_outcomes':
            results = get_programs_with_outcomes(filter_value == 'true')
        elif filter_type == 'program_has_pso':
            results = get_programs_with_pso(filter_value == 'true')
        elif filter_type == 'emt_report_generated':
            results = get_events_with_reports(filter_value == 'true')
        elif filter_type == 'organization_active':
            results = get_organizations_by_active_status(filter_value == 'true')
        elif filter_type == 'emt_big_event':
            results = get_emt_events_by_big_event(filter_value == 'true')
        elif filter_type == 'emt_finance_approval':
            results = get_emt_events_by_finance_approval(filter_value == 'true')
        elif filter_type == 'has_role_assignment':
            results = get_users_by_role_assignment_status(filter_value == 'true')
        elif filter_type == 'date_range':
            results = get_data_by_date_range(filter_value)
        elif filter_type == 'search':
            results = perform_global_search(filter_value)
        else:
            results = []
        
        all_results.append(results)
    

    # Combine results based on logic (same as before)
    if logic == 'OR':
        combined_results = []
        seen_ids = set()
        
        for result_set in all_results:
            for item in result_set:
                item_id = f"{item.get('type', '')}_{item.get('id', '')}"
                if item_id not in seen_ids:
                    combined_results.append(item)
                    seen_ids.add(item_id)
        
        return combined_results
    
    else:  # AND logic
        if not all_results:
            return []
        
        combined_results = all_results[0]
        
        for result_set in all_results[1:]:
            result_ids = {f"{item.get('type', '')}_{item.get('id', '')}" for item in result_set}
            combined_results = [
                item for item in combined_results 
                if f"{item.get('type', '')}_{item.get('id', '')}" in result_ids
            ]
        
        return combined_results
@csrf_exempt
@login_required
@user_passes_test(is_admin)
def export_data_csv(request):
    """Export filtered data as CSV"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        data = json.loads(request.body)
        filters = data.get('filters', [])
        logic = data.get('logic', 'AND')
        
        results = process_filters(filters, logic)
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        if not results:
            response.write('No data found')
            return response
        
        # Get all unique field names
        fieldnames = set()
        for item in results:
            fieldnames.update(item.keys())
        fieldnames = sorted(list(fieldnames))
        
        writer = csv.DictWriter(response, fieldnames=fieldnames)
        writer.writeheader()
        
        for item in results:
            # Ensure all fields exist in the row
            row = {field: item.get(field, '') for field in fieldnames}
            writer.writerow(row)
        
        return response
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
@user_passes_test(is_admin)
def export_data_excel(request):
    """Export filtered data as Excel"""
    if xlsxwriter is None:
        return JsonResponse({'error': 'XLSX export not available'}, status=501)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        data = json.loads(request.body)
        filters = data.get('filters', [])
        logic = data.get('logic', 'AND')
        
        results = process_filters(filters, logic)
        
        # Create Excel file in memory
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        if not results:
            worksheet = workbook.add_worksheet('No Data')
            worksheet.write('A1', 'No data found for the selected filters')
            workbook.close()
            output.seek(0)
            
            response = HttpResponse(
                output.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
            return response
        
        # Group results by type
        grouped_results = {}
        for item in results:
            item_type = item.get('type', 'Unknown')
            if item_type not in grouped_results:
                grouped_results[item_type] = []
            grouped_results[item_type].append(item)
        
        # Create worksheets for each data type
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D7E4BC',
            'border': 1
        })
        
        cell_format = workbook.add_format({'border': 1})
        
        for data_type, items in grouped_results.items():
            worksheet_name = data_type.replace('_', ' ').title()[:31]  # Excel sheet name limit
            worksheet = workbook.add_worksheet(worksheet_name)
            
            if not items:
                continue
            
            # Get all unique field names for this type
            fieldnames = set()
            for item in items:
                fieldnames.update(item.keys())
            fieldnames = sorted([f for f in fieldnames if f != 'type'])
            
            # Write headers
            for col, header in enumerate(fieldnames):
                worksheet.write(0, col, header.replace('_', ' ').title(), header_format)
                worksheet.set_column(col, col, 15)  # Set column width
            
            # Write data
            for row, item in enumerate(items, start=1):
                for col, field in enumerate(fieldnames):
                    value = item.get(field, '')
                    worksheet.write(row, col, str(value), cell_format)
        
        # Create summary worksheet
        summary_worksheet = workbook.add_worksheet('Summary')
        summary_worksheet.write('A1', 'Export Summary', header_format)
        summary_worksheet.write('A3', 'Generated:', cell_format)
        summary_worksheet.write('B3', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cell_format)
        summary_worksheet.write('A4', 'Total Records:', cell_format)
        summary_worksheet.write('B4', len(results), cell_format)
        summary_worksheet.write('A5', 'Filter Logic:', cell_format)
        summary_worksheet.write('B5', logic, cell_format)
        
        row = 7
        summary_worksheet.write(f'A{row}', 'Applied Filters:', header_format)
        row += 1
        
        for filter_item in filters:
            summary_worksheet.write(f'A{row}', f"• {filter_item.get('label', 'Unknown Filter')}", cell_format)
            row += 1
        
        row += 1
        summary_worksheet.write(f'A{row}', 'Data Types:', header_format)
        row += 1
        
        for data_type, items in grouped_results.items():
            summary_worksheet.write(f'A{row}', f"• {data_type.replace('_', ' ').title()}: {len(items)} records", cell_format)
            row += 1
        
        # Set column widths for summary
        summary_worksheet.set_column(0, 0, 20)
        summary_worksheet.set_column(1, 1, 30)
        
        workbook.close()
        output.seek(0)
        
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        
        return response
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ---------------------------------------------
#           Switch View (Admin)
# ---------------------------------------------

def is_admin(user):
    """Check if user is admin or superuser"""
    return user.is_staff or user.is_superuser

@login_required
def stop_impersonation(request):
    """Stop impersonating and return to original user"""
    if 'impersonate_user_id' in request.session:
        del request.session['impersonate_user_id']
        if 'original_user_id' in request.session:
            del request.session['original_user_id']
        messages.success(request, 'Stopped impersonation')
    
    return redirect('admin_dashboard') 

@login_required
@user_passes_test(is_admin)
def get_recent_users_api(request):
    """Get recently switched users"""
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

    
def is_admin(user):
    """Check if user is admin or superuser"""
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(is_admin)
def switch_user_view(request):
    """Display the switch user interface"""
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
@user_passes_test(is_admin)
def search_users_api(request):
    """API endpoint for quick user search"""
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
@user_passes_test(is_admin)
@require_POST
def impersonate_user(request):
    """Start impersonating a user"""
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

    return JsonResponse({'suggestions': suggestions})

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

@login_required
@require_http_methods(["GET"])
def api_program_outcomes(request, program_id):
    """API endpoint to get outcomes for a program"""
    try:
        outcome_type = request.GET.get('type', '').upper()
        
        if outcome_type == 'PO':
            outcomes = ProgramOutcome.objects.filter(program_id=program_id).values(
                'id', 'description'
            )
        elif outcome_type == 'PSO':
            outcomes = ProgramSpecificOutcome.objects.filter(program_id=program_id).values(
                'id', 'description'
            )
        else:
            return JsonResponse({'error': 'Invalid outcome type'}, status=400)
        
        return JsonResponse(list(outcomes), safe=False)
    
    except Exception as e:
        logger.error(f"Error fetching {outcome_type}s for program {program_id}: {str(e)}")
        return JsonResponse({'error': f'Failed to fetch {outcome_type}s'}, status=500)

def is_superuser(u):
    return u.is_superuser


@login_required
@user_passes_test(is_superuser)
def class_rosters(request, org_id):
    org = get_object_or_404(Organization, pk=org_id)
    year = request.GET.get("year") or request.session.get("active_year")

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
    year = request.GET.get("year") or request.session.get("active_year")
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
    """Get faculty users available for assignment to an organization - STRICT FACULTY ONLY"""
    try:
        from .models import Organization, RoleAssignment
        
        organization = Organization.objects.get(id=org_id)
        search_query = request.GET.get('search', '').strip()
        
        # Get all active users with Faculty role assignments, similar to admin_user_management
        faculty_users = User.objects.select_related('profile').prefetch_related(
            'role_assignments__organization', 
            'role_assignments__role',
            'role_assignments__organization__org_type'
        ).filter(
            is_active=True,
            role_assignments__role__name__iexact='Faculty'  # STRICT: Only Faculty role
        )
        
        # Filter by organization hierarchy (current org or parent)
        org_filter = Q(role_assignments__organization=organization)
        if organization.parent:
            org_filter |= Q(role_assignments__organization=organization.parent)
        
        faculty_users = faculty_users.filter(org_filter).distinct()
        
        # Apply search filter if provided (search by name, username, email)
        if search_query:
            search_filter = (
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query)
            )
            faculty_users = faculty_users.filter(search_filter).distinct()
        
        # Prepare user data in the same format as admin_user_management
        users_data = []
        for user in faculty_users:
            # Get user's role assignments (only Faculty roles in this org/parent)
            faculty_assignments = user.role_assignments.filter(
                role__name__iexact='Faculty'
            ).filter(org_filter)
            
            # Skip if no faculty assignments found
            if not faculty_assignments.exists():
                continue
            
            # Get roles for display
            role_names = list(faculty_assignments.values_list('role__name', flat=True))
            
            users_data.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.get_full_name() or user.username,
                'email': user.email,
                'roles': role_names
            })
        
        logger.info(f"Found {len(users_data)} FACULTY users for org {org_id} with search '{search_query}'")
        return JsonResponse(users_data, safe=False)
        
    except Organization.DoesNotExist:
        return JsonResponse({'error': 'Organization not found'}, status=404)
    except Exception as e:
        logger.error(f"Error fetching faculty users for org {org_id}: {str(e)}")
        return JsonResponse({'error': f'Failed to fetch users: {str(e)}'}, status=500)
        
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

@login_required
@require_http_methods(["GET"])
def api_popso_manager_status(request):
    """Check if the current user is assigned as a PO/PSO manager"""
    from .models import POPSOAssignment
    
    try:
        # Check if user is assigned to any organization for PO/PSO management
        is_manager = POPSOAssignment.objects.filter(
            assigned_user=request.user,
            is_active=True
        ).exists()
        
        # If user is a manager, get their assigned organizations
        assignments = []
        if is_manager:
            assignments = POPSOAssignment.objects.filter(
                assigned_user=request.user,
                is_active=True
            ).select_related('organization').values(
                'organization__id',
                'organization__name',
                'organization__org_type__name'
            )
        
        return JsonResponse({
            'is_manager': is_manager,
            'assignments': list(assignments)
        })
        
    except Exception as e:
        logger.error(f"Error checking manager status for user {request.user.id}: {str(e)}")
        return JsonResponse({'error': 'Failed to check manager status'}, status=500)

@login_required
def settings_pso_po_management(request):
    """Settings page for assigned PO/PSO managers"""
    from .models import POPSOAssignment, Program, ProgramOutcome, ProgramSpecificOutcome
    
    # Check if user is assigned as manager
    assignments = POPSOAssignment.objects.filter(
        assigned_user=request.user,
        is_active=True
    ).select_related('organization', 'organization__org_type')
    
    if not assignments.exists():
        messages.error(request, "You are not assigned to manage any PO/PSO outcomes.")
        return redirect('dashboard')
    
    # Get assigned organizations and their programs
    assigned_orgs = []
    for assignment in assignments:
        org = assignment.organization
        programs = Program.objects.filter(organization=org)
        
        org_data = {
            'organization': org,
            'programs': programs,
            'assignment': assignment
        }
        assigned_orgs.append(org_data)
    
    context = {
        'assigned_organizations': assigned_orgs,
        'user': request.user
    }
    
    return render(request, 'core/settings_pso_po_management.html', context)

