from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from core.models import OrganizationMembership

from .models import JoinRequest


def _current_academic_year_string():
    now = timezone.now()
    start_year = now.year if now.month >= 6 else now.year - 1
    end_year = start_year + 1
    return f"{start_year}-{end_year}"


@staff_member_required
@require_http_methods(["GET", "POST"])
def join_requests(request):
    if request.method == "POST":
        join_request_id = request.POST.get("request_id")
        action = request.POST.get("action")
        response_message = (request.POST.get("response_message") or "").strip()

        join_request = get_object_or_404(
            JoinRequest.objects.select_related("user", "organization"), pk=join_request_id
        )

        if action == "approve":
            _approve_join_request(request, join_request, response_message)
        elif action == "reject":
            _reject_join_request(request, join_request, response_message)
        elif action == "mark_seen":
            _mark_request_seen(request, join_request)
        else:
            messages.error(request, "Unknown action submitted.")

        return redirect("usermanagement:join_requests")

    status_filter = request.GET.get("status")
    queryset = JoinRequest.objects.select_related(
        "user",
        "organization",
        "organization__org_type",
    ).order_by("-requested_on")

    valid_statuses = {choice[0] for choice in JoinRequest.STATUS_CHOICES}
    if status_filter in valid_statuses or status_filter == "Seen":
        if status_filter == "Seen":
            queryset = queryset.filter(status=JoinRequest.STATUS_PENDING, is_seen=True)
        else:
            queryset = queryset.filter(status=status_filter)
    else:
        status_filter = "All"

    context = {
        "join_requests": queryset,
        "status_filter": status_filter,
        "status_choices": [choice[0] for choice in JoinRequest.STATUS_CHOICES] + ["Seen"],
        "pending_count": JoinRequest.objects.filter(status=JoinRequest.STATUS_PENDING, is_seen=False).count(),
    }
    return render(request, "usermanagement/join_requests.html", context)


def _approve_join_request(request, join_request, response_message):
    with transaction.atomic():
        if join_request.request_type == JoinRequest.TYPE_LEAVE:
            membership = (
                OrganizationMembership.objects.filter(
                    user=join_request.user,
                    organization=join_request.organization,
                    is_active=True,
                )
                .select_for_update()
                .first()
            )

            if membership:
                membership.is_active = False
                membership.save(update_fields=["is_active"])
            else:
                OrganizationMembership.objects.filter(
                    user=join_request.user,
                    organization=join_request.organization,
                ).update(is_active=False)

            success_message = (
                f"Approved leave request for {join_request.user.get_full_name() or join_request.user.username}."
            )
        else:
            academic_year = _current_academic_year_string()
            membership, created = OrganizationMembership.objects.get_or_create(
                user=join_request.user,
                organization=join_request.organization,
                academic_year=academic_year,
                defaults={"role": "student", "is_active": True},
            )

            if not created:
                membership.role = membership.role or "student"
                membership.is_active = True
                membership.academic_year = academic_year
                membership.save(update_fields=["role", "is_active", "academic_year"])

            success_message = (
                f"Approved join request for {join_request.user.get_full_name() or join_request.user.username}."
            )

        join_request.status = JoinRequest.STATUS_APPROVED
        join_request.is_seen = False
        join_request.response_message = response_message
        join_request.save(update_fields=["status", "is_seen", "response_message", "updated_on"])

    messages.success(request, success_message)


def _reject_join_request(request, join_request, response_message):
    join_request.status = JoinRequest.STATUS_REJECTED
    join_request.is_seen = False
    join_request.response_message = response_message
    join_request.save(update_fields=["status", "is_seen", "response_message", "updated_on"])
    messages.info(
        request,
        f"Rejected {join_request.get_request_type_display().lower()} request for {join_request.user.get_full_name() or join_request.user.username}.",
    )


def _mark_request_seen(request, join_request):
    if not join_request.is_seen:
        join_request.is_seen = True
        join_request.save(update_fields=["is_seen", "updated_on"])
        messages.success(request, "Marked request as seen.")
    else:
        messages.info(request, "Request already marked as seen.")
