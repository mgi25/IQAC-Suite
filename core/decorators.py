# core/decorators.py

import logging
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden

logger = logging.getLogger(__name__)

_LOG_PARSE_ERROR = "Decorator error while parsing request body"


def role_required(role):
    def decorator(view_func):
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            # Fetch from Profile, fallback to session if needed
            profile_role = getattr(
                getattr(request.user, "profile", None), "role", None
            )
            session_role = request.session.get("role")
            if profile_role == role or session_role == role:
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden(
                "You do not have permission to access this page."
            )

        return _wrapped_view

    return decorator


def admin_required(view_func):
    """Decorator that requires user to be a superuser or have admin role."""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not (
            request.user.is_superuser or request.session.get("role") == "admin"
        ):
            raise PermissionDenied("Admin access required")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def _expand_sidebar_ids(items):
    """Return a set with sidebar ids expanded to include parents/aliases."""

    expanded = set()
    for item in items:
        if not item:
            continue
        expanded.add(item)
        if isinstance(item, str) and ":" in item:
            parent, child = item.split(":", 1)
            expanded.add(parent)
            expanded.add(child)
    return expanded


def sidebar_permission_required(item_id):
    """Ensure the user can access a specific sidebar item."""

    if isinstance(item_id, (list, tuple, set)):
        required_ids = _expand_sidebar_ids(item_id)
    else:
        required_ids = _expand_sidebar_ids([item_id])

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_superuser or getattr(request.user, "is_staff", False) or (
                request.session.get("role", "").lower() == "admin"
            ):
                return view_func(request, *args, **kwargs)

            try:
                from .models import SidebarPermission

                allowed = SidebarPermission.get_allowed_items(request.user)
            except Exception:
                logger.exception(
                    "Failed to resolve sidebar permissions for user %s",
                    getattr(request.user, "id", None),
                )
                raise PermissionDenied("Sidebar access required")

            if allowed == "ALL":
                return view_func(request, *args, **kwargs)

            allowed_ids = _expand_sidebar_ids(allowed)

            if required_ids & allowed_ids:
                return view_func(request, *args, **kwargs)

            raise PermissionDenied("Sidebar access required")

        return _wrapped_view

    return decorator


def popso_manager_required(view_func):
    """
    Decorator that checks if user is either a superuser or has an active PO/PSO assignment
    """

    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        # Allow superusers
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        # Check if user has active PO/PSO assignment
        from .models import POPSOAssignment

        has_assignment = POPSOAssignment.objects.filter(
            assigned_user=request.user, is_active=True
        ).exists()

        if has_assignment:
            return view_func(request, *args, **kwargs)

        return HttpResponseForbidden(
            "You don't have permission to manage PO/PSO outcomes."
        )

    return _wrapped_view


def popso_program_access_required(view_func):
    """
    Decorator that checks if user can access a specific program's PO/PSO management
    """

    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        # Allow superusers
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        # Get program ID from request
        program_id = kwargs.get("program_id")

        if not program_id:
            # Try to get from JSON body
            try:
                import json

                data = json.loads(request.body) if request.body else {}
                program_id = data.get("program_id")
            except Exception as exc:
                logger.exception(_LOG_PARSE_ERROR, exc_info=exc)

        if not program_id:
            return HttpResponseForbidden("Program ID required.")

        # Check if user has assignment for this program's organization
        from .models import POPSOAssignment, Program

        try:
            program = Program.objects.get(id=program_id)
            if program.organization:
                has_assignment = POPSOAssignment.objects.filter(
                    assigned_user=request.user,
                    organization=program.organization,
                    is_active=True,
                ).exists()

                if has_assignment:
                    return view_func(request, *args, **kwargs)
        except Program.DoesNotExist:
            pass

        return HttpResponseForbidden(
            "You don't have permission to manage this program's PO/PSO outcomes."
        )

    return _wrapped_view


def prevent_impersonation_of_admins(view_func):
    """Decorator to prevent impersonation of admin users"""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Get the user being impersonated
        user_id = request.POST.get("user_id") or kwargs.get("user_id")
        if user_id:
            try:
                from django.contrib.auth.models import User

                target_user = User.objects.get(id=user_id)
                if target_user.is_superuser:
                    raise PermissionDenied("Cannot impersonate superusers")
            except User.DoesNotExist:
                pass
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def log_impersonation(view_func):
    """Decorator to log impersonation actions"""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        import logging

        logger = logging.getLogger("impersonation")

        result = view_func(request, *args, **kwargs)

        # Log the impersonation
        if hasattr(request, "user") and request.user.is_authenticated:
            if "impersonate_user_id" in request.session:
                logger.info(
                    f"User {request.user.username} (ID: {request.user.id}) "
                    f"impersonating user ID: {request.session['impersonate_user_id']}"
                )

        return result

    return _wrapped_view
