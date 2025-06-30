# # core/adapters.py

# from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
# from django.contrib import messages
# from django.shortcuts import redirect
# from django.urls import reverse
# from allauth.exceptions import ImmediateHttpResponse

# ALLOWED_DOMAIN = 'christuniversity.in'

# class SchoolSocialAccountAdapter(DefaultSocialAccountAdapter):
#     def pre_social_login(self, request, sociallogin):
#         email = sociallogin.user.email
#         domain = email.split('@')[-1].lower() if email else ''

#         # Only allow christuniversity.in emails
#         if not domain.endswith(ALLOWED_DOMAIN):
#             messages.error(request, f"Only @{ALLOWED_DOMAIN} emails are allowed. You used: {email}")
#             raise ImmediateHttpResponse(redirect(reverse('account_login')))
        
#         # Determine role based on email pattern
#         local_part, at, domain_part = email.partition('@')
#         sub_parts = domain_part.split('.')
#         role = 'student' if len(sub_parts) > 2 else 'faculty'

#         # Save role to Profile (creates if not exists)
#         user = sociallogin.user
#         user.save()
#         from core.models import Profile
#         profile, created = Profile.objects.get_or_create(user=user)
#         profile.role = role
#         profile.save()

#         # (optional) still set to session
#         request.session['role'] = role

#     def is_auto_signup_allowed(self, request, sociallogin):
#         return True

#     def login(self, request, sociallogin):
#         return super().login(request, sociallogin)


#short time logic
# core/adapters.py

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.utils.text import slugify
from django.contrib.auth.models import User

class SchoolSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        email = sociallogin.user.email
        domain = email.split('@')[-1].lower() if email else ''

        # -------- DISABLED domain restriction for development/testing --------
        # ALLOWED_DOMAIN = 'christuniversity.in'
        # if not domain.endswith(ALLOWED_DOMAIN):
        #     messages.error(request, f"Only @{ALLOWED_DOMAIN} emails are allowed. You used: {email}")
        #     raise ImmediateHttpResponse(redirect(reverse('account_login')))
        # --------------------------------------------------------------------

        # Assign role: faculty if christuniversity.in, student otherwise
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

        # (Optional) Also store role in session for reference
        request.session['role'] = role

    def is_auto_signup_allowed(self, request, sociallogin):
        return True

    def populate_user(self, request, sociallogin, data):
        """
        Ensures that the created user's username is unique,
        based on the email prefix, appending a number if necessary.
        """
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
        # No changes here, just use default logic
        return super().login(request, sociallogin)
