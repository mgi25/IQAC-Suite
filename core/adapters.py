from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.utils.text import slugify
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from allauth.exceptions import ImmediateHttpResponse

class SchoolSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        email = sociallogin.user.email
        domain = email.split('@')[-1].lower() if email else ''

        # ✅ Show error if not a CHRIST University email
        if not (domain.endswith('christuniversity.in') or domain.endswith('bcah.christuniversity.in')):
            messages.error(request, f"Only CHRIST University emails are allowed. You used: {email}")
            raise ImmediateHttpResponse(redirect(reverse('account_login')))

        # Auto-assign role: faculty if christuniversity.in, student otherwise
        if domain.endswith('christuniversity.in'):
            role = 'faculty'
        else:
            role = 'student'

        # Save role to Profile (creates if not exists)
        user = sociallogin.user
        user.save()
        from core.models import Profile
        profile, created = Profile.objects.get_or_create(user=user)
        if profile.role != role:
            profile.role = role
            profile.save()

        # Store role in session
        request.session['role'] = role

    def is_auto_signup_allowed(self, request, sociallogin):
        return True

    def populate_user(self, request, sociallogin, data):
        # Ensures username is unique from email prefix
        user = super().populate_user(request, sociallogin, data)
        base_username = slugify(user.email.split('@')[0])
        username = base_username
        count = 0
        while User.objects.filter(username=username).exists():
            count += 1
            username = f"{base_username}{count}"
        user.username = username
        return user

    def login(self, request, sociallogin):
        return super().login(request, sociallogin)
