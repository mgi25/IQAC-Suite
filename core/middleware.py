from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from core.models import RoleAssignment
from emt.models import Student
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model

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
        return RoleAssignment.objects.filter(user=user).exists()

class ImpersonationMiddleware:
    """Middleware to handle user impersonation"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if we're impersonating a user
        if request.user.is_authenticated and 'impersonate_user_id' in request.session:
            try:
                # Get the impersonated user
                impersonated_user = User.objects.get(
                    id=request.session['impersonate_user_id'],
                    is_active=True
                )
                
                # Store original user for reference
                request.original_user = request.user
                
                # Replace request.user with impersonated user
                request.user = impersonated_user
                
                # Add flag to indicate impersonation
                request.is_impersonating = True
                
            except User.DoesNotExist:
                # Clean up invalid session data
                if 'impersonate_user_id' in request.session:
                    del request.session['impersonate_user_id']
                if 'original_user_id' in request.session:
                    del request.session['original_user_id']
        else:
            request.is_impersonating = False
            request.original_user = None

        response = self.get_response(request)
        return response