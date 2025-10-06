import logging
import sys

from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import ActivityLog, Profile, RoleAssignment, SidebarModule
from functools import lru_cache
from core import navigation

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    # Skip during loaddata to avoid duplicate errors
    if "loaddata" in sys.argv:
        return

    if created:
        Profile.objects.create(user=instance)
    else:
        if hasattr(instance, "profile"):
            instance.profile.save()
        else:
            Profile.objects.create(user=instance)


@receiver(user_logged_in)
def assign_role_on_login(sender, user, request, **kwargs):
    """Assign the user's session role on login.

    Rules:
    - If an explicit Organization Role assignment exists (respecting selected org in session),
      store session["role"] as key "orgrole:<id>". Profile.role keeps the human-readable name.
    - Else, derive by email domain: *.christuniversity.in -> "student"; otherwise -> "faculty".
    """

    if request is None:
        return

    org_id = request.session.get("org_id") or request.session.get("organization_id")
    role_assignment = None
    if org_id is not None:
        role_assignment = (
            RoleAssignment.objects.filter(user=user, organization_id=org_id)
            .select_related("role")
            .first()
        )
    if role_assignment is None:
        role_assignment = (
            RoleAssignment.objects.filter(user=user).select_related("role").first()
        )

    profile, _ = Profile.objects.get_or_create(user=user)
    update_fields = []

    if role_assignment and role_assignment.role_id:
        # Persist human-readable role name on profile for convenience
        role_name_display = role_assignment.role.name
        session_role_key = f"orgrole:{role_assignment.role_id}"
    else:
        domain = user.email.split("@")[-1].lower() if user.email else ""
        role_name_display = (
            "student" if domain.endswith("christuniversity.in") else "faculty"
        )
        session_role_key = role_name_display

    if profile.role != role_name_display:
        profile.role = role_name_display
        update_fields.append("role")
    request.session["role"] = session_role_key

    if not user.is_active:
        user.is_active = True
        user.save(update_fields=["is_active"])
        profile.activated_at = timezone.now()
        update_fields.append("activated_at")

    if update_fields:
        profile.save(update_fields=update_fields)


@receiver(post_save, sender=RoleAssignment)
def sync_profile_role_on_assignment_save(sender, instance, **kwargs):
    """Keep Profile.role in sync when RoleAssignment is created or updated."""
    role_name = instance.role.name if instance.role else "student"
    profile, _ = Profile.objects.get_or_create(user=instance.user)
    if profile.role != role_name:
        profile.role = role_name
        profile.save(update_fields=["role"])


@receiver(post_delete, sender=RoleAssignment)
def sync_profile_role_on_assignment_delete(sender, instance, **kwargs):
    """Reset Profile.role when a RoleAssignment is removed."""
    profile = Profile.objects.filter(user=instance.user).first()
    if not profile:
        return
    ra = (
        RoleAssignment.objects.filter(user=instance.user).select_related("role").first()
    )
    role_name = ra.role.name if ra and ra.role else "student"
    if profile.role != role_name:
        profile.role = role_name
        profile.save(update_fields=["role"])


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """
    Logs a message when a user logs in.
    """
    ip = request.META.get("REMOTE_ADDR", "unknown")
    ua = request.META.get("HTTP_USER_AGENT", "unknown")
    logger.info(
        f"User '{user.username}' (ID: {user.id}) logged in from IP address {ip} with UA {ua}."
    )
    ActivityLog.objects.create(
        user=user,
        action="login",
        description=(f"User '{user.username}' logged in. IP: {ip}. User-Agent: {ua}."),
        ip_address=ip,
        metadata={"user_agent": ua},
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """
    Logs a message when a user logs out.
    """
    # The user object might be None if the session was destroyed before the signal was sent
    if user:
        ip = request.META.get("REMOTE_ADDR", "unknown")
        ua = request.META.get("HTTP_USER_AGENT", "unknown")
        logger.info(
            f"User '{user.username}' (ID: {user.id}) logged out from IP {ip} with UA {ua}."
        )
        ActivityLog.objects.create(
            user=user,
            action="logout",
            description=(
                f"User '{user.username}' logged out. IP: {ip}. User-Agent: {ua}."
            ),
            ip_address=ip,
            metadata={"user_agent": ua},
        )


# ───────────────────────────────
# SidebarModule cache invalidation
# ───────────────────────────────

def _clear_nav_cache():  # pragma: no cover - simple utility
    try:
        navigation.get_nav_items.cache_clear()
    except Exception:
        pass


@receiver(post_save, sender=SidebarModule)
def sidebar_module_saved(sender, instance, **kwargs):  # pragma: no cover - simple
    _clear_nav_cache()


@receiver(post_delete, sender=SidebarModule)
def sidebar_module_deleted(sender, instance, **kwargs):  # pragma: no cover - simple
    _clear_nav_cache()
