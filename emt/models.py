from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import Department, Association, Club, Center, Cell

# ────────────────────────────────────────────────────────────────
#  MAIN PROPOSAL
# ────────────────────────────────────────────────────────────────
class EventProposal(models.Model):
    submitted_by   = models.ForeignKey(User, on_delete=models.CASCADE, related_name="emt_eventproposals")
    department     = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="proposals")
    association    = models.ForeignKey(Association, on_delete=models.SET_NULL, null=True, blank=True, related_name="proposals")
    club           = models.ForeignKey(Club, on_delete=models.SET_NULL, null=True, blank=True, related_name="proposals")
    center         = models.ForeignKey(Center, on_delete=models.SET_NULL, null=True, blank=True, related_name="proposals")
    cell           = models.ForeignKey(Cell, on_delete=models.SET_NULL, null=True, blank=True, related_name="proposals")
    # ── NEW APPROVAL FLAGS ──
    needs_finance_approval = models.BooleanField(
        default=False,
        help_text="Check if this event needs finance approval"
    )
    is_big_event           = models.BooleanField(
        default=False,
        help_text="Check if this is a big event (Dean sign-off needed)"
    )
    # ────────────────────────

    committees           = models.TextField(blank=True)
    event_title          = models.CharField(max_length=200, blank=True)
    num_activities       = models.PositiveIntegerField(null=True, blank=True)
    event_datetime       = models.DateTimeField(null=True, blank=True)
    venue                = models.CharField(max_length=200, blank=True)
    academic_year        = models.CharField(max_length=20,  blank=True)
    target_audience      = models.CharField(max_length=200, blank=True)

    faculty_incharges    = models.ManyToManyField(
        User, blank=True, related_name="faculty_incharge_proposals"
    )
    student_coordinators = models.TextField(blank=True)

    event_focus_type     = models.CharField(max_length=200, blank=True)
    report_generated     = models.BooleanField(default=False)

    # ------------- Income -------------
    fest_fee_participants   = models.PositiveIntegerField(null=True, blank=True)
    fest_fee_rate           = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fest_fee_amount         = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    fest_sponsorship_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    conf_fee_participants   = models.PositiveIntegerField(null=True, blank=True)
    conf_fee_rate           = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    conf_fee_amount         = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    conf_sponsorship_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # meta
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    STATUS_CHOICES = [
        ('draft',        'Draft'),
        ('submitted',    'Submitted'),
        ('under_review', 'Under Review'),
        ('waiting', 'Waiting'),
        ('approved',     'Approved'),
        ('rejected',     'Rejected'),
        ('returned',     'Returned for Revision'),
        ('finalized',    'Finalized'),  # <-- add this!
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    def __str__(self):
        return self.event_title or f"Proposal #{self.id}"

# (Your other related models remain unchanged below!)
# ────────────────────────────────────────────────────────────────
#  One-to-one / related tables (unchanged)
# ────────────────────────────────────────────────────────────────

class EventNeedAnalysis(models.Model):
    proposal = models.OneToOneField(EventProposal, on_delete=models.CASCADE)
    content  = models.TextField()

class EventObjectives(models.Model):
    proposal = models.OneToOneField(EventProposal, on_delete=models.CASCADE)
    content  = models.TextField()

class EventExpectedOutcomes(models.Model):
    proposal = models.OneToOneField(EventProposal, on_delete=models.CASCADE)
    content  = models.TextField()

class TentativeFlow(models.Model):
    proposal = models.OneToOneField(EventProposal, on_delete=models.CASCADE)
    content  = models.TextField()

# ────────────────────────────────────────────────────────────────
#  Speaker & Expense (unchanged)
# ────────────────────────────────────────────────────────────────
class SpeakerProfile(models.Model):
    proposal        = models.ForeignKey(EventProposal, on_delete=models.CASCADE)
    full_name       = models.CharField(max_length=100)
    designation     = models.CharField(max_length=100)
    affiliation     = models.CharField(max_length=100)
    contact_email   = models.EmailField()
    contact_number  = models.CharField(max_length=15)
    photo           = models.ImageField(upload_to='speakers/')
    detailed_profile= models.TextField()

class ExpenseDetail(models.Model):
    proposal    = models.ForeignKey(EventProposal, on_delete=models.CASCADE, related_name='expense_details')
    sl_no       = models.PositiveIntegerField()
    particulars = models.CharField(max_length=200)
    amount      = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['sl_no']

# ────────────────────────────────────────────────────────────────
#  Approval Steps (unchanged)
# ────────────────────────────────────────────────────────────────
class ApprovalStep(models.Model):
    proposal      = models.ForeignKey(EventProposal, on_delete=models.CASCADE, related_name="approval_steps")
    step_order    = models.PositiveIntegerField(null=True, blank=True)
    role_required = models.CharField(
        max_length=50,
        help_text="Role needed: e.g., faculty, dept_iqac, hod, director, dean",
        null=True, blank=True
    )
    assigned_to = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_approvals"
    )
    approved_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="completed_approvals"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    status      = models.CharField(
        max_length=20,
        choices=[('pending','Pending'), ('approved','Approved'),
                 ('rejected','Rejected'), ('skipped','Skipped')],
        default='pending'
    )
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ['step_order']

    def __str__(self):
        return f"{self.proposal.event_title} • Step {self.step_order} [{self.role_required}] {self.status}"

# ────────────────────────────────────────────────────────────────
#  Media Request (unchanged)
# ────────────────────────────────────────────────────────────────
class MediaRequest(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('Poster', 'Poster'),
        ('Video', 'Video'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    event_date = models.DateField()
    media_file = models.FileField(upload_to='media_requests/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.media_type} request by {self.user.username}"

# ────────────────────────────────────────────────────────────────
#  EVENT REPORT
# ────────────────────────────────────────────────────────────────
class EventReport(models.Model):
    proposal = models.OneToOneField(EventProposal, on_delete=models.CASCADE, related_name='event_report')

    # Post-event fields
    location = models.CharField(max_length=200, blank=True)
    blog_link = models.URLField(blank=True)
    num_student_volunteers = models.PositiveIntegerField(null=True, blank=True)
    num_participants = models.PositiveIntegerField(null=True, blank=True)
    external_contact_details = models.TextField(blank=True)

    summary = models.TextField(blank=True)
    outcomes = models.TextField(blank=True)
    impact_on_stakeholders = models.TextField(blank=True)
    innovations_best_practices = models.TextField(blank=True)
    pos_pso_mapping = models.TextField(blank=True)
    needs_grad_attr_mapping = models.TextField(blank=True)
    contemporary_requirements = models.TextField(blank=True)
    sdg_value_systems_mapping = models.TextField(blank=True)
    iqac_feedback = models.TextField(blank=True)
    report_signed_date = models.DateField(default=timezone.now)
    beneficiaries_details = models.TextField(blank=True)

    # --- THIS IS THE NEW FIELD ---
    ai_generated_report = models.TextField(
        blank=True,
        null=True,
        help_text="This field will store the report generated by AI."
    )
    # -----------------------------

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class EventReportAttachment(models.Model):
    report = models.ForeignKey(EventReport, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='report_attachments/')
    caption = models.CharField(max_length=255, blank=True)