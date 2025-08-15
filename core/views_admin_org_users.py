import csv
import io
import re

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from core.models import (
    Organization,
    OrganizationMembership,
    Profile,
    Class,
    OrganizationRole,
    RoleAssignment,
)
from emt.models import Student as EmtStudent
from .forms import OrgUsersCSVUploadForm
from django.urls import reverse

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
    Unified user management interface with tabbed layout.
    Replaces the old role selection with a comprehensive management page.
    """
    org = get_object_or_404(Organization, pk=org_id)
    
    # Handle direct POST requests from old form submissions for backward compatibility
    if request.method == "POST":
        role = request.POST.get("role")
        if role == "student":
            return redirect("admin_org_users_students", org_id=org.id)
        if role == "faculty":
            return redirect("admin_org_users_faculty", org_id=org.id)
    
    # Return the new unified interface
    return render(request, "core_admin_org_users/user_management.html", {"org": org})


@user_passes_test(lambda u: u.is_superuser)
def student_flow(request, org_id):
    org = get_object_or_404(Organization, pk=org_id)
    show_archived = request.GET.get("archived") == "1"
    classes = (
        Class.objects.filter(organization=org, is_active=not show_archived)
        .annotate(student_count=Count("students"))
        .order_by("name")
    )
    return render(
        request,
        "core_admin_org_users/students.html",
        {"org": org, "classes": classes, "show_archived": show_archived},
    )


@user_passes_test(lambda u: u.is_superuser)
def faculty_flow(request, org_id):
    org = get_object_or_404(Organization, pk=org_id)
    show_archived = request.GET.get("archived") == "1"
    faculty = (
        OrganizationMembership.objects.filter(
            organization=org,
            role="faculty",
            is_active=not show_archived,
        )
        .select_related("user")
        .order_by("user__first_name", "user__last_name")
    )
    return render(
        request,
        "core_admin_org_users/faculty.html",
        {"org": org, "faculty": faculty, "show_archived": show_archived},
    )


@user_passes_test(lambda u: u.is_superuser)
def faculty_detail(request, org_id, member_id):
    org = get_object_or_404(Organization, pk=org_id)
    membership = get_object_or_404(
        OrganizationMembership, pk=member_id, organization=org, role="faculty"
    )
    return render(
        request,
        "core_admin_org_users/faculty_detail.html",
        {"org": org, "membership": membership},
    )


@user_passes_test(lambda u: u.is_superuser)
def faculty_toggle_active(request, org_id, member_id):
    org = get_object_or_404(Organization, pk=org_id)
    membership = get_object_or_404(
        OrganizationMembership, pk=member_id, organization=org, role="faculty"
    )
    membership.is_active = not membership.is_active
    membership.save(update_fields=["is_active"])
    msg = (
        f"Faculty '{membership.user.get_full_name() or membership.user.username}' "
        f"{'activated' if membership.is_active else 'archived'}."
    )
    messages.success(request, msg)
    url = reverse("admin_org_users_faculty", args=[org.id])
    if request.GET.get("archived") == "1":
        url += "?archived=1"
    return redirect(url)


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
        messages.error(request, "Please provide required fields and a CSV file.")
        if referer:
            return redirect(referer)
        return redirect(
            "admin_org_users_faculty" if is_faculty else "admin_org_users_students",
            org_id=org.id,
        )

    ay = form.cleaned_data["academic_year"].strip()
    class_name = (form.cleaned_data.get("class_name") or "").strip()
    if not is_faculty and not class_name:
        messages.error(request, "Please provide a class for the students.")
        return redirect("admin_org_users_students", org_id=org.id)

    cls = None
    if not is_faculty:
        cls, _ = Class.objects.get_or_create(
            organization=org,
            academic_year=ay,
            code=class_name,
            defaults={"name": class_name, "is_active": True},
        )
        if not cls.is_active:
            cls.is_active = True
            cls.save(update_fields=["is_active"])

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

    rows = list(reader)
    roles_in_csv = set()
    invalid_roles = set()
    for row in rows:
        role_raw = (row.get("role") or "").strip()
        if not role_raw:
            continue
        role_key = role_raw.lower()
        role_name = VALID_ROLES.get(role_key)
        if role_name:
            roles_in_csv.add(role_name)
        else:
            invalid_roles.add(role_raw)

    if invalid_roles:
        messages.error(
            request,
            "Unknown roles in CSV: " + ", ".join(sorted(invalid_roles)),
        )
        return redirect(
            "admin_org_users_faculty" if is_faculty else "admin_org_users_students",
            org_id=org.id,
        )

    for role_name in roles_in_csv:
        OrganizationRole.objects.get_or_create(organization=org, name=role_name)

    with transaction.atomic():
        for i, row in enumerate(rows, start=2):
            reg = (row.get(id_field) or "").strip()
            name = (row.get("name") or "").strip()
            email = (row.get("email") or "").strip().lower()
            role_raw = (row.get("role") or "").strip()
            role_key = role_raw.lower()
            role = VALID_ROLES.get(role_key, role_key)

            if not email or "@" not in email:
                skipped += 1
                errors.append(f"Row {i}: invalid email")
                continue

            org_role = OrganizationRole.objects.filter(
                organization=org, name__iexact=role
            ).first()
            if not org_role:
                messages.error(
                    request,
                    f"Row {i}: role '{role_raw}' not found for this organization."
                    " Please create it first.",
                )
                return redirect(
                    "admin_org_users_faculty"
                    if is_faculty
                    else "admin_org_users_students",
                    org_id=org.id,
                )

            first, last = _split_name(name)

            # Try to find an existing user by email to avoid duplicates when
            # the username differs from the email address (e.g., users who
            # registered manually). If not found, fall back to creating a new
            # user with the email as the username.
            user = User.objects.filter(email__iexact=email).first()
            created = False
            if not user:
                user, created = User.objects.get_or_create(
                    username=email,
                    defaults={
                        "email": email,
                        "first_name": first,
                        "last_name": last,
                        "is_active": False,
                    },
                )
            if created:
                users_created += 1
            else:
                fields_to_update = []
                if not user.first_name and first:
                    user.first_name = first
                    fields_to_update.append("first_name")
                if not user.last_name and last:
                    user.last_name = last
                    fields_to_update.append("last_name")
                if user.email.lower() != email:
                    user.email = email
                    fields_to_update.append("email")
                if fields_to_update:
                    user.save(update_fields=fields_to_update)
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
                defaults={"role": org_role.name, "is_primary": True, "is_active": True},
            )
            if mem_created:
                memberships_created += 1
            else:
                fields_to_update = []
                if mem.role != org_role.name:
                    mem.role = org_role.name
                    fields_to_update.append("role")
                if not mem.is_active:
                    mem.is_active = True
                    fields_to_update.append("is_active")
                if fields_to_update:
                    mem.save(update_fields=fields_to_update)
                    memberships_updated += 1

            RoleAssignment.objects.update_or_create(
                user=user,
                organization=org,
                role=org_role,
                defaults={
                    "academic_year": ay,
                    "class_name": class_name if org_role.name == "student" else None,
                },
            )

            if profile.role != org_role.name:
                profile.role = org_role.name
                profile.save(update_fields=["role"])

            if org_role.name == "student" and cls is not None:
                student_obj, _ = EmtStudent.objects.get_or_create(user=user)
                cls.students.add(student_obj)

    if errors:
        messages.warning(
            request,
            "Some rows were skipped:\n" + "\n".join(errors[:8]) + ("" if len(errors) <= 8 else f"\n(+{len(errors) - 8} more)"),
        )
    if is_faculty:
        messages.success(
            request,
            f"CSV processed for {org.name} ({ay}). Users created: {users_created}, Users updated: {users_updated}, "
            f"Memberships created: {memberships_created}, Memberships updated: {memberships_updated}, Skipped: {skipped}.",
        )
        return redirect("admin_org_users_faculty", org_id=org.id)

    total_students = memberships_created + memberships_updated
    messages.success(
        request,
        f"Uploaded {total_students} students into {class_name} ({ay}).",
    )
    return redirect(
        f"{reverse('class_roster_detail', args=[org.id, class_name])}?year={ay}"
    )


@user_passes_test(lambda u: u.is_superuser)
def class_detail(request, org_id, class_id):
    org = get_object_or_404(Organization, pk=org_id)
    cls = get_object_or_404(Class, pk=class_id, organization=org)
    students = cls.students.select_related("user").order_by(
        "user__first_name", "user__last_name"
    )
    return render(
        request,
        "core_admin_org_users/class_detail.html",
        {"org": org, "cls": cls, "students": students},
    )


@user_passes_test(lambda u: u.is_superuser)
def class_remove_student(request, org_id, class_id, student_id):
    org = get_object_or_404(Organization, pk=org_id)
    cls = get_object_or_404(Class, pk=class_id, organization=org)
    student = get_object_or_404(EmtStudent, pk=student_id)
    if request.method == "POST":
        cls.students.remove(student)
        messages.success(
            request,
            f"Removed {student.user.get_full_name() or student.user.username} from {cls.name}.",
        )
    return redirect("admin_org_users_class_detail", org_id=org.id, class_id=cls.id)


@user_passes_test(lambda u: u.is_superuser)
def class_toggle_active(request, org_id, class_id):
    org = get_object_or_404(Organization, pk=org_id)
    cls = get_object_or_404(Class, pk=class_id, organization=org)
    cls.is_active = not cls.is_active
    cls.save(update_fields=["is_active"])
    msg = f"Class '{cls.name}' {'activated' if cls.is_active else 'archived'}."
    messages.success(request, msg)
    url = reverse("admin_org_users_students", args=[org.id])
    if request.GET.get("archived") == "1":
        url += "?archived=1"
    return redirect(url)


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

