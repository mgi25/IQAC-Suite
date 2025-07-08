from django import forms
from django.contrib.auth.models import User
from django.urls import reverse_lazy

from .models import (
    EventProposal, EventNeedAnalysis, EventObjectives,
    EventExpectedOutcomes, TentativeFlow, SpeakerProfile,
    ExpenseDetail, Department
)

# ──────────────────────────────────────────────────────────────
#  STEP 1 • Event Proposal Form (with new flags)
# ──────────────────────────────────────────────────────────────
class EventProposalForm(forms.ModelForm):
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        widget=forms.Select(attrs={
            'class': 'select2-ajax',
            'data-url': reverse_lazy("emt:api_departments")
        }),
        required=True
    )

    faculty_incharges = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role_assignments__role="faculty").distinct(),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'select2-ajax',
            'data-url': reverse_lazy("emt:api_faculty"),
            'placeholder': "Type a lecturer name…",
        })
    )

    # ── NEW FLAGS ──
    # needs_finance_approval = forms.BooleanField(
    #     required=False,
    #     label="Does this event require finance approval?"
    # )
    # is_big_event           = forms.BooleanField(
    #     required=False,
    #     label="Is this a big event (Dean approval needed)?"
    # )
    # ───────────────

    class Meta:
        model   = EventProposal
        exclude = ['submitted_by', 'created_at', 'updated_at', 'status', 'report_generated','needs_finance_approval','is_big_event']
        labels = {
            'department': 'Which department is organizing the event?',
            'committees': 'List the committee(s) and any collaborations involved:',
            'event_title': 'What is the title of your event?',
            'num_activities': 'How many activities will take place?',
            'event_datetime': 'When will the event happen?',
            'venue': 'Where is the event venue?',
            'academic_year': 'Which academic year does this fall under?',
            'faculty_incharges': 'Faculty In-charges (select one or more)',
            'student_coordinators': 'Student Coordinators (names & contacts)',
            'target_audience': 'Who is your target audience?',
            'event_focus_type': 'What is the focus / theme of the event?',
            # income labels unchanged…
        }
        widgets = {
            'event_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'committees':         forms.Textarea(attrs={'rows': 2}),
            'student_coordinators': forms.Textarea(attrs={'rows': 2}),
            'target_audience':    forms.TextInput(attrs={'placeholder': 'e.g., BSc students'}),
        }


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
