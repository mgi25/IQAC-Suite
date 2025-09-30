import logging
from typing import Iterable, List, Optional

from django.conf import settings
from django.core.mail import EmailMessage, get_connection

from .models import Organization, OrganizationRole, RoleAssignment

logger = logging.getLogger(__name__)


def send_notification(subject: str, body: str, to: Iterable[str] | str, cc: Optional[Iterable[str]] = None) -> bool:
    """Send an email if EMAIL_NOTIFICATIONS_ENABLED is True.

    Returns True if queued successfully, False otherwise. Logs errors instead of raising.
    """
    if not getattr(settings, "EMAIL_NOTIFICATIONS_ENABLED", True):
        logger.info("Email notifications disabled; skipping: %s", subject)
        return False

    if isinstance(to, str):
        recipients: List[str] = [to]
    else:
        recipients = [r for r in to if r]
    if not recipients:
        logger.warning("send_notification called with no recipients: %s", subject)
        return False

    try:
        connection = get_connection()
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            to=recipients,
            cc=list(cc) if cc else None,
            connection=connection,
        )
        email.content_subtype = "html" if "</" in body else "plain"
        email.send(fail_silently=False)
        logger.info("Email sent: %s -> %s", subject, recipients)
        return True
    except Exception:
        logger.exception("Failed to send email: %s", subject)
        return False


def resolve_role_emails(org: Organization, role_name_contains: str) -> List[str]:
    """Find user emails assigned a role within an organization whose role name contains the token.

    role_name_contains: e.g. 'hod', 'iqac', 'uiqac', 'diqac'
    """
    try:
        token = (role_name_contains or "").lower()
        ras = (
            RoleAssignment.objects.select_related("role", "user")
            .filter(organization=org, role__isnull=False)
        )
        emails = []
        for ra in ras:
            name = (getattr(ra.role, "name", "") or "").lower()
            if token in name:
                email = getattr(ra.user, "email", "") or ""
                if email:
                    emails.append(email)
        return sorted(set(emails))
    except Exception:
        logger.exception("Failed to resolve role emails for org=%s token=%s", org.id if org else None, role_name_contains)
        return []
