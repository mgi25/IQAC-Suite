from django import forms
from .models import RoleAssignment, OrganizationRole

class RoleAssignmentForm(forms.ModelForm):
    class Meta:
        model = RoleAssignment
        fields = ("role", "organization")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Show only active roles; you can filter by organization if needed
        self.fields["role"].queryset = OrganizationRole.objects.filter(is_active=True)
