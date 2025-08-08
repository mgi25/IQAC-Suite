from django.utils import timezone
from django.utils.timesince import timesince
from django.db.models import Q
from datetime import timedelta
from emt.models import EventProposal

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
        # Determine notification type based on status
        if p.status == EventProposal.Status.REJECTED:
            n_type = 'alert'
        elif p.status in [EventProposal.Status.SUBMITTED, EventProposal.Status.UNDER_REVIEW]:
            n_type = 'reminder'
        else:
            n_type = 'info'
        message = f"{p.event_title or 'Event Proposal'} - {p.get_status_display()}"
        time_label = timesince(p.updated_at, timezone.now()) + ' ago'
        notif_list.append({'type': n_type, 'msg': message, 'time': time_label})

    return {'notifications': notif_list}