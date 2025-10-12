from django.contrib import admin

from .models import JoinRequest


@admin.register(JoinRequest)
class JoinRequestAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "organization",
        "request_type",
        "status",
        "is_seen",
        "requested_on",
        "updated_on",
    )
    list_filter = ("request_type", "status", "is_seen", "organization")
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "organization__name",
    )
    autocomplete_fields = ("user", "organization")
    readonly_fields = ("requested_on", "updated_on")
