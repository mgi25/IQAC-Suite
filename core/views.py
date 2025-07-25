from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden, JsonResponse, HttpResponseRedirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Sum
from django.forms import inlineformset_factory
from django import forms
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json
from .models import (
    Profile,
    RoleAssignment,
    Organization,
    OrganizationType,
    Report,
    OrganizationRole,
)
from emt.models import (
    EventProposal, EventNeedAnalysis, EventObjectives, EventExpectedOutcomes, TentativeFlow,
    ExpenseDetail, SpeakerProfile, ApprovalStep
)
from django.views.decorators.http import require_GET, require_POST
from .models import ApprovalFlowTemplate
# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────
def superuser_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_superuser):
            return HttpResponseForbidden("You are not authorized to access this page.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


class RoleAssignmentForm(forms.ModelForm):
    class Meta:
        model = RoleAssignment
        fields = ("role", "organization")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        extra = [(r.name, r.name) for r in OrganizationRole.objects.all()]
        self.fields["role"].choices = RoleAssignment.ROLE_CHOICES + extra

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

        roles = [ra.get_role_display() for ra in request.user.role_assignments.all()]
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
def admin_dashboard(request):
    return render(request, "core/admin_dashboard.html")

@user_passes_test(lambda u: u.is_superuser)
def admin_user_panel(request):
    return render(request, "core/admin_user_panel.html")


@user_passes_test(lambda u: u.is_superuser)
def admin_role_management(request):
    org_types = OrganizationType.objects.all().order_by("name")

    context = {
        "org_types": org_types,
    }
    return render(request, "core/admin_role_management.html", context)



@user_passes_test(lambda u: u.is_superuser)
@require_POST
def add_org_role(request):
    org_id = request.POST.get("org_id")
    org_type_id = request.POST.get("org_type_id")
    name = request.POST.get("name", "").strip()

    if not name:
        return redirect("admin_role_management")

    if org_id:
        org = get_object_or_404(Organization, id=org_id)
        OrganizationRole.objects.get_or_create(organization=org, name=name)
        messages.success(request, f"Role '{name}' added to {org.name}.")
    elif org_type_id:
        orgs = Organization.objects.filter(org_type_id=org_type_id, is_active=True)
        org_names = []
        for org in orgs:
            OrganizationRole.objects.get_or_create(organization=org, name=name)
            org_names.append(org.name)
        org_type = get_object_or_404(OrganizationType, id=org_type_id)
        if org_names:
            msg = f"Role '{name}' added to all organizations in {org_type.name}: {', '.join(org_names)}"
        else:
            msg = f"No active organizations found in {org_type.name}."
        messages.success(request, msg)
    return redirect("admin_role_management")


@user_passes_test(lambda u: u.is_superuser)
@require_POST
def delete_org_role(request, role_id):
    role = get_object_or_404(OrganizationRole, id=role_id)
    role.delete()
    return redirect("admin_role_management")


@user_passes_test(lambda u: u.is_superuser)
def view_org_roles(request):
    """Display roles, optionally filtered by organization type."""
    roles = (
        OrganizationRole.objects.select_related("organization", "organization__org_type")
        .order_by("organization__org_type__name", "organization__name", "name")
    )

    org_type_id = request.GET.get("org_type_id")
    org_type = None
    if org_type_id:
        org_type = get_object_or_404(OrganizationType, id=org_type_id)
        roles = roles.filter(organization__org_type=org_type)

    context = {
        "roles": roles,
        "org_type": org_type,
    }
    return render(request, "core/admin_view_roles.html", context)


@user_passes_test(lambda u: u.is_superuser)
@require_POST
def update_org_role(request, role_id):
    role = get_object_or_404(OrganizationRole, id=role_id)
    new_name = request.POST.get("name", "").strip()
    if new_name:
        role.name = new_name
        role.save()
    return redirect("view_org_roles")


@user_passes_test(lambda u: u.is_superuser)
@require_POST
def toggle_org_role(request, role_id):
    role = get_object_or_404(OrganizationRole, id=role_id)
    role.is_active = not role.is_active
    role.save()
    return redirect("view_org_roles")

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
    users = users.distinct().prefetch_related('role_assignments', 'role_assignments__organization')
    return render(request, "core/admin_user_management.html", {"users": users})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    RoleFormSet = inlineformset_factory(
        User,
        RoleAssignment,
        form=RoleAssignmentForm,
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

    orgs = (
        Organization.objects.filter(is_active=True)
        .select_related("org_type")
        .prefetch_related("roles")
    )

    org_roles = {org.id: [r.name for r in org.roles.all()] for org in orgs}

    orgs_by_type = {}
    roles_by_type = {}
    for org in orgs:
        ot_id = org.org_type_id
        orgs_by_type.setdefault(ot_id, []).append({"id": org.id, "name": org.name})
        roles_by_type.setdefault(ot_id, set()).update(r.name for r in org.roles.all())
    roles_by_type = {k: sorted(v) for k, v in roles_by_type.items()}

    return render(
        request,
        "core/admin_user_edit.html",
        {
            "user_obj": user,
            "formset": formset,
            "organizations": Organization.objects.filter(is_active=True),
            "organization_types": OrganizationType.objects.filter(),
            "org_roles_json": json.dumps(org_roles),
            "role_choices_json": json.dumps(RoleAssignment.ROLE_CHOICES),
            "orgs_by_type_json": json.dumps(orgs_by_type),
            "roles_by_type_json": json.dumps(roles_by_type),
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
        # Include both active and inactive organizations for comprehensive management
        qs = Organization.objects.filter(org_type=org_type).order_by('name')
        orgs_by_type[org_type.name] = qs
        # For JS: only include active organizations for parent dropdown
        active_orgs = qs.filter(is_active=True)
        orgs_by_type_json[org_type.name.lower()] = [{'id': o.id, 'name': o.name} for o in active_orgs]

    return render(request, "core/admin_master_data.html", {
        "org_types": org_types,
        "orgs_by_type": orgs_by_type,
        "academic_years": academic_years,
        "selected_year": selected_year,
        "orgs_by_type_json": json.dumps(orgs_by_type_json),  # Pass for JS dynamic dropdown!
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
            parent_id = data.get("parent")  # Can be None, empty string, or an ID
            
            if not name:
                return JsonResponse({"success": False, "error": "Name is required"})
            
            obj.name = name
            if hasattr(obj, "is_active"):
                obj.is_active = is_active
            
            # Handle parent assignment for organizations
            if model_name == "organization" and hasattr(obj, "parent"):
                if parent_id and parent_id.strip():  # If parent_id is provided and not empty
                    try:
                        parent_obj = Organization.objects.get(id=parent_id)
                        # Validate that the parent is of the correct type for this organization
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
                    # Remove parent if empty or None
                    obj.parent = None
            
            obj.save()
            
            response_data = {
                "success": True,
                "name": obj.name,
                "is_active": getattr(obj, "is_active", True),
            }
            
            # Include parent name in response if applicable
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
                
                # Get or create the organization type
                try:
                    org_type_obj = OrganizationType.objects.get(name__iexact=org_type_name)
                except OrganizationType.DoesNotExist:
                    return JsonResponse({"success": False, "error": f"Organization type '{org_type_name}' does not exist"})
                
                # Check if organization with same name and type already exists
                if Organization.objects.filter(name__iexact=name, org_type=org_type_obj).exists():
                    return JsonResponse({"success": False, "error": f"{org_type_obj.name} with name '{name}' already exists"})
                
                # Handle parent organization
                parent_obj = None
                if parent_id:
                    try:
                        parent_obj = Organization.objects.get(id=parent_id)
                    except Organization.DoesNotExist:
                        return JsonResponse({"success": False, "error": "Parent organization not found"})
                
                # Create the organization
                obj = Organization.objects.create(
                    name=name,
                    org_type=org_type_obj,
                    parent=parent_obj,
                    is_active=True
                )
                
            elif model_name == "organization_type":
                parent_id = data.get("parent")
                
                # Check if organization type already exists
                if OrganizationType.objects.filter(name__iexact=name).exists():
                    return JsonResponse({"success": False, "error": f"Organization type '{name}' already exists"})
                
                # Handle parent type
                parent_obj = None
                if parent_id:
                    try:
                        parent_obj = OrganizationType.objects.get(id=parent_id)
                    except OrganizationType.DoesNotExist:
                        return JsonResponse({"success": False, "error": "Parent organization type not found"})
                
                # Create the organization type
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
    return render(request, "core/admin_settings.html")

@user_passes_test(lambda u: u.is_superuser)
def master_data_dashboard(request):
    from transcript.models import AcademicYear
    from django.contrib.auth.models import User
    
    # Calculate statistics
    stats = {
        'organizations': Organization.objects.count(),
        'org_types': OrganizationType.objects.count(),
        'academic_years': AcademicYear.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
    }
    
    # Recent activities (placeholder - you can implement actual activity tracking)
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
    }
    return render(request, "core/admin_approval_flow_manage.html", context)


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
    from .models import Program, ProgramOutcome, ProgramSpecificOutcome
    programs = Program.objects.all().order_by("name")
    context = {
        "programs": programs,
    }
    return render(request, "core/admin_pso_po_management.html", context)

@require_GET
def get_approval_flow(request, org_id):
    steps = ApprovalFlowTemplate.objects.filter(organization_id=org_id).order_by('step_order')
    data = [
        {
            'id': step.id,
            'step_order': step.step_order,
            'role_required': step.role_required,
            'user_id': step.user.id if step.user else None,
            'user_name': step.user.get_full_name() if step.user else '',
        } for step in steps
    ]
    return JsonResponse({'success': True, 'steps': data})

@require_POST
@csrf_exempt
def save_approval_flow(request, org_id):
    data = json.loads(request.body)
    steps = data.get('steps', [])
    org = Organization.objects.get(id=org_id)
    # Remove old steps
    ApprovalFlowTemplate.objects.filter(organization=org).delete()
    # Add new steps
    for idx, step in enumerate(steps, 1):
        if not step.get('role_required'):
            continue  # skip empty roles
        ApprovalFlowTemplate.objects.create(
            organization=org,
            step_order=idx,
            role_required=step['role_required'],
            user_id=step.get('user_id')
        )

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
    q = request.GET.get("q", "")
    role = request.GET.get("role", "")
    org_id = request.GET.get("org_id", "")

    users = User.objects.all()

    # --- Filter by search string ---
    if q:
        users = users.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q)
        )

    # --- Filter by role ---
    if role:
        users = users.filter(role_assignments__role__iexact=role)

    # --- Filter by organization/department ---
    if org_id:
        users = users.filter(role_assignments__organization_id=org_id)

    users = users.distinct()[:10]
    data = [{"id": u.id, "name": u.get_full_name(), "email": u.email} for u in users]
    return JsonResponse({"success": True, "users": data})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def organization_users(request, org_id):
    """Return users for a given organization, optional search by name or role."""
    q = request.GET.get("q", "")
    role = request.GET.get("role", "")

    assignments = RoleAssignment.objects.filter(organization_id=org_id)
    if role:
        assignments = assignments.filter(role__iexact=role)
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
            "role": a.get_role_display(),
        }
        for a in assignments
    ]
    return JsonResponse({"success": True, "users": users_data})

