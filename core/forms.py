from django import forms
from django.db.models import Q
import json

from .models import RoleAssignment, OrganizationRole, Organization, OrganizationType

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


class RegistrationForm(forms.Form):
    """Capture registration number and multiple organization/role pairs."""

    registration_number = forms.CharField(max_length=50, required=False)
    assignments = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, include_regno=True, **kwargs):
        super().__init__(*args, **kwargs)
        if include_regno:
            self.fields["registration_number"].required = True
        else:
            self.fields.pop("registration_number")

    def clean_assignments(self):
        data = self.cleaned_data.get("assignments", "")
        if not data:
            return []
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            raise forms.ValidationError("Invalid role assignment data.")

        cleaned = []
        for item in payload:
            org_id = item.get("organization")
            role_id = item.get("role")
            if not org_id or not role_id:
                continue
            # Ensure the IDs exist
            if not Organization.objects.filter(id=org_id).exists():
                continue
            if not OrganizationRole.objects.filter(id=role_id).exists():
                continue
            cleaned.append({"organization": org_id, "role": role_id})
        return cleaned


class OrgSelectForm(forms.Form):
    org_type = forms.ModelChoiceField(
        queryset=OrganizationType.objects.all(), required=True, label="Organization Type"
    )
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.none(), required=True, label="Organization"
    )
    role = forms.ChoiceField(
        choices=(("student", "Student"), ("faculty", "Faculty")), required=True
    )

    def __init__(self, *args, **kwargs):
        initial_type = kwargs.pop("initial_type", None)
        super().__init__(*args, **kwargs)
        if initial_type:
            self.fields["organization"].queryset = Organization.objects.filter(
                org_type=initial_type
            )


class CreateClassForm(forms.Form):
    parent_org = forms.ModelChoiceField(
        queryset=Organization.objects.all(), label="Parent Organization"
    )
    name = forms.CharField(max_length=255, label="Class Name")
    code = forms.CharField(max_length=64, label="Unique Code")
    academic_year = forms.CharField(
        max_length=9, label="Academic Year (e.g., 2025-2026)"
    )


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField()


class OrgUsersCSVUploadForm(forms.Form):
    class_name = forms.CharField(
        max_length=100,
        label="Class",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "e.g., BSc-A"}),
    )
    academic_year = forms.CharField(
        max_length=9,
        label="Academic Year (e.g., 2025-2026)",
        widget=forms.TextInput(attrs={"placeholder": "2025-2026"})
    )
    csv_file = forms.FileField(label="CSV File")
