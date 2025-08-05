from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in, user_logged_out
from .models import Profile
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
    """Assign either the faculty or student role based on the email address."""
    email = (user.email or "").lower()
    # Determine role purely based on email domain.
    # Any address ending with ``christuniversity.in`` is a student account;
    # everything else defaults to faculty.
    domain = email.split("@")[-1]
    role = "student" if domain.endswith("christuniversity.in") else "faculty"

    profile, _ = Profile.objects.get_or_create(user=user)
    if profile.role != role:
        profile.role = role
        profile.save()
    # Store the role in the session for downstream views if available.
    if request is not None:
        request.session['role'] = role

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