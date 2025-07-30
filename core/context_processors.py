from django.utils import timezone
from django.utils.timesince import timesince
from emt.models import EventProposal


def notifications(request):
    """Return proposal-related notifications for the logged-in user."""
    if not request.user.is_authenticated:
        return {}

    proposals = (
        EventProposal.objects
        .filter(submitted_by=request.user)
        .order_by('-updated_at')[:5]
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
