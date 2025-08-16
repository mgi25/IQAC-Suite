import json
import logging
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)

@require_http_methods(["GET", "POST"])
def core_admin_sidebar_permissions(request: HttpRequest) -> HttpResponse:
    """Simple view showing how to handle sidebar permission assignment."""
    users = []  # Fetch from DB
    roles = []  # Fetch from DB
    available_permissions = []  # Fetch from DB
    assigned_permissions = []  # Fetch from DB based on user/role

    if request.method == "POST":
        assigned_order = json.loads(request.POST.get("assigned_order", "[]"))
        user_id = request.POST.get("user_id")
        role_id = request.POST.get("role_id")
        if not user_id and not role_id:
            messages.error(request, "Select a user or role")
            return redirect("core_admin_sidebar_permissions")
        # Save logic
        target = None
        if user_id:
            # target = User.objects.get(pk=user_id)
            pass
        elif role_id:
            # target = Role.objects.get(pk=role_id)
            pass
        if target is not None:
            # target.sidebar_permissions.set(assigned_order, clear=True)
            # target.sidebar_permissions_order = assigned_order
            # target.save()
            logger.info("Updated sidebar permissions for %s", target)
            messages.success(request, "Permissions saved")
        return redirect("core_admin_sidebar_permissions")

    context = {
        "users": users,
        "roles": roles,
        "available_permissions": available_permissions,
        "assigned_permissions": assigned_permissions,
    }
    return render(request, "core_admin/sidebar_permissions.html", context)
