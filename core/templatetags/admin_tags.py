from django import template
from django.contrib.auth.models import User

register = template.Library()

@register.inclusion_tag('partials/impersonation_banner.html', takes_context=True)
def impersonation_banner(context):
    """Display impersonation banner"""
    request = context['request']
    return {
        'is_impersonating': getattr(request, 'is_impersonating', False),
        'impersonated_user': request.user if getattr(request, 'is_impersonating', False) else None,
        'original_user': getattr(request, 'original_user', None),
    }

@register.simple_tag
def can_impersonate(user):
    """Check if user can impersonate others"""
    return user.is_staff or user.is_superuser