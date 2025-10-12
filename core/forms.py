import json
from django import forms
from django.db.models import Q

from .models import (
    CDLMessage,
    CDLRequest,
    CertificateBatch,
    Organization,
    OrganizationRole,
    OrganizationType,
    RoleAssignment,
    StudentAchievement,
)


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
        self.fields["organization"].queryset = Organization.objects.filter(
            org_filter
        ).order_by("name")
        self.fields["organization"].empty_label = "Select Organization"

        # Include active roles plus the currently assigned role (even if inactive)
        role_filter = Q(is_active=True)
        if self.instance.pk and self.instance.role_id:
            role_filter |= Q(pk=self.instance.role_id)
        self.fields["role"].queryset = (
            OrganizationRole.objects.filter(role_filter)
            .select_related("organization")
            .order_by("name")
        )
        self.fields["role"].empty_label = "Select Role"

        # Mark fields as not required for deletion-safe formsets
        self.fields["organization"].required = False
        self.fields["role"].required = False


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
            # Ensure IDs exist
            if not Organization.objects.filter(id=org_id).exists():
                continue
            if not OrganizationRole.objects.filter(id=role_id).exists():
                continue
            cleaned.append({"organization": org_id, "role": role_id})
        return cleaned


class OrgSelectForm(forms.Form):
    org_type = forms.ModelChoiceField(
        queryset=OrganizationType.objects.all(),
        required=True,
        label="Organization Type",
    )
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.none(),
        required=True,
        label="Organization",
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
        widget=forms.TextInput(attrs={"placeholder": "2025-2026"}),
    )
    csv_file = forms.FileField(label="CSV File")


# ────────────────────────────────────────────────────────────────
#  CDL FORMS
# ────────────────────────────────────────────────────────────────
class CDLRequestForm(forms.ModelForm):
    """Form capturing CDL requirements during proposal submission."""

    class Meta:
        model = CDLRequest
        exclude = ("proposal", "created_at", "updated_at")

    def clean(self):
        cleaned = super().clean()

        wants_cdl = cleaned.get("wants_cdl")
        need_poster = cleaned.get("need_poster")
        need_certificate_any = cleaned.get("need_certificate_any")
        need_certificate_cdl = cleaned.get("need_certificate_cdl")
        poster_mode = cleaned.get("poster_mode")
        certificate_mode = cleaned.get("certificate_mode")
        poster_summary = cleaned.get("poster_summary", "")

        if wants_cdl and need_poster:
            required_fields = [
                "poster_organization_name",
                "poster_time",
                "poster_date",
                "poster_venue",
                "poster_resource_person",
                "poster_resource_designation",
                "poster_title",
                "poster_summary",
                "poster_design_link",
            ]
            for field in required_fields:
                if not cleaned.get(field):
                    self.add_error(field, "This field is required")

            # summary ~150 words
            if poster_summary:
                words = poster_summary.split()
                if len(words) < 120 or len(words) > 180:
                    self.add_error(
                        "poster_summary", "Summary must be around 150 words"
                    )

            if not poster_mode:
                self.add_error("poster_mode", "Select a poster option")

        if need_certificate_any:
            if need_certificate_cdl and not certificate_mode:
                self.add_error("certificate_mode", "Select certificate option")
            if (
                need_certificate_cdl
                and certificate_mode
                == CDLRequest.CertificateMode.CORRECT_EXISTING
                and not cleaned.get("certificate_design_link")
            ):
                self.add_error(
                    "certificate_design_link", "Provide design link"
                )

        if (
            wants_cdl
            and need_poster
            and need_certificate_cdl
            and poster_mode
            and certificate_mode
        ):
            if not cleaned.get("combined_design_link"):
                self.add_error(
                    "combined_design_link",
                    "Provide combined design link when poster and certificate are via CDL",
                )

        return cleaned


class CertificateBatchUploadForm(forms.ModelForm):
    class Meta:
        model = CertificateBatch
        fields = ["csv_file"]


class CDLMessageForm(forms.ModelForm):
    class Meta:
        model = CDLMessage
        fields = ["body", "file", "sent_via_email"]


class StudentAchievementForm(forms.ModelForm):
    """Validate student achievement submissions including optional document upload."""

    MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB
    ALLOWED_CONTENT_TYPES = {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
    }

    class Meta:
        model = StudentAchievement
        fields = ["title", "description", "date_achieved", "document"]

    def clean_document(self):
        document = self.cleaned_data.get("document")
        if not document:
            return document

        if document.size > self.MAX_UPLOAD_SIZE:
            raise forms.ValidationError("Document must be 5 MB or smaller.")

        content_type = getattr(document, "content_type", "").lower()
        if content_type and content_type not in self.ALLOWED_CONTENT_TYPES:
            raise forms.ValidationError(
                "Unsupported file type. Upload a PDF or image file."
            )

        return document
