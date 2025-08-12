from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.utils import timezone
from .models import Profile, RoleAssignment
import sys
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    # Skip during loaddata to avoid duplicate errors
    if 'loaddata' in sys.argv:
        return

    if created:
        Profile.objects.create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
        else:
            Profile.objects.create(user=instance)


@receiver(user_logged_in)
def assign_role_on_login(sender, user, request, **kwargs):
    """Assign the user's role for the current organization on login."""

    if request is None:
        return

    org_id = request.session.get("org_id") or request.session.get("organization_id")
    role_assignment = None
    if org_id is not None:
        role_assignment = RoleAssignment.objects.filter(
            user=user, organization_id=org_id
        ).select_related("role").first()
    if role_assignment is None:
        role_assignment = RoleAssignment.objects.filter(user=user).select_related("role").first()

    profile, _ = Profile.objects.get_or_create(user=user)
    update_fields = []

    if role_assignment:
        role_name = role_assignment.role.name
        if profile.role != role_name:
            profile.role = role_name
            update_fields.append("role")
        request.session["role"] = role_name

    if not user.is_active:
        user.is_active = True
        user.save(update_fields=["is_active"])
        profile.activated_at = timezone.now()
        update_fields.append("activated_at")

    if update_fields:
        profile.save(update_fields=update_fields)

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """
    Logs a message when a user logs in.
    """
    logger.info(f"User '{user.username}' (ID: {user.id}) logged in from IP address {request.META.get('REMOTE_ADDR')}.")
    
@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """
    Logs a message when a user logs out.
    """
    # The user object might be None if the session was destroyed before the signal was sent
    if user:
        logger.info(f"User '{user.username}' (ID: {user.id}) logged out.")
