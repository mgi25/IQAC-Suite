from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from core.models import RoleAssignment
from emt.models import Student
from django.contrib.auth import get_user_model


class ImpersonationMiddleware:
    """Swap ``request.user`` when admin impersonates another user.

    If ``request.session['impersonate_user_id']`` is present, we fetch the
    target user and make subsequent code see that user as the authenticated
    ``request.user``.  The original user (the admin) is exposed via
    ``request.original_user`` and ``request.actor`` so views can attribute
    any changes to the admin rather than the impersonated account.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.is_impersonating = False
        request.original_user = None
        request.actor = request.user

        impersonate_id = request.session.get("impersonate_user_id")
        if impersonate_id:
            UserModel = get_user_model()
            try:
                target = UserModel.objects.get(id=impersonate_id)
            except UserModel.DoesNotExist:
                request.session.pop("impersonate_user_id", None)
            else:
                request.original_user = request.user
                request.user = target
                request.actor = request.original_user
                request.is_impersonating = True

        response = self.get_response(request)
        return response

class RegistrationRequiredMiddleware:
    """Redirect authenticated users to the registration form until they register."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and not user.is_superuser and not self._is_exempt_path(request.path):
            if not self._user_is_registered(user):
                return redirect('registration_form')
        return self.get_response(request)

    def _is_exempt_path(self, path):
        """Return True if the path should bypass registration enforcement."""
        exempt_paths = {
            reverse('registration_form'),
            reverse('logout'),
            reverse('login'),
            reverse('api_organizations'),
            reverse('api_roles'),
        }
        if path in exempt_paths:
            return True
        exempt_prefixes = (
            '/accounts/',
            '/admin/',
            '/core-admin/',
            settings.STATIC_URL,
            settings.MEDIA_URL,
        )
        return any(path.startswith(prefix) for prefix in exempt_prefixes)

    def _user_is_registered(self, user):
        """Check whether the user has completed registration."""
        domain = user.email.split('@')[-1].lower() if user.email else ''
        is_student = domain.endswith('christuniversity.in')
        if is_student:
            try:
                student = user.student_profile
            except Student.DoesNotExist:
                return False
            if not student.registration_number:
                return False
        profile = getattr(user, "profile", None)
        if profile and profile.role:
            return True
        return RoleAssignment.objects.filter(user=user).exists()
