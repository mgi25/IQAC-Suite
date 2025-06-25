from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from allauth.exceptions import ImmediateHttpResponse

ALLOWED_DOMAIN = 'christuniversity.in'

class SchoolSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        email = sociallogin.user.email
        domain = email.split('@')[-1].lower() if email else ''

        # Only allow christuniversity.in emails
        if not domain.endswith(ALLOWED_DOMAIN):
            messages.error(request, f"Only @{ALLOWED_DOMAIN} emails are allowed. You used: {email}")
            raise ImmediateHttpResponse(redirect(reverse('account_login')))
        
        # Determine role (student/faculty) based on email
        local_part, at, domain_part = email.partition('@')
        sub_parts = domain_part.split('.')
        # sub_parts: e.g. ['bscdsh', 'christuniversity', 'in']

        if len(sub_parts) > 2:
            # Subdomain exists: treat as student
            request.session['role'] = 'student'
        else:
            # No subdomain: treat as faculty
            request.session['role'] = 'faculty'

        # Optionally, store this on the user object if you have a profile model etc.
        # sociallogin.user.role = ...

    def is_auto_signup_allowed(self, request, sociallogin):
        return True

    def login(self, request, sociallogin):
        return super().login(request, sociallogin)
