from django import forms
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from .models import (
    EventProposal, EventNeedAnalysis, EventObjectives,
    EventExpectedOutcomes, TentativeFlow, SpeakerProfile,
    ExpenseDetail
)
from core.models import Department, Association, Club, Center, Cell

ORG_TYPE_CHOICES = [
    ('department', 'Department'),
    ('association', 'Association'),
    ('club', 'Club'),
    ('center', 'Center'),
    ('cell', 'Cell'),
]
class EventProposalForm(forms.ModelForm):
    org_type = forms.ChoiceField(
        required=True,
        label="Type of Organisation",
        choices=ORG_TYPE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'tomselect-orgtype',
        }),
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'org-box department-box'})
    )
    association = forms.ModelChoiceField(
        queryset=Association.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'org-box association-box'})
    )
    club = forms.ModelChoiceField(
        queryset=Club.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'org-box club-box'})
    )
    center = forms.ModelChoiceField(
        queryset=Center.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'org-box center-box'})
    )
    cell = forms.ModelChoiceField(
        queryset=Cell.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'org-box cell-box'})
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

    class Meta:
        model = EventProposal
        fields = [
            'org_type', 'department', 'association', 'club', 'center', 'cell',
            'faculty_incharges', 'event_title', 'event_datetime', 'venue',
            'committees', 'num_activities', 'academic_year', 'student_coordinators',
            'target_audience', 'event_focus_type', 'fest_fee_participants',
            'fest_fee_rate', 'fest_fee_amount', 'fest_sponsorship_amount',
            'conf_fee_participants', 'conf_fee_rate', 'conf_fee_amount', 'conf_sponsorship_amount',
        ]
        exclude = ['submitted_by', 'created_at', 'updated_at', 'status', 'report_generated', 'needs_finance_approval', 'is_big_event']

        labels = {
            'org_type': 'Type of Organisation',
            'department': 'Department',
            'association': 'Association',
            'club': 'Club',
            'center': 'Center',
            'cell': 'Cell',
            # ...rest as before...
        }
        widgets = {
            'event_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'committees':         forms.Textarea(attrs={'rows': 2}),
            'student_coordinators': forms.Textarea(attrs={'rows': 2}),
            'target_audience':    forms.TextInput(attrs={'placeholder': 'e.g., BSc students'}),
        }

    def clean(self):
        data = super().clean()
        org_type = data.get('org_type', '').lower()
        model_map = {
            'department': Department,
            'association': Association,
            'club': Club,
            'center': Center,
            'cell': Cell,
        }
        found = False
        for org_field, model in model_map.items():
            if org_type == org_field:
                val = data.get(org_field)
                # If not found by id, check by posted string (for new names)
                if not val:
                    posted_val = self.data.get(org_field)
                    if posted_val:
                        if posted_val.isdigit():
                            val = model.objects.filter(id=int(posted_val)).first()
                        else:
                            val = model.objects.filter(name=posted_val).first()
                            if not val:
                                val = model.objects.create(name=posted_val)
                if val:
                    data[org_field] = val
                    found = True
                else:
                    self.add_error(org_field, f'Please select or enter a valid {org_field.title()} name.')
            else:
                data[org_field] = None
        if not found:
            self.add_error('org_type', 'Please select an organization and its name.')
        return data


# ──────────────────────────────────────────────────────────────
#  Remaining forms (unchanged)
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
