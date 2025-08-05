import os
import shutil
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden, JsonResponse, HttpResponseRedirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.forms import inlineformset_factory
from django import forms
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
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
)
from emt.models import EventProposal, Student
from django.views.decorators.http import require_GET, require_POST
from .models import ApprovalFlowTemplate, ApprovalFlowConfig
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
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
    student, _ = Student.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            student.registration_number = form.cleaned_data["registration_number"]
            student.save()
            for item in form.cleaned_data["assignments"]:
                RoleAssignment.objects.get_or_create(
                    user=request.user,
                    organization_id=item["organization"],
                    role_id=item["role"],
                )
            return redirect("dashboard")
    else:
        initial = {"registration_number": student.registration_number}
        form = RegistrationForm(initial=initial)

    return render(request, "core/Registration_form.html", {"form": form})


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
#  Dashboard
# ─────────────────────────────────────────────────────────────
@login_required
def dashboard(request):
    # Role-based landing logic
    user = request.user
    roles = RoleAssignment.objects.filter(user=user).select_related('role', 'organization')
    role_names = [ra.role.name for ra in roles]

    # Superuser/admin: redirect to admin dashboard
    if user.is_superuser:
        return redirect('admin_dashboard')

    # Student: show student dashboard (core/dashboard.html)
    if 'student' in [r.lower() for r in role_names]:
        dashboard_template = "core/dashboard.html"
    # Faculty: show faculty dashboard (core/dashboard.html)
    elif 'faculty' in [r.lower() for r in role_names]:
        dashboard_template = "core/dashboard.html"
    # Default: show dashboard
    else:
        dashboard_template = "core/dashboard.html"

    finalized_events = EventProposal.objects.filter(status='finalized').distinct()
    my_events = finalized_events.filter(Q(submitted_by=user) | Q(faculty_incharges=user)).distinct()
    other_events = finalized_events.exclude(Q(submitted_by=user) | Q(faculty_incharges=user)).distinct()
    upcoming_events_count = finalized_events.filter(event_datetime__gte=timezone.now()).count()
    organized_events_count = my_events.count()
    week_start = timezone.now().date() - timezone.timedelta(days=timezone.now().weekday())
    week_end = week_start + timezone.timedelta(days=6)
    this_week_events = finalized_events.filter(event_datetime__date__gte=week_start, event_datetime__date__lte=week_end).count()
    students_participated = finalized_events.aggregate(
        total=Sum('fest_fee_participants') + Sum('conf_fee_participants')
    )['total'] or 0
    my_students = Student.objects.filter(mentor=user)
    my_classes = Class.objects.filter(teacher=user)
    context = {
        "my_events": my_events,
        "other_events": other_events,
        "upcoming_events_count": upcoming_events_count,
        "organized_events_count": organized_events_count,
        "this_week_events": this_week_events,
        "students_participated": students_participated,
        "my_students": my_students,
        "my_classes": my_classes,
        "role_names": role_names,
        "user": user,
    }
    return render(request, dashboard_template, context)

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
    all_assignments = RoleAssignment.objects.select_related('role', 'user').all()
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
        'active_users': User.objects.filter(is_active=True).count(),
        'new_users_this_week': User.objects.filter(date_joined__gte=timezone.now() - timedelta(days=7)).count(),
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
    return redirect("admin_role_management") + f"?org_type_id={org.org_type.id}"


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
        return redirect("admin_role_management") + f"?org_type_id={org_type.id}"

    # Update all roles with the old name from all organizations of this type
    updated_count = OrganizationRole.objects.filter(
        organization__org_type=org_type,
        name__iexact=old_name
    ).update(
        name=new_name,
        description=new_description
    )
    
    messages.success(request, f"Role updated for {updated_count} {org_type.name}(s).")
    return redirect("admin_role_management") + f"?org_type_id={org_type.id}"


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
    return redirect("admin_role_management") + f"?org_type_id={org_type.id}"

# ===================================================================
# END OF SINGLE-PAGE ROLE MANAGEMENT
# ===================================================================

@user_passes_test(lambda u: u.is_superuser)
def admin_user_management(request):
    """
    Manages and displays a paginated list of users with filtering capabilities.
    """
    users_list = User.objects.select_related('profile').prefetch_related(
        'role_assignments__organization', 
        'role_assignments__role'
    ).order_by('-date_joined')

    q = request.GET.get('q', '').strip()
    role_id = request.GET.get('role')
    org_id = request.GET.get('organization')
    status = request.GET.get('status')

    if q:
        users_list = users_list.filter(
            Q(email__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(username__icontains=q)
        )
    
    if role_id:
        users_list = users_list.filter(role_assignments__role_id=role_id)
    
    if org_id:
        users_list = users_list.filter(role_assignments__organization_id=org_id)

    if status in ['active', 'inactive']:
        users_list = users_list.filter(is_active=(status == 'active'))

    users_list = users_list.distinct()

    paginator = Paginator(users_list, 25)
    page_number = request.GET.get('page')
    try:
        users = paginator.page(page_number)
    except PageNotAnInteger:
        users = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages)

    all_roles = OrganizationRole.objects.filter(is_active=True).order_by('name')
    all_organizations = Organization.objects.filter(is_active=True).order_by('name')

    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']

    context = {
        'users': users,
        'all_roles': all_roles,
        'all_organizations': all_organizations,
        'current_filters': {
            'q': q,
            'role': int(role_id) if role_id and role_id.isdigit() else None,
            'organization': int(org_id) if org_id and org_id.isdigit() else None,
            'status': status,
        },
        'query_params': query_params.urlencode(),
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
    if request.method == "POST":
        formset = RoleFormSet(request.POST, instance=user)
        user.first_name = request.POST.get("first_name", "").strip()
        user.last_name  = request.POST.get("last_name", "").strip()
        user.email      = request.POST.get("email", "").strip()
        user.save()

        if formset.is_valid():
            formset.save()
            messages.success(request, "User roles updated successfully.")
            return redirect("admin_user_management")
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
        "title": p.title,
        "description": p.description,
        "organization": str(p.organization) if p.organization else None,
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

    selected_year_param = request.GET.get('year')
    current_year = datetime.datetime.now().year

    academic_years_from_db = AcademicYear.objects.all().order_by('-year')
    if not academic_years_from_db.exists():
        for year in range(current_year - 1, current_year + 3):
            AcademicYear.objects.create(year=f"{year}-{year + 1}")
        academic_years_from_db = AcademicYear.objects.all().order_by('-year')

    academic_years = [{'value': ay.year, 'display': ay.year} for ay in academic_years_from_db]

    if selected_year_param:
        selected_year = next((ay for ay in academic_years if ay['value'] == selected_year_param), None)
        if not selected_year:
            selected_year = academic_years[0] if academic_years else {'value': f"{current_year}-{current_year + 1}", 'display': f"{current_year}-{current_year + 1}"}
    else:
        selected_year = academic_years[0] if academic_years else {'value': f"{current_year}-{current_year + 1}", 'display': f"{current_year}-{current_year + 1}"}

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
        "academic_years": academic_years,
        "selected_year": selected_year,
        "orgs_by_type_json": json.dumps(orgs_by_type_json),
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

@user_passes_test(lambda u: u.is_superuser)
def admin_settings_dashboard(request):
    return render(request, "core/admin_settings.html")

@user_passes_test(lambda u: u.is_superuser)
def master_data_dashboard(request):
    from transcript.models import AcademicYear
    from django.contrib.auth.models import User
    
    stats = {
        'organizations': Organization.objects.count(),
        'org_types': OrganizationType.objects.count(),
        'academic_years': AcademicYear.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
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




@login_required
@csrf_exempt
def set_academic_year(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            academic_year = data.get('academic_year')
            if academic_year:
                request.session['selected_academic_year'] = str(academic_year)
                return JsonResponse({'success': True})
        except (json.JSONDecodeError, ValueError):
            pass
    return JsonResponse({'success': False})

@login_required
@user_passes_test(lambda u: u.is_superuser)
@csrf_exempt
def add_academic_year(request):
    if request.method == 'POST':
        try:
            import re
            from transcript.models import AcademicYear
            data = json.loads(request.body)
            academic_year = data.get('academic_year')
            if not academic_year:
                return JsonResponse({'success': False, 'error': 'Academic year is required'})
            if not re.match(r'^\d{4}-\d{4}$', academic_year):
                return JsonResponse({'success': False, 'error': 'Invalid format. Use YYYY-YYYY (e.g., 2025-2026)'})
            if AcademicYear.objects.filter(year=academic_year).exists():
                return JsonResponse({'success': False, 'error': f'Academic year {academic_year} already exists'})
            AcademicYear.objects.create(year=academic_year)
            return JsonResponse({'success': True, 'message': f'Academic year {academic_year} added successfully'})
        except (json.JSONDecodeError, ValueError) as e:
            return JsonResponse({'success': False, 'error': 'Invalid request data'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Only POST method allowed'})

@user_passes_test(lambda u: u.is_superuser)
def admin_pso_po_management(request):
    import json
    from .models import Program, ProgramOutcome, ProgramSpecificOutcome
    
    org_types = OrganizationType.objects.filter(is_active=True).order_by('name')
    orgs_by_type = {}
    orgs_by_type_json = {}

    for org_type in org_types:
        qs = Organization.objects.filter(org_type=org_type).order_by('name')
        orgs_by_type[org_type.name] = qs
        active_orgs = qs.filter(is_active=True)
        orgs_by_type_json[org_type.name.lower()] = [{'id': o.id, 'name': o.name} for o in active_orgs]
    
    programs = Program.objects.all().order_by("name")
    context = {
        "org_types": org_types,
        "orgs_by_type": orgs_by_type,
        "orgs_by_type_json": json.dumps(orgs_by_type_json),
        "programs": programs,
    }
    return render(request, "core/admin_pso_po_management.html", context)

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
            user_id=step.get('user_id')
        )

    config, _ = ApprovalFlowConfig.objects.get_or_create(organization=org)
    config.require_faculty_incharge_first = require_first
    config.save()

    return JsonResponse({'success': True})
def api_approval_flow_steps(request, org_id):
    steps = list(
        ApprovalFlowTemplate.objects.filter(organization_id=org_id).order_by('step_order').values(
            'id', 'step_order', 'role_required', 'user_id'
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
    roles = (
        OrganizationRole.objects
        .filter(organization__org_type_id=org_type_id, is_active=True)
        .values("id", "name")
        .order_by("name")
    )
    # Deduplicate by name while preserving an ID for each
    seen = set()
    unique_roles = []
    for r in roles:
        if r["name"] not in seen:
            seen.add(r["name"])
            unique_roles.append({"id": r["id"], "name": r["name"]})
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
    role = 'faculty' if user.is_staff else 'student'
    initials = ''.join([x[0] for x in user.get_full_name().split()]) or user.username[:2].upper()
    return JsonResponse({
        'role': role,
        'name': user.get_full_name(),
        'subtitle': '',  # Add more info if needed
        'initials': initials,
    })

@login_required
def api_faculty_overview(request):
    stats = [
        # Build from your models as needed
    ]
    return JsonResponse(stats, safe=False)

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
@require_GET
def admin_dashboard_api(request):
    """
    API endpoint for dashboard analytics - useful for real-time updates.
    """
    from django.contrib.auth.models import User
    stats = {
        'students': User.objects.filter(
            role_assignments__role__name__icontains='student'
        ).distinct().count(),
        'faculties': User.objects.filter(
            role_assignments__role__name__icontains='faculty'
        ).distinct().count(),
        'hods': User.objects.filter(
            role_assignments__role__name__icontains='hod'
        ).distinct().count(),
        'centers': Organization.objects.filter(is_active=True).count(),
        'total_users': User.objects.filter(is_active=True).count(),
        'total_proposals': EventProposal.objects.count(),
        'pending_proposals': EventProposal.objects.filter(
            status__in=['submitted', 'under_review']
        ).count(),
    }
    return JsonResponse({'success': True, 'stats': stats})