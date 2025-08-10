from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from core.models import Organization


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
    # TODO: parse CSV, create/update users + OrganizationMembership
    return redirect("admin_org_users_students", org_id=org.id)


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

