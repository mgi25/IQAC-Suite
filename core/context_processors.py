from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from emt.models import EventProposal
from transcript.models import get_active_academic_year
from .models import SidebarPermission
from .sidebar import MODULES, normalize_items

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


def sidebar_permissions(request):
    """Provide allowed sidebar items for the current user or role.

    Returns:
      allowed_nav_tree: dict normalized hierarchical structure used by base.html
      allowed_nav_items: legacy flat list for backward checks (derived from tree)
    """
    if not request.user.is_authenticated:
        return {"allowed_nav_items": None, "allowed_nav_tree": None, "sidebar_modules": MODULES}

    user = request.user
    role = request.session.get("role") or getattr(getattr(user, 'profile', None), 'role', '')
    org_id = request.session.get("active_organization_id")  # optional, if your app sets this

    # Fetch in precedence order: user@org, user global, role@org, role global
    perms_qs = SidebarPermission.objects.none()
    try:
        q = SidebarPermission.objects
        filters = []
        if org_id:
            filters.append(q.filter(user=user, organization_id=org_id))
            filters.append(q.filter(role=role or '', organization_id=org_id))
        filters.append(q.filter(user=user, organization__isnull=True))
        filters.append(q.filter(role=role or '', organization__isnull=True))
        perms_qs = filters[0]
        for extra in filters[1:]:
            perms_qs = perms_qs.union(extra)
    except Exception:
        pass

    # Merge items: later entries have lower precedence; apply in our desired order
    merged: dict = {}
    for p in perms_qs:
        data = normalize_items(p.items)
        for mod, subs in data.items():
            if mod not in merged:
                merged[mod] = list(subs)
            else:
                # If existing is [], it means full access, keep []
                if merged[mod] == []:
                    continue
                if subs == []:
                    merged[mod] = []
                else:
                    merged[mod] = sorted(list(set(merged[mod]) | set(subs)))

    # Legacy flat list for old checks
    flat = sorted(merged.keys()) if merged else None
    return {
        "allowed_nav_items": flat,
        "allowed_nav_tree": merged or None,
        "sidebar_modules": MODULES,
    }
