from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.text import slugify
from django.contrib.auth.models import User
from core.models import RoleAssignment
from emt.models import Student

class SchoolSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """Allow login only for pre-existing users.

        If a user tries to authenticate with an email that is not present in
        the system, we block the login attempt and redirect them back to the
        login page with an error message. This prevents unregistered users from
        creating accounts simply by logging in with Google and avoids role
        conflicts when administrators later import users in bulk.
        """
        email = sociallogin.user.email
        if email:
            try:
                user = User.objects.get(email=email)
                sociallogin.connect(request, user)
                return
            except User.DoesNotExist:
                if request and hasattr(request, "_messages"):
                    messages.error(request, "Account does not exist. Contact administrator.")
                raise ImmediateHttpResponse(redirect('login'))

        if request and hasattr(request, "_messages"):
            messages.error(request, "Invalid login attempt. Contact administrator.")
        raise ImmediateHttpResponse(redirect('login'))

    def is_auto_signup_allowed(self, request, sociallogin):
        return True

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        base_username = slugify(user.email.split('@')[0])
        username = base_username
        count = 0
        # Ensure the username is unique
        while User.objects.filter(username=username).exists():
            count += 1
            username = f"{base_username}{count}"
        user.username = username
        return user

    def login(self, request, sociallogin):
        return super().login(request, sociallogin)


class RoleBasedAccountAdapter(DefaultAccountAdapter):
    """Redirect users based on their role after login."""

    def get_login_redirect_url(self, request):
        user = request.user
        if user.is_superuser:
            return reverse('admin_dashboard')
        domain = user.email.split('@')[-1].lower() if user.email else ''
        if domain.endswith('christuniversity.in'):
            try:
                student = user.student_profile
            except Student.DoesNotExist:
                return reverse('registration_form')
            if not getattr(student, 'registration_number', ''):
                return reverse('registration_form')
        if not RoleAssignment.objects.filter(user=user).exists():
            return reverse('registration_form')
        return reverse('dashboard')
