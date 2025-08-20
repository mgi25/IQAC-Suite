from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from emt.models import EventProposal
from transcript.models import get_active_academic_year

from .models import SidebarPermission
from .sidebar import MODULES, normalize_items


def notifications(request):
    """
    Return proposal-related notifications for the logged-in user.

    Logic:
    - Show the user's own proposals.
    - Include proposals that are NOT FINALIZED, or anything updated in the last 2 days.
    - Limit to the 10 most recently updated proposals.
    """
    if not request.user.is_authenticated:
        return {"notifications": []}

    two_days_ago = timezone.now() - timedelta(days=2)

    proposals = (
        EventProposal.objects
        .filter(submitted_by=request.user)
        .filter(
            Q(updated_at__gte=two_days_ago) |
            ~Q(status=EventProposal.Status.FINALIZED)
        )
        .order_by("-updated_at")[:10]
    )

    notif_list = []
    for p in proposals:
        # Build notification payloads compatible with the header dropdown.
        if p.status == EventProposal.Status.REJECTED:
            n_type, icon = "alert", "triangle-exclamation"
        elif p.status in (EventProposal.Status.SUBMITTED, EventProposal.Status.UNDER_REVIEW):
            n_type, icon = "reminder", "clock"
        else:
            n_type, icon = "info", "circle-info"

        notif_list.append({
            "title": p.event_title or "Event Proposal",
            "message": p.get_status_display(),
            "created_at": p.updated_at,
            "icon": icon,
            "type": n_type,
            "is_read": False,  # frontend can toggle this per user-session if needed
        })

    return {"notifications": notif_list}


def active_academic_year(request):
    """Provide the active academic year to all templates."""
    return {"active_academic_year": get_active_academic_year()}


def _full_access_tree():
    """
    Produce a normalized tree that represents FULL access to all sidebar modules.
    normalize_items() accepts MODULES and returns a canonical dict:
        { "module_key": [] } meaning [] = all sub-items
    """
    return normalize_items(MODULES)


def _merge_permission_items(perms_qs):
    """
    Merge a sequence of SidebarPermission records into a single normalized dict.

    Rules:
    - If a module has [] in the merged result, it means FULL access to that module; keep it as [].
    - Otherwise union the allowed sub-items and sort for stability.
    """
    merged = {}
    for perm in perms_qs:
        data = normalize_items(perm.items or [])
        for mod, subs in data.items():
            if mod not in merged:
                merged[mod] = list(subs)
                continue
            # Existing is full access → keep full access
            if merged[mod] == []:
                continue
            # Incoming is full access → override to full access
            if subs == []:
                merged[mod] = []
            else:
                merged[mod] = sorted(set(merged[mod]) | set(subs))
    return merged


def sidebar_permissions(request):
    """
    Provide allowed sidebar items for the current user or role.

    Returns (all keys always present for template simplicity):
      - allowed_nav_tree: dict normalized hierarchical structure used by base.html
      - allowed_nav_items: legacy flat list for backward checks (derived from tree)
      - sidebar_modules: original MODULES for rendering (unchanged)

    Precedence for permission records (highest → lowest):
      1) user@organization
      2) user (global)
      3) role@organization
      4) role (global)

    Special cases:
      - Unauthenticated: no access (None values)
      - Superuser or session role 'admin': full access to everything
    """
    context = {
        "allowed_nav_items": None,
        "allowed_nav_tree": None,
        "sidebar_modules": MODULES,
    }

    if not request.user.is_authenticated:
        return context

    user = request.user
    # Pull role from session first; fall back to user.profile.role if present
    role = request.session.get("role") or getattr(getattr(user, "profile", None), "role", "")
    org_id = request.session.get("active_organization_id")

    # Superuser or explicit admin role → full access
    if user.is_superuser or (role and str(role).lower() == "admin"):
        tree = _full_access_tree()
        flat = sorted(tree.keys()) if tree else []
        context.update({
            "allowed_nav_tree": tree,
            "allowed_nav_items": flat,
        })
        return context

    # Build precedence-ordered list of queries and evaluate each separately
    # (Using separate queries avoids DB-specific UNION requirements and is clearer.)
    perms_ordered = []

    # 1) user@organization
    if org_id:
        perms_ordered.extend(
            SidebarPermission.objects.filter(user=user, organization_id=org_id)
        )

    # 2) user (global)
    perms_ordered.extend(
        SidebarPermission.objects.filter(user=user, organization__isnull=True)
    )

    # 3) role@organization
    if role and org_id:
        perms_ordered.extend(
            SidebarPermission.objects.filter(role=role, organization_id=org_id)
        )

    # 4) role (global)
    if role:
        perms_ordered.extend(
            SidebarPermission.objects.filter(role=role, organization__isnull=True)
        )

    merged = _merge_permission_items(perms_ordered)

    # If nothing matched, default to no access (None) letting templates fall back gracefully.
    # If you want a safer default (e.g., hide nothing), comment below and set merged = _full_access_tree()
    if merged:
        flat = sorted(merged.keys())
        context.update({
            "allowed_nav_tree": merged,
            "allowed_nav_items": flat,
        })

    return context
