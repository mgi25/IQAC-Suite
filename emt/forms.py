from django import forms
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.urls import reverse_lazy
from .models import (
    EventProposal, EventNeedAnalysis, EventObjectives,
    EventExpectedOutcomes, TentativeFlow, SpeakerProfile,
    ExpenseDetail, EventReport, EventReportAttachment, CDLSupport,
    CDLCertificateRecipient, CDLMessage,
)
from core.models import (
    Organization,
    OrganizationType,
    SDGGoal,
    SDG_GOALS,
    OrganizationMembership,
)

# Reusable validator to ensure names contain only letters and basic punctuation
NAME_PATTERN = r"^[A-Za-z .'-]+$"
name_validator = RegexValidator(
    NAME_PATTERN,
    "Only letters and standard punctuation (.'- and spaces) are allowed.",
)

class EventProposalForm(forms.ModelForm):
    organization_type = forms.ModelChoiceField(
        required=True,
        label="Type of Organization",
        queryset=OrganizationType.objects.all(),
        widget=forms.Select(attrs={'class': 'tomselect-orgtype'}),
    )
    organization = forms.ModelChoiceField(
        required=True,
        label="Organization Name",
        queryset=Organization.objects.none(),  # Populated in __init__ below!
        widget=forms.Select(attrs={'class': 'org-box organization-box'})
    )

    faculty_incharges = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),  # No initial users, loaded via JS!
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'select2-ajax',
            'data-url': reverse_lazy("emt:api_faculty"),
            'placeholder': "Type a lecturer name…",
        })
    )
    student_coordinators = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )
    sdg_goals = forms.ModelMultipleChoiceField(
        queryset=SDGGoal.objects.filter(name__in=SDG_GOALS).order_by("id"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Aligned SDG Goals',
    )



    academic_year = forms.CharField(
        required=True,
        label="Academic Year",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'style': 'background-color: #f8f9fa; cursor: not-allowed;',
            'placeholder': 'Academic year will be set by admin',
        }),
        help_text="This academic year is set by the admin and cannot be changed."
    )

    def __init__(self, *args, **kwargs):
        selected_academic_year = kwargs.pop('selected_academic_year', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Filter organization queryset by selected type if available in POST/data/instance
        org_type = None
        if self.data.get("organization_type"):
            try:
                org_type_id = int(self.data.get("organization_type"))
                org_type = OrganizationType.objects.filter(id=org_type_id).first()
            except Exception:
                org_type = None
        elif self.instance and getattr(self.instance, "organization", None):
            org_type = self.instance.organization.org_type
            # Pre-populate organization type when editing existing proposals
            self.fields["organization_type"].initial = org_type
        elif user:
            assignment = (
                user.role_assignments
                .filter(organization__isnull=False)
                .select_related("organization__org_type")
                .first()
            )
            if assignment:
                org_type = assignment.organization.org_type
                self.fields["organization_type"].initial = org_type
                self.fields["organization"].initial = assignment.organization
            else:
                membership = (
                    user.org_memberships
                    .filter(is_active=True)
                    .select_related("organization__org_type")
                    .first()
                )
                if membership:
                    org_type = membership.organization.org_type
                    self.fields["organization_type"].initial = org_type
                    self.fields["organization"].initial = membership.organization

        if org_type:
            self.fields['organization'].queryset = Organization.objects.filter(org_type=org_type, is_active=True)
        else:
            self.fields['organization'].queryset = Organization.objects.filter(is_active=True)

        # Academic year setup
        if selected_academic_year and not self.instance.pk:
            self.fields['academic_year'].initial = selected_academic_year
            self.fields['academic_year'].widget.attrs['value'] = selected_academic_year
        elif not self.instance.pk:
            self.fields['academic_year'].widget.attrs['placeholder'] = 'No academic year set by admin'

    class Meta:
        model = EventProposal
        fields = [
            'organization_type', 'organization', 'faculty_incharges', 'event_title', 'event_start_date', 'event_end_date', 'venue',
            'committees_collaborations', 'sdg_goals', 'num_activities', 'academic_year', 'student_coordinators', 'pos_pso',
            'target_audience', 'event_focus_type', 'fest_fee_participants',
            'fest_fee_rate', 'fest_fee_amount', 'fest_sponsorship_amount',
            'conf_fee_participants', 'conf_fee_rate', 'conf_fee_amount', 'conf_sponsorship_amount',
        ]
        exclude = ['submitted_by', 'created_at', 'updated_at', 'status', 'report_generated', 'needs_finance_approval', 'is_big_event']

        labels = {
            'organization_type': 'Type of Organization',
            'organization': 'Organization Name',
            'event_start_date': 'Start Date',
            'event_end_date': 'End Date',
            'venue': 'Location',
            'pos_pso': 'POS & PSO Management',
            'sdg_goals': 'Aligned SDG Goals',
            'committees_collaborations': 'Committees & Collaborations',
        }
        widgets = {
            'event_start_date': forms.DateInput(attrs={'type': 'date'}),
            'event_end_date': forms.DateInput(attrs={'type': 'date'}),
            'committees_collaborations': forms.Textarea(attrs={'rows': 3, 'placeholder': 'List committees and collaborations involved'}),

            'student_coordinators': forms.Textarea(attrs={'rows': 2}),
            'target_audience':    forms.TextInput(attrs={'placeholder': 'e.g., BSc students'}),
            'pos_pso':            forms.Textarea(attrs={'rows': 2, 'placeholder': 'e.g., PO1, PSO2'}),
        }

    def clean(self):
        data = super().clean()
        org_type = data.get('organization_type')
        organization = data.get('organization')
        if not org_type:
            self.add_error('organization_type', 'Please select an organization type.')
        if not organization:
            self.add_error('organization', 'Please select an organization name.')
        elif org_type and organization and organization.org_type != org_type:
            self.add_error('organization', 'Selected organization does not match the chosen type.')
        return data

# ──────────────────────────────────────────────────────────────
#  Remaining forms (unchanged, but imports updated)
# ──────────────────────────────────────────────────────────────
class NeedAnalysisForm(forms.ModelForm):
    class Meta:
        model   = EventNeedAnalysis
        fields  = ['content']
        labels  = {'content': 'Explain the need for organizing this event.'}
        widgets = {
            'content': forms.Textarea(
                attrs={'rows': 8, 'placeholder': 'Describe why this event is needed…'}
            )
        }

class ObjectivesForm(forms.ModelForm):
    class Meta:
        model   = EventObjectives
        fields  = ['content']
        labels  = {'content': 'List the objectives of this event.'}
        widgets = {
            'content': forms.Textarea(
                attrs={'rows': 8, 'placeholder': 'e.g., 1. Increase awareness…'}
            )
        }

class ExpectedOutcomesForm(forms.ModelForm):
    class Meta:
        model   = EventExpectedOutcomes
        fields  = ['content']
        labels  = {'content': 'What outcomes do you expect from this event?'}
        widgets = {
            'content': forms.Textarea(
                attrs={'rows': 7, 'placeholder': 'List expected outcomes clearly…'}
            )
        }

class TentativeFlowForm(forms.ModelForm):
    class Meta:
        model   = TentativeFlow
        fields  = ['content']
        labels  = {'content': 'Outline the tentative flow of your event'}
        widgets = {
            'content': forms.Textarea(
                attrs={'rows': 8, 'placeholder': '10:00 AM – Welcome\n10:15 AM – Guest Talk…'}
            )
        }

class SpeakerProfileForm(forms.ModelForm):
    full_name = forms.CharField(
        validators=[name_validator],
        widget=forms.TextInput(attrs={'pattern': NAME_PATTERN}),
    )

    class Meta:
        model   = SpeakerProfile
        fields  = [
            'full_name', 'designation', 'affiliation',
            'contact_email', 'contact_number', 'linkedin_url', 'photo', 'detailed_profile'
        ]
        labels = {
            'full_name':       'Full Name',
            'designation':     'Designation / Title',
            'affiliation':     'Affiliation / Organization',
            'contact_email':   'Email',
            'contact_number':  'Contact Number',
            'linkedin_url':    'LinkedIn Profile',
            'photo':           'Speaker Photo',
            'detailed_profile':'Brief Profile / Bio'
        }
        widgets = {
            'detailed_profile': forms.Textarea(attrs={'rows': 5}),
            'linkedin_url': forms.URLInput(attrs={'placeholder': 'https://linkedin.com/in/username'})
        }

class ExpenseDetailForm(forms.ModelForm):
    class Meta:
        model  = ExpenseDetail
        fields = ['sl_no', 'particulars', 'amount']

class EventReportForm(forms.ModelForm):
    class Meta:
        model = EventReport
        fields = [
            'location', 'blog_link', 'actual_event_type', 'num_student_volunteers', 'num_participants', 'external_contact_details',
            'summary', 'outcomes', 'impact_on_stakeholders', 'innovations_best_practices',
            'pos_pso_mapping', 'needs_grad_attr_mapping', 'contemporary_requirements', 'sdg_value_systems_mapping',
            'iqac_feedback', 'report_signed_date', 'beneficiaries_details', 'attendance_notes'
        ]
        widgets = {
            'location': forms.TextInput(attrs={'class': 'ultra-input'}),
            'blog_link': forms.TextInput(attrs={'class': 'ultra-input'}),
            'actual_event_type': forms.TextInput(attrs={'class': 'ultra-input'}),
            'num_student_volunteers': forms.NumberInput(attrs={'class': 'ultra-input'}),
            'num_participants': forms.NumberInput(attrs={'class': 'ultra-input'}),
            'external_contact_details': forms.Textarea(attrs={'class': 'ultra-input', 'rows': 3}),
            'summary': forms.Textarea(attrs={'class': 'ultra-input', 'rows': 3}),
            'outcomes': forms.Textarea(attrs={'class': 'ultra-input', 'rows': 3}),
            'impact_on_stakeholders': forms.Textarea(attrs={'class': 'ultra-input', 'rows': 3}),
            'innovations_best_practices': forms.Textarea(attrs={'class': 'ultra-input', 'rows': 3}),
            'pos_pso_mapping': forms.Textarea(attrs={'class': 'ultra-input', 'rows': 2, 'placeholder': 'Click to select POs/PSOs'}),
            'needs_grad_attr_mapping': forms.Textarea(attrs={'class': 'ultra-input', 'rows': 2}),
            'contemporary_requirements': forms.Textarea(attrs={'class': 'ultra-input', 'rows': 2}),
            'sdg_value_systems_mapping': forms.Textarea(attrs={'class': 'ultra-input', 'rows': 2}),
            'iqac_feedback': forms.Textarea(attrs={'class': 'ultra-input', 'rows': 2}),
            'report_signed_date': forms.DateInput(attrs={'class': 'ultra-input', 'type': 'date'}),
            'beneficiaries_details': forms.Textarea(attrs={'class': 'ultra-input', 'rows': 2}),
            'attendance_notes': forms.Textarea(attrs={'class': 'ultra-input', 'rows': 2}),
        }

class EventReportAttachmentForm(forms.ModelForm):
    class Meta:
        model = EventReportAttachment
        fields = ['file', 'caption']
        widgets = {
            # Use plain FileInput to avoid Django's "Change" and "Clear" controls
            'file': forms.FileInput(attrs={'class': 'file-input', 'style': 'display:none;'}),
            'caption': forms.TextInput(attrs={'style': 'display:none;'}),
        }


class CDLSupportForm(forms.ModelForm):
    """Form for capturing CDL support requirements during proposal submission."""

    poster_choice = forms.ChoiceField(
        choices=CDLSupport.PosterChoice.choices,
        widget=forms.RadioSelect,
        required=False,
    )
    certificate_choice = forms.ChoiceField(
        choices=CDLSupport.CertificateChoice.choices,
        widget=forms.RadioSelect,
        required=False,
    )
    other_services = forms.MultipleChoiceField(
        choices=[
            ("photography", "Event Photography"),
            ("videography", "Event Videography"),
            ("digital_board", "Digital Board Display"),
            ("voluntary_cards", "Voluntary Cards"),
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    poster_required = forms.BooleanField(
        required=False, label="Do you need a poster for your event?"
    )
    poster_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    certificates_required = forms.BooleanField(
        required=False, label="Do you need certificates for this event?"
    )
    certificate_help = forms.BooleanField(
        required=False, label="Do you need CDL help with event certificates?"
    )

    resource_person_name = forms.CharField(
        required=False,
        validators=[name_validator],
        widget=forms.TextInput(attrs={'pattern': NAME_PATTERN}),
    )

    class Meta:
        model = CDLSupport
        fields = [
            "needs_support",
            "poster_required",
            "poster_choice",
            "organization_name",
            "poster_time",
            "poster_date",
            "poster_venue",
            "resource_person_name",
            "resource_person_designation",
            "poster_event_title",
            "poster_summary",
            "poster_design_link",
            "other_services",
            "certificates_required",
            "certificate_help",
            "certificate_choice",
            "certificate_design_link",
            "blog_content",
        ]
        widgets = {
            "blog_content": forms.Textarea(attrs={"rows": 6}),
            "poster_summary": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_poster_summary(self):
        text = self.cleaned_data.get("poster_summary", "").strip()
        if text and len(text.split()) > 150:
            raise forms.ValidationError("Summary must be 150 words or fewer.")
        return text
    def clean_blog_content(self):
        text = self.cleaned_data.get("blog_content", "").strip()
        if text and len(text.split()) > 150:
            raise forms.ValidationError("Blog content must be 150 words or fewer.")
        return text


class CertificateRecipientForm(forms.ModelForm):
    name = forms.CharField(
        validators=[name_validator],
        widget=forms.TextInput(attrs={'pattern': NAME_PATTERN}),
    )

    class Meta:
        model = CDLCertificateRecipient
        fields = ["name", "role", "certificate_type"]


class CDLMessageForm(forms.ModelForm):
    class Meta:
        model = CDLMessage
        fields = ["message", "file"]
