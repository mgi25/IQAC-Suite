import logging
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from emt.models import EventProposal
from transcript.models import get_active_academic_year

from .models import RoleAssignment, SidebarPermission

logger = logging.getLogger(__name__)


def notifications(request):
    """Return proposal-related notifications for the logged-in user."""
    if not request.user.is_authenticated:
        return {}

    two_days_ago = timezone.now() - timedelta(days=2)
    proposals = (
        EventProposal.objects.filter(submitted_by=request.user)
        .filter(
            ~Q(status=EventProposal.Status.FINALIZED) | Q(updated_at__gte=two_days_ago)
        )
        .order_by("-updated_at")[:10]
    )

    notif_list = []
    for p in proposals:
        """Build notification payloads compatible with the header dropdown."""
        if p.status == EventProposal.Status.REJECTED:
            n_type = "alert"
            icon = "triangle-exclamation"
        elif p.status in [
            EventProposal.Status.SUBMITTED,
            EventProposal.Status.UNDER_REVIEW,
        ]:
            n_type = "reminder"
            icon = "clock"
        else:
            n_type = "info"
            icon = "circle-info"

        notif_list.append(
            {
                "title": p.event_title or "Event Proposal",
                "message": p.get_status_display(),
                "created_at": p.updated_at,
                "icon": icon,
                "type": n_type,
                "is_read": False,
            }
        )

    return {"notifications": notif_list}


def active_academic_year(request):
    """Provide the active academic year to all templates."""
    return {"active_academic_year": get_active_academic_year()}


def sidebar_permissions(request):
    """Provide allowed sidebar items for the current user.

    Logic overview:
    - Superusers/admins: unrestricted.
    - User-specific permissions (role empty) override everything.
    - Otherwise merge sidebar items for all ``RoleAssignment`` records using
      ``SidebarPermission`` entries with ``role=orgrole:<id>``.
    - If no role-based records exist, fallback to the legacy session ``role``
      and finally to the faculty baseline.
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
        return sorted(expanded)

    # 1) User-specific override
    user_perm = SidebarPermission.objects.filter(
        user=request.user, role__in=["", None]
    ).first()
    if user_perm:
        try:
            logger.debug(
                "sidebar_permissions CP: user=%s override items=%s",
                request.user.id,
                user_perm.items,
            )
        except Exception:
            pass
        return {
            "allowed_nav_items": _expand_with_parents(user_perm.items),
            "unrestricted_nav": False,
        }

    # 2) Merge permissions from all assigned organization roles
    role_items = set()
    role_ids = RoleAssignment.objects.filter(user=request.user).values_list(
        "role_id", flat=True
    )
    if role_ids:
        role_keys = [f"orgrole:{rid}" for rid in role_ids]
        for perm in SidebarPermission.objects.filter(
            user__isnull=True, role__in=role_keys
        ):
            role_items.update(perm.items)
    try:
        logger.debug(
            "sidebar_permissions CP: user=%s role_ids=%s merged_items=%s session_role=%s",
            request.user.id,
            list(role_ids),
            sorted(role_items),
            request.session.get("role"),
        )
    except Exception:
        pass

    # 3) Legacy session role with faculty fallback
    session_role = (request.session.get("role") or "").strip()
    if session_role.lower() == "admin":
        return {"allowed_nav_items": [], "unrestricted_nav": True}

    if session_role:
        perm = SidebarPermission.objects.filter(
            user__isnull=True, role__iexact=session_role
        ).first()
        if perm:
            role_items.update(perm.items)

    if not role_items:
        perm = SidebarPermission.objects.filter(
            user__isnull=True, role__iexact="faculty"
        ).first()
        if perm:
            role_items.update(perm.items)

    if role_items:
        try:
            logger.debug(
                "sidebar_permissions CP: user=%s final allowed=%s",
                request.user.id,
                sorted(role_items),
            )
        except Exception:
            pass
        return {
            "allowed_nav_items": _expand_with_parents(sorted(role_items)),
            "unrestricted_nav": False,
        }

    try:
        logger.debug(
            "sidebar_permissions CP: user=%s default none (no role/org or perms)",
            request.user.id,
        )
    except Exception:
        pass
    return {"allowed_nav_items": [], "unrestricted_nav": False}
