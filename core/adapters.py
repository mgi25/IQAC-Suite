from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify

from core.models import Profile


class SchoolSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """Connect to existing user if email matches, otherwise allow signup."""
        email = sociallogin.user.email
        if not email:
            return
        try:
            user = User.objects.get(email=email)
            sociallogin.connect(request, user)
        except User.DoesNotExist:
            # New email; allow the social login flow to continue which will
            # create a new user account.
            pass

    def is_auto_signup_allowed(self, request, sociallogin):
        return True

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        base_username = slugify(user.email.split("@")[0])
        username = base_username
        count = 0
        # Ensure the username is unique
        while User.objects.filter(username=username).exists():
            count += 1
            username = f"{base_username}{count}"
        user.username = username
        return user

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)
        profile, _ = Profile.objects.get_or_create(user=user)
        domain = user.email.split("@")[-1].lower() if user.email else ""
        role = (
            "student" if domain.endswith("christuniversity.in") else "faculty"
        )
        if profile.role != role:
            profile.role = role
            profile.save(update_fields=["role"])
        return user

    def login(self, request, sociallogin):
        return super().login(request, sociallogin)


class RoleBasedAccountAdapter(DefaultAccountAdapter):
    """Redirect users based on their role after login.

    Also permits users created via bulk upload to log in once even if their
    ``is_active`` flag is ``False``.  Upon that first login the signal
    ``user_logged_in`` will activate the account.
    """

    def pre_login(
        self,
        request,
        user,
        *,
        email_verification,
        signal_kwargs,
        email,
        signup,
        redirect_url,
    ):
        """Allow first-time inactive users to proceed with login."""
        if not user.is_active:
            profile = getattr(user, "profile", None)
            if not (
                profile and getattr(profile, "activated_at", None) is None
            ):
                return self.respond_user_inactive(request, user)

    def get_login_redirect_url(self, request):
        user = request.user
        if user.is_superuser:
            return reverse("admin_dashboard")
        return reverse("dashboard")
