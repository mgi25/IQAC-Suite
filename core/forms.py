from django import forms
from django.db.models import Q

from .models import RoleAssignment, OrganizationRole, Organization

class RoleAssignmentForm(forms.ModelForm):
    class Meta:
        model = RoleAssignment
        fields = ("role", "organization")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Include active organizations plus the currently assigned one (if any)
        org_filter = Q(is_active=True)
        if self.instance.pk and self.instance.organization_id:
            org_filter |= Q(pk=self.instance.organization_id)
        self.fields["organization"].queryset = (
            Organization.objects.filter(org_filter).order_by("name")
        )

        # Include active roles plus the currently assigned role (even if inactive)
        role_filter = Q(is_active=True)
        if self.instance.pk and self.instance.role_id:
            role_filter |= Q(pk=self.instance.role_id)
        self.fields["role"].queryset = (
            OrganizationRole.objects.filter(role_filter)
            .select_related("organization")
            .order_by("name")
        )
