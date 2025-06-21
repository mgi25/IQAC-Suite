from django.db import models
from django.contrib.auth.models import User

class EventProposal(models.Model):
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="emt_eventproposals")
    department           = models.CharField(max_length=100)
    committees           = models.TextField()
    event_title          = models.CharField(max_length=200)
    num_activities       = models.PositiveIntegerField()
    event_datetime       = models.DateTimeField()
    venue                = models.CharField(max_length=200)
    academic_year        = models.CharField(max_length=20)
    target_audience      = models.CharField(max_length=200)
    faculty_incharges    = models.TextField()
    student_coordinators = models.TextField()
    event_focus_type     = models.CharField(max_length=200)

    # Income Section
    fest_fee_participants     = models.PositiveIntegerField(null=True, blank=True)
    fest_fee_rate             = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fest_fee_amount           = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    fest_sponsorship_amount   = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    conf_fee_participants     = models.PositiveIntegerField(null=True, blank=True)
    conf_fee_rate             = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    conf_fee_amount           = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    conf_sponsorship_amount   = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status     = models.CharField(max_length=20, choices=[
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], default='draft')

    def __str__(self):
        return self.event_title
    
class EventNeedAnalysis(models.Model):
    proposal = models.OneToOneField(EventProposal, on_delete=models.CASCADE)
    content = models.TextField()


class EventObjectives(models.Model):
    proposal = models.OneToOneField(EventProposal, on_delete=models.CASCADE)
    content  = models.TextField()
class EventExpectedOutcomes(models.Model):
    proposal = models.OneToOneField(EventProposal, on_delete=models.CASCADE)
    content  = models.TextField()
class TentativeFlow(models.Model):
    proposal = models.OneToOneField(EventProposal, on_delete=models.CASCADE)
    content  = models.TextField()
class SpeakerProfile(models.Model):
    proposal         = models.ForeignKey(EventProposal, on_delete=models.CASCADE)
    full_name        = models.CharField(max_length=100)
    designation      = models.CharField(max_length=100)
    affiliation      = models.CharField(max_length=100)
    contact_email    = models.EmailField()
    contact_number   = models.CharField(max_length=15)
    photo            = models.ImageField(upload_to='speakers/')
    detailed_profile = models.TextField()
class ExpenseDetail(models.Model):
    proposal    = models.ForeignKey(EventProposal, on_delete=models.CASCADE, related_name='expense_details')
    sl_no       = models.PositiveIntegerField()
    particulars = models.CharField(max_length=200)
    amount      = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['sl_no']

    # models.py
class AttendanceRecord(models.Model):
    proposal = models.ForeignKey(EventProposal, on_delete=models.CASCADE, related_name='attendees')
    reg_no   = models.CharField(max_length=20)
    name     = models.CharField(max_length=100)

class Coordinator(models.Model):
    proposal = models.ForeignKey(EventProposal, on_delete=models.CASCADE, related_name='coordinators')
    name     = models.CharField(max_length=100)

class Volunteer(models.Model):
    proposal = models.ForeignKey(EventProposal, on_delete=models.CASCADE, related_name='volunteers')
    name     = models.CharField(max_length=100)

