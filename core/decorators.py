# core/decorators.py

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from functools import wraps
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

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

def admin_required(view_func):
    """Decorator that requires user to be admin (staff or superuser)"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied("Admin access required")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def popso_manager_required(view_func):
    """
    Decorator that checks if user is either a superuser or has an active PO/PSO assignment
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        # Allow superusers
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Check if user has active PO/PSO assignment
        from .models import POPSOAssignment
        has_assignment = POPSOAssignment.objects.filter(
            assigned_user=request.user,
            is_active=True
        ).exists()
        
        if has_assignment:
            return view_func(request, *args, **kwargs)
        
        return HttpResponseForbidden("You don't have permission to manage PO/PSO outcomes.")
    
    return _wrapped_view

def popso_program_access_required(view_func):
    """
    Decorator that checks if user can access a specific program's PO/PSO management
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        # Allow superusers
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Get program ID from request
        program_id = kwargs.get('program_id')
        
        if not program_id:
            # Try to get from JSON body
            try:
                import json
                data = json.loads(request.body) if request.body else {}
                program_id = data.get('program_id')
            except:
                pass
        
        if not program_id:
            return HttpResponseForbidden("Program ID required.")
        
        # Check if user has assignment for this program's organization
        from .models import POPSOAssignment, Program
        try:
            program = Program.objects.get(id=program_id)
            if program.organization:
                has_assignment = POPSOAssignment.objects.filter(
                    assigned_user=request.user,
                    organization=program.organization,
                    is_active=True
                ).exists()
                
                if has_assignment:
                    return view_func(request, *args, **kwargs)
        except Program.DoesNotExist:
            pass
        
        return HttpResponseForbidden("You don't have permission to manage this program's PO/PSO outcomes.")
    
    return _wrapped_view

def prevent_impersonation_of_admins(view_func):
    """Decorator to prevent impersonation of admin users"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Get the user being impersonated
        user_id = request.POST.get('user_id') or kwargs.get('user_id')
        if user_id:
            try:
                from django.contrib.auth.models import User
                target_user = User.objects.get(id=user_id)
                if target_user.is_superuser:
                    raise PermissionDenied("Cannot impersonate superusers")
            except User.DoesNotExist:
                pass
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def log_impersonation(view_func):
    """Decorator to log impersonation actions"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        import logging
        logger = logging.getLogger('impersonation')
        
        result = view_func(request, *args, **kwargs)
        
        # Log the impersonation
        if hasattr(request, 'user') and request.user.is_authenticated:
            if 'impersonate_user_id' in request.session:
                logger.info(
                    f"User {request.user.username} (ID: {request.user.id}) "
                    f"impersonating user ID: {request.session['impersonate_user_id']}"
                )
        
        return result
    return _wrapped_view