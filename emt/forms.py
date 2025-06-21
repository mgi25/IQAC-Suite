from django import forms
from .models import EventProposal,AttendanceRecord, Coordinator, Volunteer   , EventNeedAnalysis,EventObjectives,EventExpectedOutcomes,TentativeFlow,SpeakerProfile,ExpenseDetail

class EventProposalForm(forms.ModelForm):
    class Meta:
        model = EventProposal
        exclude = ['submitted_by', 'created_at', 'updated_at', 'status']
        labels = {
            'department': 'Which department is organizing the event?',
            'committees': 'List the committee(s) and any collaborations involved:',
            'event_title': 'What is the title of your event?',
            'num_activities': 'How many activities will take place?',
            'event_datetime': 'When will the event happen?',
            'venue': 'Where is the event venue?',
            'academic_year': 'Which academic year does this fall under?',
            'target_audience': 'Who is your target audience?',
            'faculty_incharges': 'Faculty In-charges (names & roles):',
            'student_coordinators': 'Student Coordinators (names & contacts):',
            'event_focus_type': 'What is the focus/theme of the event?',
            'fest_fee_participants': 'Fest: Number of participants (for fee)',
            'fest_fee_rate': 'Fest: Fee per participant (₹)',
            'fest_fee_amount': 'Fest: Total expected amount from fees (₹)',
            'fest_sponsorship_amount': 'Fest: Total sponsorship amount (₹)',
            'conf_fee_participants': 'Conference: Number of participants (for fee)',
            'conf_fee_rate': 'Conference: Fee per participant (₹)',
            'conf_fee_amount': 'Conference: Total expected amount from fees (₹)',
            'conf_sponsorship_amount': 'Conference: Total sponsorship amount (₹)',
        }
        widgets = {
            'event_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'committees': forms.Textarea(attrs={'rows': 2}),
            'faculty_incharges': forms.Textarea(attrs={'rows': 2}),
            'student_coordinators': forms.Textarea(attrs={'rows': 2}),
        }
class NeedAnalysisForm(forms.ModelForm):
    class Meta:
        model = EventNeedAnalysis
        fields = ['content']
        labels = {
            'content': 'Explain the need for organizing this event. You may include observations or survey results.',
        }
        widgets = {
            'content': forms.Textarea(attrs={
                'placeholder': 'Describe why this event is needed...',
                'rows': 8
            }),
        }
class ObjectivesForm(forms.ModelForm):
    class Meta:
        model = EventObjectives
        fields = ['content']
        labels = {
            'content': 'List the objectives of this event. Present them as clear and concise points.',
        }
        widgets = {
            'content': forms.Textarea(attrs={
                'placeholder': 'e.g. 1. Increase awareness...\n2. Provide skill training...',
                'rows': 8
            }),
        }
class ExpectedOutcomesForm(forms.ModelForm):
    class Meta:
        model = EventExpectedOutcomes
        fields = ['content']
        labels = {
            'content': 'What outcomes do you expect from this event?',
        }
        widgets = {
            'content': forms.Textarea(attrs={
                'placeholder': 'List the expected outcomes clearly...',
                'rows': 7
            }),
        }
class TentativeFlowForm(forms.ModelForm):
    class Meta:
        model = TentativeFlow
        fields = ['content']
        labels = {
            'content': 'Outline the tentative flow of your event',
        }
        widgets = {
            'content': forms.Textarea(attrs={
                'placeholder': 'Example:\n10:00 AM - Welcome\n10:15 AM - Guest Talk\n11:00 AM - Activities\n12:00 PM - Vote of Thanks...',
                'rows': 8,
            }),
        }
class SpeakerProfileForm(forms.ModelForm):
    class Meta:
        model = SpeakerProfile
        fields = [
            'full_name', 'designation', 'affiliation',
            'contact_email', 'contact_number', 'photo', 'detailed_profile'
        ]
        labels = {
            'full_name': 'Full Name of Speaker',
            'designation': 'Designation/Title',
            'affiliation': 'Affiliation/Organization',
            'contact_email': 'Email Address',
            'contact_number': 'Contact Number',
            'photo': 'Upload Speaker Photo',
            'detailed_profile': 'Brief Profile/Bio of Speaker'
        }
        widgets = {
            'detailed_profile': forms.Textarea(attrs={'rows': 5}),
        }
class ExpenseDetailForm(forms.ModelForm):
    class Meta:
        model = ExpenseDetail
        fields = ['sl_no', 'particulars', 'amount']

# forms.py
class AttendanceForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        fields = ['reg_no', 'name']

class CoordinatorForm(forms.ModelForm):
    class Meta:
        model = Coordinator
        fields = ['name']

class VolunteerForm(forms.ModelForm):
    class Meta:
        model = Volunteer
        fields = ['name']
