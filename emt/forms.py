from django import forms
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from .models import (
    EventProposal, EventNeedAnalysis, EventObjectives,
    EventExpectedOutcomes, TentativeFlow, SpeakerProfile,
    ExpenseDetail, EventReport, EventReportAttachment
)
from core.models import Organization, OrganizationType

class EventProposalForm(forms.ModelForm):
    organization_type = forms.ModelChoiceField(
        required=True,
        label="Type of Organisation",
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
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'e.g., Alice, Bob'}),
        help_text="Enter student coordinator names, separated by commas."
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
            'organization_type', 'organization', 'faculty_incharges', 'event_title', 'event_datetime', 'venue',
            'committees', 'num_activities', 'academic_year', 'student_coordinators',
            'target_audience', 'event_focus_type', 'fest_fee_participants',
            'fest_fee_rate', 'fest_fee_amount', 'fest_sponsorship_amount',
            'conf_fee_participants', 'conf_fee_rate', 'conf_fee_amount', 'conf_sponsorship_amount',
        ]
        exclude = ['submitted_by', 'created_at', 'updated_at', 'status', 'report_generated', 'needs_finance_approval', 'is_big_event']

        labels = {
            'organization_type': 'Type of Organisation',
            'organization': 'Organization Name',
        }
        widgets = {
            'event_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'committees':         forms.Textarea(attrs={'rows': 2}),
            'student_coordinators': forms.Textarea(attrs={'rows': 2}),
            'target_audience':    forms.TextInput(attrs={'placeholder': 'e.g., BSc students'}),
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
    class Meta:
        model   = SpeakerProfile
        fields  = [
            'full_name', 'designation', 'affiliation',
            'contact_email', 'contact_number', 'photo', 'detailed_profile'
        ]
        labels = {
            'full_name':       'Full Name',
            'designation':     'Designation / Title',
            'affiliation':     'Affiliation / Organization',
            'contact_email':   'Email',
            'contact_number':  'Contact Number',
            'photo':           'Speaker Photo',
            'detailed_profile':'Brief Profile / Bio'
        }
        widgets = {
            'detailed_profile': forms.Textarea(attrs={'rows': 5})
        }

class ExpenseDetailForm(forms.ModelForm):
    class Meta:
        model  = ExpenseDetail
        fields = ['sl_no', 'particulars', 'amount']

class EventReportForm(forms.ModelForm):
    class Meta:
        model = EventReport
        fields = [
            'location', 'blog_link', 'num_student_volunteers', 'num_participants', 'external_contact_details',
            'summary', 'outcomes', 'impact_on_stakeholders', 'innovations_best_practices',
            'pos_pso_mapping', 'needs_grad_attr_mapping', 'contemporary_requirements', 'sdg_value_systems_mapping',
            'iqac_feedback', 'report_signed_date', 'beneficiaries_details'
        ]
        widgets = {
            'location': forms.TextInput(attrs={'class': 'ultra-input'}),
            'blog_link': forms.TextInput(attrs={'class': 'ultra-input'}),
            'num_student_volunteers': forms.NumberInput(attrs={'class': 'ultra-input'}),
            'num_participants': forms.NumberInput(attrs={'class': 'ultra-input'}),
            'external_contact_details': forms.Textarea(attrs={'class': 'ultra-input', 'rows': 3}),
            'summary': forms.Textarea(attrs={'class': 'ultra-input', 'rows': 3}),
            'outcomes': forms.Textarea(attrs={'class': 'ultra-input', 'rows': 3}),
            'impact_on_stakeholders': forms.Textarea(attrs={'class': 'ultra-input', 'rows': 3}),
            'innovations_best_practices': forms.Textarea(attrs={'class': 'ultra-input', 'rows': 3}),
            'pos_pso_mapping': forms.Textarea(attrs={'class': 'ultra-input', 'rows': 2}),
            'needs_grad_attr_mapping': forms.Textarea(attrs={'class': 'ultra-input', 'rows': 2}),
            'contemporary_requirements': forms.Textarea(attrs={'class': 'ultra-input', 'rows': 2}),
            'sdg_value_systems_mapping': forms.Textarea(attrs={'class': 'ultra-input', 'rows': 2}),
            'iqac_feedback': forms.Textarea(attrs={'class': 'ultra-input', 'rows': 2}),
            'report_signed_date': forms.DateInput(attrs={'class': 'ultra-input', 'type': 'date'}),
            'beneficiaries_details': forms.Textarea(attrs={'class': 'ultra-input', 'rows': 2}),
        }

class EventReportAttachmentForm(forms.ModelForm):
    class Meta:
        model = EventReportAttachment
        fields = ['file', 'caption']
