# core/decorators.py

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

def role_required(role):
    def decorator(view_func):
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            # Fetch from Profile, fallback to session if needed
            profile_role = getattr(getattr(request.user, 'profile', None), 'role', None)
            session_role = request.session.get('role')
            if profile_role == role or session_role == role:
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("You do not have permission to access this page.")
        return _wrapped_view
    return decorator
