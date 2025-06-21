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

        if not domain.endswith(ALLOWED_DOMAIN):
            messages.error(request, f"Only @{ALLOWED_DOMAIN} emails are allowed. You used: {email}")
            raise ImmediateHttpResponse(redirect(reverse('account_login')))

    def is_auto_signup_allowed(self, request, sociallogin):
        return True

    def login(self, request, sociallogin):
        return super().login(request, sociallogin)
