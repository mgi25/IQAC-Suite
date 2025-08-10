from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse

from .models import Organization, OrganizationType, OrganizationMembership
from .forms import OrgSelectForm, CreateClassForm, CSVUploadForm

import csv
import io

superuser_required = user_passes_test(lambda u: u.is_superuser)


@superuser_required
def entrypoint(request):
    return render(request, "core_admin_org_users/entrypoint.html")


@superuser_required
def select_role(request):
    if request.method == "POST":
        form = OrgSelectForm(request.POST)
        if form.is_valid():
            request.session["orgu_selected_org"] = form.cleaned_data["organization"].id
            request.session["orgu_role"] = form.cleaned_data["role"]
            if form.cleaned_data["role"] == "student":
                return redirect("admin_org_users_students")
            return redirect("admin_org_users_faculty")
    else:
        form = OrgSelectForm()
    return render(request, "core_admin_org_users/select_role.html", {"form": form})


@superuser_required
def student_flow(request):
    org_id = request.session.get("orgu_selected_org")
    role = request.session.get("orgu_role")
    if not org_id or role != "student":
        return redirect("admin_org_users_select_role")
    organization = get_object_or_404(Organization, id=org_id)
    existing_classes = organization.children.all()
    create_form = CreateClassForm(initial={"parent_org": organization})
    upload_form = CSVUploadForm()
    return render(
        request,
        "core_admin_org_users/students.html",
        {
            "organization": organization,
            "existing_classes": existing_classes,
            "create_form": create_form,
            "upload_form": upload_form,
        },
    )


@superuser_required
def faculty_flow(request):
    org_id = request.session.get("orgu_selected_org")
    role = request.session.get("orgu_role")
    if not org_id or role != "faculty":
        return redirect("admin_org_users_select_role")
    organization = get_object_or_404(Organization, id=org_id)
    children = organization.children.all()
    upload_form = CSVUploadForm()
    return render(
        request,
        "core_admin_org_users/faculty.html",
        {
            "organization": organization,
            "children": children,
            "upload_form": upload_form,
        },
    )


@superuser_required
def create_class(request):
    if request.method != "POST":
        return redirect("admin_org_users_students")
    form = CreateClassForm(request.POST)
    if form.is_valid():
        parent_org = form.cleaned_data["parent_org"]
        org = Organization.objects.create(
            name=form.cleaned_data["name"],
            org_type=parent_org.org_type,
            parent=parent_org,
            code=form.cleaned_data["code"],
            meta={"academic_year": form.cleaned_data["academic_year"]},
        )
        messages.success(request, f"Class '{org.name}' created")
    else:
        messages.error(request, "Failed to create class")
    return redirect("admin_org_users_students")


@superuser_required
def upload_csv(request):
    if request.method != "POST":
        return redirect("admin_org_users_select_role")
    role = request.session.get("orgu_role")
    redirect_view = (
        "admin_org_users_students" if role == "student" else "admin_org_users_faculty"
    )
    form = CSVUploadForm(request.POST, request.FILES)
    org_id = (
        request.POST.get("organization_id")
        or request.POST.get("class_id")
        or request.session.get("orgu_selected_org")
    )
    if not org_id:
        messages.error(request, "No organization selected")
        return redirect(redirect_view)
    organization = get_object_or_404(Organization, id=org_id)
    if not form.is_valid():
        messages.error(request, "Please upload a valid CSV file")
        return redirect(redirect_view)
    csv_file = form.cleaned_data["csv_file"]
    if not csv_file.name.lower().endswith(".csv"):
        messages.error(request, "Please upload a CSV file")
        return redirect(redirect_view)
    try:
        decoded = csv_file.read().decode("utf-8")
    except Exception:
        messages.error(request, "Could not read uploaded file")
        return redirect(redirect_view)
    reader = csv.DictReader(io.StringIO(decoded))
    required = {"email", "first_name", "last_name", "academic_year", "role"}
    missing = required - set(reader.fieldnames or [])
    if missing:
        messages.error(request, f"Missing columns: {', '.join(sorted(missing))}")
        return redirect(redirect_view)
    users_created = memberships_created = memberships_updated = rows_skipped = 0
    for row in reader:
        email = (row.get("email") or "").strip().lower()
        first_name = (row.get("first_name") or "").strip()
        last_name = (row.get("last_name") or "").strip()
        academic_year = (row.get("academic_year") or "").strip()
        row_role = (row.get("role") or "").strip().lower()
        if not email or not academic_year or row_role != role:
            rows_skipped += 1
            continue
        user, created = OrganizationMembership._meta.get_field("user").remote_field.model.objects.get_or_create(
            username=email,
            defaults={"email": email, "first_name": first_name, "last_name": last_name, "is_active": True},
        )
        if created:
            users_created += 1
        else:
            # update names if blank
            changed = False
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                changed = True
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                changed = True
            if changed:
                user.save()
        membership, created_mem = OrganizationMembership.objects.get_or_create(
            user=user,
            organization=organization,
            academic_year=academic_year,
            defaults={"role": role},
        )
        if created_mem:
            memberships_created += 1
        else:
            if membership.role != role:
                membership.role = role
                membership.save()
            memberships_updated += 1
    summary = (
        f"Created {users_created} users, Created {memberships_created} memberships, "
        f"Updated {memberships_updated} memberships, Skipped {rows_skipped} rows"
    )
    messages.success(request, summary)
    return redirect(redirect_view)


@superuser_required
def fetch_children(request, org_id):
    children = Organization.objects.filter(parent_id=org_id).order_by("name")
    data = [
        {"id": o.id, "name": o.name, "code": o.code} for o in children
    ]
    return JsonResponse(data, safe=False)


@superuser_required
def fetch_by_type(request, type_id):
    orgs = Organization.objects.filter(org_type_id=type_id).order_by("name")
    data = [{"id": o.id, "name": o.name, "code": o.code} for o in orgs]
    return JsonResponse(data, safe=False)
