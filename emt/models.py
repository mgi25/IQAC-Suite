from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import Organization

# ────────────────────────────────────────────────────────────────
#  MAIN PROPOSAL
# ────────────────────────────────────────────────────────────────
class EventProposal(models.Model):
    """The central model for capturing all event proposal details."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SUBMITTED = 'submitted', 'Submitted'
        UNDER_REVIEW = 'under_review', 'Under Review'
        WAITING = 'waiting', 'Waiting for Action'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        RETURNED = 'returned', 'Returned for Revision'
        FINALIZED = 'finalized', 'Finalized'

    submitted_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="emt_eventproposals"
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name="emt_proposals"
    )

    # Approval flags
    needs_finance_approval = models.BooleanField(
        default=False, help_text="Check if this event needs finance approval"
    )
    is_big_event = models.BooleanField(
        default=False, help_text="Check if this is a big event (Dean sign-off needed)"
    )

    committees = models.TextField(blank=True, help_text="List of committees involved.")
    event_title = models.CharField(max_length=200, blank=True)
    num_activities = models.PositiveIntegerField(null=True, blank=True)
    event_datetime = models.DateTimeField(null=True, blank=True)
    venue = models.CharField(max_length=200, blank=True)
    academic_year = models.CharField(max_length=20, blank=True)
    target_audience = models.CharField(max_length=200, blank=True)

    faculty_incharges = models.ManyToManyField(
        User, blank=True, related_name="faculty_incharge_proposals"
    )
    # UPDATED: Changed from TextField to ManyToManyField for better data integrity
    student_coordinators = models.TextField(blank=True, help_text="Comma-separated student coordinator names (temporary).")

    event_focus_type = models.CharField(max_length=200, blank=True)
    report_generated = models.BooleanField(default=False)

    # Income fields
    fest_fee_participants = models.PositiveIntegerField(null=True, blank=True)
    fest_fee_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fest_fee_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    fest_sponsorship_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    conf_fee_participants = models.PositiveIntegerField(null=True, blank=True)
    conf_fee_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    conf_fee_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    conf_sponsorship_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        verbose_name = "Event Proposal"
        verbose_name_plural = "Event Proposals"
        ordering = ['-created_at']

    def __str__(self):
        return self.event_title or f"Proposal #{self.id}"

    @property
    def return_comment(self):
        """Return the comment from the latest rejected approval step, if any."""
        step = (
            self.approval_steps.filter(status=ApprovalStep.Status.REJECTED)
            .order_by("-step_order")
            .first()
        )
        return getattr(step, "comment", "")

# ────────────────────────────────────────────────────────────────
#  One-to-one / related tables
# ────────────────────────────────────────────────────────────────

class EventNeedAnalysis(models.Model):
    """Stores the need analysis content for an event proposal."""
    proposal = models.OneToOneField(EventProposal, on_delete=models.CASCADE, related_name='need_analysis')
    content = models.TextField()

class EventObjectives(models.Model):
    """Stores the objectives for an event proposal."""
    proposal = models.OneToOneField(EventProposal, on_delete=models.CASCADE, related_name='objectives')
    content = models.TextField()

class EventExpectedOutcomes(models.Model):
    """Stores the expected outcomes for an event proposal."""
    proposal = models.OneToOneField(EventProposal, on_delete=models.CASCADE, related_name='expected_outcomes')
    content = models.TextField()

class TentativeFlow(models.Model):
    """Stores the tentative flow of events for a proposal."""
    proposal = models.OneToOneField(EventProposal, on_delete=models.CASCADE, related_name='tentative_flow')
    content = models.TextField()

# ────────────────────────────────────────────────────────────────
#  Speaker & Expense
# ────────────────────────────────────────────────────────────────
class SpeakerProfile(models.Model):
    """Stores the profile of a speaker for an event."""
    proposal = models.ForeignKey(EventProposal, on_delete=models.CASCADE, related_name='speakers')
    full_name = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    affiliation = models.CharField(max_length=100)
    contact_email = models.EmailField()
    contact_number = models.CharField(max_length=15)
    photo = models.ImageField(upload_to='speakers/', blank=True, null=True)
    detailed_profile = models.TextField()

    def __str__(self):
        return f"{self.full_name} for {self.proposal.event_title}"

class ExpenseDetail(models.Model):
    """Stores a single line item of an expense for a proposal."""
    proposal = models.ForeignKey(EventProposal, on_delete=models.CASCADE, related_name='expense_details')
    sl_no = models.PositiveIntegerField()
    particulars = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['sl_no']
        verbose_name = "Expense Detail"
        verbose_name_plural = "Expense Details"

# ────────────────────────────────────────────────────────────────
#  Approval Steps
# ────────────────────────────────────────────────────────────────
class ApprovalStep(models.Model):
    """Represents a single step in the approval workflow for a proposal."""
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        SKIPPED = 'skipped', 'Skipped'

    class Role(models.TextChoices):
        FACULTY = 'faculty', 'Faculty'
        FACULTY_INCHARGE = 'faculty_incharge', 'Faculty In-Charge'
        DEPT_IQAC = 'dept_iqac', 'Department IQAC'
        HOD = 'hod', 'Head of Department'
        DIRECTOR = 'director', 'Director'
        DEAN = 'dean', 'Dean'
        FINANCE = 'finance', 'Finance Officer'

    proposal = models.ForeignKey(EventProposal, on_delete=models.CASCADE, related_name="approval_steps")
    step_order = models.PositiveIntegerField(null=True, blank=True)
    role_required = models.CharField(max_length=50, choices=Role.choices, null=True, blank=True)
    assigned_to = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_approvals")
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="completed_approvals")
    approved_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ['step_order']
        verbose_name = "Approval Step"
        verbose_name_plural = "Approval Steps"

    def __str__(self):
        return f"{self.proposal.event_title} • Step {self.step_order} [{self.get_role_required_display()}] {self.get_status_display()}"

# ────────────────────────────────────────────────────────────────
#  Media Request
# ────────────────────────────────────────────────────────────────
class MediaRequest(models.Model):
    """A model to track requests for media creation (e.g., posters)."""
    class MediaType(models.TextChoices):
        POSTER = 'Poster', 'Poster'
        VIDEO = 'Video', 'Video'

    class Status(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        COMPLETED = 'Completed', 'Completed'
        REJECTED = 'Rejected', 'Rejected'

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    media_type = models.CharField(max_length=20, choices=MediaType.choices)
    title = models.CharField(max_length=200)
    description = models.TextField()
    event_date = models.DateField()
    media_file = models.FileField(upload_to='media_requests/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_media_type_display()} request by {self.user.username}"


# ────────────────────────────────────────────────────────────────
#  CDL SUPPORT REQUEST
# ────────────────────────────────────────────────────────────────
class CDLSupport(models.Model):
    """Optional support request from CDL while submitting a proposal."""

    SUPPORT_CHOICES = [
        ("media", "Media Support"),
        ("poster", "Poster Support"),
        ("certificates", "Certificates"),
    ]

    proposal = models.OneToOneField(
        EventProposal,
        on_delete=models.CASCADE,
        related_name="cdl_support",
    )
    needs_support = models.BooleanField(default=False)
    blog_content = models.TextField(blank=True)
    poster_link = models.URLField(blank=True)
    support_options = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"CDL Support for {self.proposal.event_title}"

# ────────────────────────────────────────────────────────────────
#  EVENT REPORT
# ────────────────────────────────────────────────────────────────
class EventReport(models.Model):
    """Stores the post-event report, linked to the original proposal."""
    proposal = models.OneToOneField(EventProposal, on_delete=models.CASCADE, related_name='event_report')
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
    ai_generated_report = models.TextField(
        blank=True, null=True, help_text="This field will store the report generated by AI."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Event Report"
        verbose_name_plural = "Event Reports"

    def __str__(self):
        return f"Report for {self.proposal.event_title}"

class EventReportAttachment(models.Model):
    """An attachment (e.g., image, PDF) for an event report."""
    report = models.ForeignKey(EventReport, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='report_attachments/')
    caption = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Attachment for {self.report.proposal.event_title}"

# ────────────────────────────────────────────────────────────────
#  STUDENT PROFILE
# ────────────────────────────────────────────────────────────────
class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    mentor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='mentees')
    events = models.ManyToManyField('EventProposal', blank=True, related_name='participants')
    # Add any other fields you need, for example:
    registration_number = models.CharField(max_length=50, blank=True)
    gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    attendance = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username
