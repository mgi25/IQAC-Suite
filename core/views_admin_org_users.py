import csv
import io
import re

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from core.models import Organization, OrganizationMembership, Profile
from .forms import OrgUsersCSVUploadForm

VALID_ROLES = {
    "student": "student",
    "faculty": "faculty",
    "tutor": "tutor",
    "s": "student",
    "f": "faculty",
    "t": "tutor",
}


def _split_name(fullname: str):
    fullname = (fullname or "").strip()
    if not fullname:
        return "", ""
    if "," in fullname:
        last, first = [x.strip() for x in fullname.split(",", 1)]
        return first, last
    parts = fullname.split()
    if len(parts) == 1:
        return parts[0], ""
    return " ".join(parts[:-1]), parts[-1]

@user_passes_test(lambda u: u.is_superuser)
def entrypoint(request):
    return render(request, "core_admin_org_users/entrypoint.html")


@user_passes_test(lambda u: u.is_superuser)
def select_role(request, org_id):
    """
    Page shown after clicking 'Add Users' for a specific organization.
    Lets admin choose Student or Faculty. Then redirects to the right flow.
    """
    org = get_object_or_404(Organization, pk=org_id)
    if request.method == "POST":
        role = request.POST.get("role")
        if role == "student":
            return redirect("admin_org_users_students", org_id=org.id)
        if role == "faculty":
            return redirect("admin_org_users_faculty", org_id=org.id)
    return render(request, "core_admin_org_users/select_role.html", {"org": org})


@user_passes_test(lambda u: u.is_superuser)
def student_flow(request, org_id):
    org = get_object_or_404(Organization, pk=org_id)
    # TODO: render tabs for Existing Class / Create New Class + CSV upload
    return render(request, "core_admin_org_users/students.html", {"org": org})


@user_passes_test(lambda u: u.is_superuser)
def faculty_flow(request, org_id):
    org = get_object_or_404(Organization, pk=org_id)
    # TODO: UI to assign faculty to org or underlying class + CSV upload
    return render(request, "core_admin_org_users/faculty.html", {"org": org})


@user_passes_test(lambda u: u.is_superuser)
def create_class(request, org_id):
    org = get_object_or_404(Organization, pk=org_id)
    # TODO: create class under org, then redirect back to students flow
    return redirect("admin_org_users_students", org_id=org.id)


@user_passes_test(lambda u: u.is_superuser)
def upload_csv(request, org_id):
    org = get_object_or_404(Organization, pk=org_id)
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    referer = request.META.get("HTTP_REFERER", "")
    is_faculty = "faculty" in referer

    form = OrgUsersCSVUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "Please provide Academic Year and a CSV file.")
        if referer:
            return redirect(referer)
        return redirect(
            "admin_org_users_faculty" if is_faculty else "admin_org_users_students",
            org_id=org.id,
        )

    ay = form.cleaned_data["academic_year"].strip()
    f = request.FILES["csv_file"]
    if not f.name.lower().endswith(".csv"):
        messages.error(request, "Only .csv files are allowed.")
        return redirect(
            "admin_org_users_faculty" if is_faculty else "admin_org_users_students",
            org_id=org.id,
        )

    users_created = 0
    users_updated = 0
    memberships_created = 0
    memberships_updated = 0
    skipped = 0
    errors = []

    try:
        data = f.read().decode("utf-8-sig")
    except Exception:
        data = f.read().decode("latin-1")

    reader = csv.DictReader(io.StringIO(data))
    id_field = "emp_id" if is_faculty else "register_no"
    required = {id_field, "name", "email", "role"}
    if not required.issubset({c.strip().lower() for c in reader.fieldnames or []}):
        messages.error(
            request,
            f"CSV must have headers: {id_field}, name, email, role",
        )
        return redirect(
            "admin_org_users_faculty" if is_faculty else "admin_org_users_students",
            org_id=org.id,
        )

    with transaction.atomic():
        for i, row in enumerate(reader, start=2):
            reg = (row.get(id_field) or "").strip()
            name = (row.get("name") or "").strip()
            email = (row.get("email") or "").strip().lower()
            role_raw = (row.get("role") or "").strip().lower()
            role = VALID_ROLES.get(role_raw)

            if not email or "@" not in email:
                skipped += 1
                errors.append(f"Row {i}: invalid email")
                continue
            if not role:
                skipped += 1
                errors.append(f"Row {i}: invalid role '{role_raw}' (use student/faculty/tutor)")
                continue

            first, last = _split_name(name)

            user, created = User.objects.get_or_create(
                username=email,
                defaults={"email": email, "first_name": first, "last_name": last, "is_active": True},
            )
            if created:
                users_created += 1
            else:
                upd = False
                if not user.first_name and first:
                    user.first_name = first
                    upd = True
                if not user.last_name and last:
                    user.last_name = last
                    upd = True
                if upd:
                    user.save(update_fields=["first_name", "last_name"])
                    users_updated += 1

            profile, _ = Profile.objects.get_or_create(user=user)
            if hasattr(profile, "register_no") and reg:
                if profile.register_no != reg:
                    profile.register_no = reg
                    profile.save(update_fields=["register_no"])

            mem, mem_created = OrganizationMembership.objects.get_or_create(
                user=user,
                organization=org,
                academic_year=ay,
                defaults={"role": role, "is_primary": True},
            )
            if mem_created:
                memberships_created += 1
            else:
                if mem.role != role:
                    mem.role = role
                    mem.save(update_fields=["role"])
                    memberships_updated += 1

    if errors:
        messages.warning(
            request,
            "Some rows were skipped:\n" + "\n".join(errors[:8]) + ("" if len(errors) <= 8 else f"\n(+{len(errors) - 8} more)"),
        )
    messages.success(
        request,
        f"CSV processed for {org.name} ({ay}). Users created: {users_created}, Users updated: {users_updated}, "
        f"Memberships created: {memberships_created}, Memberships updated: {memberships_updated}, Skipped: {skipped}.",
    )

    if is_faculty:
        return redirect("admin_org_users_faculty", org_id=org.id)
    return redirect("admin_org_users_students", org_id=org.id)


@user_passes_test(lambda u: u.is_superuser)
def csv_template(request, org_id):
    org = get_object_or_404(Organization, pk=org_id)
    role = request.GET.get("role", "student")
    field = "emp_id" if role == "faculty" else "register_no"

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="org_{org.id}_bulk_upload_template.csv"'
    writer = csv.writer(response)
    writer.writerow([field, "name", "email", "role"])
    sample_id = "EMP001" if field == "emp_id" else "24DS001"
    writer.writerow([sample_id, "Aarya Shah", "aarya@example.edu", role])
    return response


@user_passes_test(lambda u: u.is_superuser)
def fetch_children(request, org_id):
    children = Organization.objects.filter(parent_id=org_id).order_by("name")
    data = [{"id": o.id, "name": o.name, "code": o.code} for o in children]
    return JsonResponse(data, safe=False)


@user_passes_test(lambda u: u.is_superuser)
def fetch_by_type(request, type_id):
    orgs = Organization.objects.filter(org_type_id=type_id).order_by("name")
    data = [{"id": o.id, "name": o.name, "code": o.code} for o in orgs]
    return JsonResponse(data, safe=False)

