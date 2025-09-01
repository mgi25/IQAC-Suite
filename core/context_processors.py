from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from emt.models import EventProposal
from transcript.models import get_active_academic_year
from .models import SidebarPermission

def notifications(request):
    """Return proposal-related notifications for the logged-in user."""
    if not request.user.is_authenticated:
        return {}

    two_days_ago = timezone.now() - timedelta(days=2)
    proposals = (
        EventProposal.objects
        .filter(submitted_by=request.user)
        .filter(
            ~Q(status=EventProposal.Status.FINALIZED) |
            Q(updated_at__gte=two_days_ago)
        )
        .order_by('-updated_at')[:10]
    )

    notif_list = []
    for p in proposals:
        """Build notification payloads compatible with the header dropdown."""
        if p.status == EventProposal.Status.REJECTED:
            n_type = 'alert'
            icon = 'triangle-exclamation'
        elif p.status in [EventProposal.Status.SUBMITTED, EventProposal.Status.UNDER_REVIEW]:
            n_type = 'reminder'
            icon = 'clock'
        else:
            n_type = 'info'
            icon = 'circle-info'

        notif_list.append({
            'title': p.event_title or 'Event Proposal',
            'message': p.get_status_display(),
            'created_at': p.updated_at,
            'icon': icon,
            'type': n_type,
            'is_read': False,
        })

    return {'notifications': notif_list}


def active_academic_year(request):
    """Provide the active academic year to all templates."""
    return {"active_academic_year": get_active_academic_year()}

from .models import SidebarPermission, RoleAssignment

def sidebar_permissions(request):
    """Provide allowed sidebar items for the current user or role."""

    if not request.user.is_authenticated:
        return {"allowed_nav_items": []}  # nothing for anonymous

    # Superusers/admins always see everything
    if request.user.is_superuser or request.session.get("role", "").lower() == "admin":
        return {"allowed_nav_items": None}  # None = unrestricted

    items = []

    # --- Check user-specific permissions first ---
    user_perm = SidebarPermission.objects.filter(
        user=request.user, role__in=["", None]
    ).first()
    if user_perm:
        items = user_perm.items
    else:
        # --- If no user-specific, check role-based permissions ---
        session_role = request.session.get("role")

        # If role not already cached in session, derive it
        if not session_role:
            roles = RoleAssignment.objects.filter(user=request.user).select_related("role")
            role_names = [ra.role.name.lower() for ra in roles]

            email = (request.user.email or "").lower()
            if "student" in role_names or email.endswith("@christuniversity.in"):
                session_role = "student"
            elif "faculty" in role_names:
                session_role = "faculty"
            else:
                session_role = "faculty"  # default fallback

            request.session["role"] = session_role

        # Check for role-based sidebar permissions
        role_perm = SidebarPermission.objects.filter(
            user__isnull=True, role__iexact=session_role
        ).first()
        if role_perm:
            items = role_perm.items
    print("Allowed items for", request.user.username, "=>", items)
    return {"allowed_nav_items": items}

