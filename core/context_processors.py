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
    """Provide allowed sidebar items for the current user.

    Rules (requested):
    - Superusers/admins: unrestricted.
    - Else: resolve by session["role"]. If that's an org role key (orgrole:<id>),
      use that record; else treat it as a plain baseline label (student/faculty).
    - If no record exists for the resolved role, fallback to faculty baseline.
    - User-specific (role empty) overrides all of the above.
    """

    # Anonymous users: nothing and restricted
    if not request.user.is_authenticated:
        return {"allowed_nav_items": [], "unrestricted_nav": False}

    # Superusers: unrestricted; keep allowed_nav_items as [] for backward compat
    if request.user.is_superuser:
        return {"allowed_nav_items": [], "unrestricted_nav": True}

    def _expand_with_parents(ids):
        if not ids:
            return ids
        expanded = set(ids)
        for item in list(ids):
            if ":" in item:
                parent = item.split(":", 1)[0]
                expanded.add(parent)
        # Add leaf aliases for legacy template checks
        expanded.update({item.split(":", 1)[1] for item in ids if ":" in item})
        return list(expanded)

    # 1) User-specific override
    user_perm = SidebarPermission.objects.filter(user=request.user, role__in=["", None]).first()
    if user_perm:
        return {"allowed_nav_items": _expand_with_parents(user_perm.items), "unrestricted_nav": False}

    # 2) Role from session, with fallback to faculty
    session_role = (request.session.get("role") or "").strip()
    role_perm = None
    if session_role:
        role_perm = SidebarPermission.objects.filter(user__isnull=True, role=session_role).first()

    if not role_perm:
        # Faculty baseline fallback
        role_perm = SidebarPermission.objects.filter(user__isnull=True, role="faculty").first()

    if role_perm:
        return {"allowed_nav_items": _expand_with_parents(role_perm.items), "unrestricted_nav": False}

    return {"allowed_nav_items": [], "unrestricted_nav": False}

