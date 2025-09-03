from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from .models import (
    SDGGoal,
    log_impersonation_start,
    CDLRequest,
    CDLCommunicationThread,
    CDLMessage,
    CertificateBatch,
    CertificateEntry,
)


class ImpersonationUserAdmin(BaseUserAdmin):
    """Extended UserAdmin with impersonation functionality"""
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:user_id>/impersonate/',
                self.admin_site.admin_view(self.impersonate_user),
                name='auth_user_impersonate',
            ),
        ]
        return custom_urls + urls
    
    @method_decorator(csrf_protect)
    @method_decorator(require_POST)
    def impersonate_user(self, request, user_id):
        """Impersonate user from admin"""
        if not request.user.is_superuser:
            messages.error(request, "Only superusers can impersonate users")
            return redirect('admin:auth_user_changelist')

        try:
            target_user = User.objects.get(id=user_id, is_active=True)
            if target_user.is_superuser:
                messages.error(request, "Cannot impersonate superusers")
                return redirect('admin:auth_user_changelist')

            request.session['impersonate_user_id'] = target_user.id
            request.session['original_user_id'] = request.user.id
            log_impersonation_start(request, target_user)
            messages.success(request, f'Now impersonating {target_user.get_full_name() or target_user.username}')
            return redirect('/')  # Redirect to main site
        except User.DoesNotExist:
            messages.error(request, "User not found or inactive")
            return redirect('admin:auth_user_changelist')

admin.site.unregister(User)
admin.site.register(User, ImpersonationUserAdmin)
admin.site.register(SDGGoal)
admin.site.register(CDLRequest)
admin.site.register(CDLCommunicationThread)
admin.site.register(CDLMessage)
admin.site.register(CertificateBatch)
admin.site.register(CertificateEntry)
