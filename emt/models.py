from django.db import models
from django.contrib.auth.models import User

# ────────────────────────────────────────────────────────────────
#  Master table – Departments  (simple, extensible)
# ────────────────────────────────────────────────────────────────
class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# ────────────────────────────────────────────────────────────────
#  MAIN PROPOSAL
# ────────────────────────────────────────────────────────────────
class EventProposal(models.Model):
    submitted_by   = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="emt_eventproposals"
    )

    # smart FK instead of free-text
    department     = models.ForeignKey(
        Department, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="proposals"
    )

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

    # smart Many-to-Many instead of comma text
    faculty_incharges    = models.ManyToManyField(
        User, blank=True, related_name="faculty_incharge_proposals"
    )
    student_coordinators = models.TextField(blank=True)

    event_focus_type     = models.CharField(max_length=200, blank=True)
    report_generated     = models.BooleanField(default=False)

    # ------------- Income -------------
    fest_fee_participants     = models.PositiveIntegerField(null=True, blank=True)
    fest_fee_rate             = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fest_fee_amount           = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    fest_sponsorship_amount   = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    conf_fee_participants     = models.PositiveIntegerField(null=True, blank=True)
    conf_fee_rate             = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    conf_fee_amount           = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    conf_sponsorship_amount   = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # meta
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    STATUS_CHOICES = [
        ('draft',        'Draft'),
        ('submitted',    'Submitted'),
        ('under_review', 'Under Review'),
        ('approved',     'Approved'),
        ('rejected',     'Rejected'),
        ('returned',     'Returned for Revision'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    def __str__(self):
        return self.event_title or f"Proposal #{self.id}"


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
