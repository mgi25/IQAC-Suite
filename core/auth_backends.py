from django.contrib.auth.backends import ModelBackend


class AllowInactiveFirstLoginBackend(ModelBackend):
    """Allow users who have never activated to authenticate once.

    Standard ModelBackend refuses to authenticate users with ``is_active`` set
    to ``False``.  When users are bulk uploaded, their accounts start inactive
    and they should be able to log in once to activate themselves.  This backend
    permits authentication for such users while still blocking logins for
    accounts that have been explicitly deactivated after activation.
    """

    def user_can_authenticate(self, user):
        if user.is_active:
            return True
        profile = getattr(user, "profile", None)
        if profile and getattr(profile, "activated_at", None) is None:
            return True
        return False
