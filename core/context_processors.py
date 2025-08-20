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


def sidebar_permissions(request):
    """Provide allowed sidebar items for the current user or role."""
    if not request.user.is_authenticated:
        return {"allowed_nav_items": []}

    if request.user.is_superuser or request.session.get("role") == "admin":
        return {"allowed_nav_items": []}

    items = []
    perm = SidebarPermission.objects.filter(user=request.user).first()
    if perm and isinstance(perm.items, list):
        items = perm.items
    else:
        role = request.session.get("role")
        if role:
            perm = SidebarPermission.objects.filter(role=role).first()
            if perm and isinstance(perm.items, list):
                items = perm.items

    return {"allowed_nav_items": items}
