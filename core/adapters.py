from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.utils.text import slugify
from django.contrib.auth.models import User
from core.models import Profile

class SchoolSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        Connects to existing user by email (prevents duplicates).
        Lets allauth handle authentication pipeline and redirect.
        """
        email = sociallogin.user.email
        if email:
            try:
                user = User.objects.get(email=email)
                sociallogin.connect(request, user)
                # DO NOT interrupt the pipeline! Do not redirect here.
                return  # Let allauth finish logging in this user
            except User.DoesNotExist:
                pass  # User doesn't exist, will create new one

        # If user does not exist, this is a new signup (sociallogin.user not yet saved)
        role = 'student'  # Set default role for first-time signup (customize as needed)
        user = sociallogin.user
        user.save()
        profile, _ = Profile.objects.get_or_create(user=user)
        if profile.role != role:
            profile.role = role
            profile.save()
        request.session['role'] = role

    def is_auto_signup_allowed(self, request, sociallogin):
        # Always allow Google auto signup (customize if you want domain restriction)
        return True

    def populate_user(self, request, sociallogin, data):
        # Ensures unique username for new users
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
        # Use default login
        return super().login(request, sociallogin)
