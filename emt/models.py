from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from core.models import Organization, SDGGoal


# ────────────────────────────────────────────────────────────────
#  MAIN PROPOSAL
# ────────────────────────────────────────────────────────────────
class EventProposal(models.Model):
    """The central model for capturing all event proposal details."""

    @property
    def title(self):
        """Convenience property to return the proposal's event title."""
        return self.event_title or "Untitled Event"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        WAITING = "waiting", "Waiting for Action"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        RETURNED = "returned", "Returned for Revision"
        FINALIZED = "finalized", "Finalized"

    submitted_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="emt_eventproposals"
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emt_proposals",
    )

    # Approval flags
    needs_finance_approval = models.BooleanField(
        default=False, help_text="Check if this event needs finance approval"
    )
    is_big_event = models.BooleanField(
        default=False, help_text="Check if this is a big event (Dean sign-off needed)"
    )

    committees = models.TextField(blank=True, help_text="List of committees involved.")
    sdg_goals = models.ManyToManyField(
        SDGGoal, blank=True, related_name="event_proposals"
    )
    committees_collaborations = models.TextField(
        blank=True, help_text="Committees and collaborations involved."
    )
    event_title = models.CharField(max_length=200, blank=False)
    num_activities = models.PositiveIntegerField(null=True, blank=True)
    event_datetime = models.DateTimeField(null=True, blank=True)
    event_start_date = models.DateField(null=True, blank=True)
    event_end_date = models.DateField(null=True, blank=True)
    venue = models.CharField(max_length=200, blank=True)
    academic_year = models.CharField(max_length=20, blank=True)
    target_audience = models.CharField(max_length=200, blank=True)
    pos_pso = models.TextField(blank=True)

    faculty_incharges = models.ManyToManyField(
        User, blank=True, related_name="faculty_incharge_proposals"
    )
    # UPDATED: Changed from TextField to ManyToManyField for better data integrity
    student_coordinators = models.TextField(
        blank=True, help_text="Comma-separated student coordinator names (temporary)."
    )

    event_focus_type = models.CharField(max_length=200, blank=True)
    report_generated = models.BooleanField(default=False)

    # Report assignment field
    report_assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_report_tasks",
        help_text="User assigned to generate the report for this event",
    )
    report_assigned_at = models.DateTimeField(null=True, blank=True)

    # Income fields
    fest_fee_participants = models.PositiveIntegerField(null=True, blank=True)
    fest_fee_rate = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    fest_fee_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    fest_sponsorship_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    conf_fee_participants = models.PositiveIntegerField(null=True, blank=True)
    conf_fee_rate = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    conf_fee_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    conf_sponsorship_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )

    class Meta:
        verbose_name = "Event Proposal"
        verbose_name_plural = "Event Proposals"
        ordering = ["-created_at"]

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

    proposal = models.OneToOneField(
        EventProposal, on_delete=models.CASCADE, related_name="need_analysis"
    )
    content = models.TextField()


class EventObjectives(models.Model):
    """Stores the objectives for an event proposal."""

    proposal = models.OneToOneField(
        EventProposal, on_delete=models.CASCADE, related_name="objectives"
    )
    content = models.TextField()


class EventExpectedOutcomes(models.Model):
    """Stores the expected outcomes for an event proposal."""

    proposal = models.OneToOneField(
        EventProposal, on_delete=models.CASCADE, related_name="expected_outcomes"
    )
    content = models.TextField()


class TentativeFlow(models.Model):
    """Stores the tentative flow of events for a proposal."""

    proposal = models.OneToOneField(
        EventProposal, on_delete=models.CASCADE, related_name="tentative_flow"
    )
    content = models.TextField()


class EventActivity(models.Model):
    """Represents a planned activity within an event proposal."""

    proposal = models.ForeignKey(
        EventProposal, on_delete=models.CASCADE, related_name="activities"
    )
    name = models.CharField(max_length=255)
    date = models.DateField()

    class Meta:
        ordering = ["date", "id"]


# ────────────────────────────────────────────────────────────────
#  Speaker & Expense
# ────────────────────────────────────────────────────────────────
class SpeakerProfile(models.Model):
    """Stores the profile of a speaker for an event."""

    proposal = models.ForeignKey(
        EventProposal, on_delete=models.CASCADE, related_name="speakers"
    )
    full_name = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    affiliation = models.CharField(max_length=100)
    contact_email = models.EmailField()
    contact_number = models.CharField(max_length=15)
    linkedin_url = models.URLField(
        blank=True, null=True, help_text="LinkedIn profile URL"
    )
    photo = models.ImageField(upload_to="speakers/", blank=True, null=True)
    detailed_profile = models.TextField()

    def __str__(self):
        return f"{self.full_name} for {self.proposal.event_title}"


class ExpenseDetail(models.Model):
    """Stores a single line item of an expense for a proposal."""

    proposal = models.ForeignKey(
        EventProposal, on_delete=models.CASCADE, related_name="expense_details"
    )
    sl_no = models.PositiveIntegerField()
    particulars = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["sl_no"]
        verbose_name = "Expense Detail"
        verbose_name_plural = "Expense Details"


class IncomeDetail(models.Model):
    """Stores a single line item of income for a proposal."""

    proposal = models.ForeignKey(
        EventProposal, on_delete=models.CASCADE, related_name="income_details"
    )
    sl_no = models.PositiveIntegerField()
    particulars = models.CharField(max_length=200)
    participants = models.PositiveIntegerField()
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["sl_no"]
        verbose_name = "Income Detail"
        verbose_name_plural = "Income Details"


# ────────────────────────────────────────────────────────────────
#  Approval Steps
# ────────────────────────────────────────────────────────────────
class ApprovalStepQuerySet(models.QuerySet):
    def visible_for_ui(self):
        """Hide optional steps that were never forwarded for display."""
        return self.exclude(
            is_optional=True,
            optional_unlocked=False,
        ).exclude(
            is_optional=True,
            status=ApprovalStep.Status.SKIPPED,
        )

    # Backwards compatibility with previous helper name
    visible_for_status = visible_for_ui


class ApprovalStep(models.Model):
    """Represents a single step in the approval workflow for a proposal."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SKIPPED = "skipped", "Skipped"

    class Role(models.TextChoices):
        FACULTY = "faculty", "Faculty"
        FACULTY_INCHARGE = "faculty_incharge", "Faculty In-Charge"
        DEPT_IQAC = "dept_iqac", "Department IQAC"
        HOD = "hod", "Head of Department"
        DIRECTOR = "director", "Director"
        DEAN = "dean", "Dean"
        FINANCE = "finance", "Finance Officer"

    proposal = models.ForeignKey(
        EventProposal, on_delete=models.CASCADE, related_name="approval_steps"
    )
    step_order = models.PositiveIntegerField(null=True, blank=True)
    order_index = models.PositiveIntegerField(default=0)
    role_required = models.CharField(
        max_length=50, choices=Role.choices, null=True, blank=True
    )
    assigned_to = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_approvals",
    )
    approved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="completed_approvals",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    is_optional = models.BooleanField(default=False)
    optional_unlocked = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    decided_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="decided_steps",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True)
    comment = models.TextField(blank=True)

    objects = ApprovalStepQuerySet.as_manager()

    class Meta:
        ordering = ["order_index"]
        verbose_name = "Approval Step"
        verbose_name_plural = "Approval Steps"

    def __str__(self):
        return (
            f"{self.proposal.event_title} • Step {self.step_order} "
            f"[{self.get_role_required_display()}] {self.get_status_display()}"
        )


# ────────────────────────────────────────────────────────────────
#  Media Request
# ────────────────────────────────────────────────────────────────
class MediaRequest(models.Model):
    """A model to track requests for media creation (e.g., posters)."""

    class MediaType(models.TextChoices):
        POSTER = "Poster", "Poster"
        VIDEO = "Video", "Video"

    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        COMPLETED = "Completed", "Completed"
        REJECTED = "Rejected", "Rejected"

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    media_type = models.CharField(max_length=20, choices=MediaType.choices)
    title = models.CharField(max_length=200)
    description = models.TextField()
    event_date = models.DateField()
    media_file = models.FileField(upload_to="media_requests/", null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_media_type_display()} request by {self.user.username}"


# ────────────────────────────────────────────────────────────────
#  CDL SUPPORT REQUEST
# ────────────────────────────────────────────────────────────────
class CDLSupport(models.Model):
    """Optional support request from CDL while submitting a proposal.

    The model stores information gathered in two phases:
    pre‑event requirements (posters, certificates and other services) and
    post‑event certificate processing.
    """

    class PosterChoice(models.TextChoices):
        CDL_CREATE = "cdl_create", "Ask CDL to make the poster"
        PROVIDE_DESIGN = "provide_design", "Provide my own poster design"

    class CertificateChoice(models.TextChoices):
        CDL_CREATE = "cdl_create", "Ask CDL to make the certificate"
        PROVIDE_TEMPLATE = "provide_template", "Provide my own certificate template"

    proposal = models.OneToOneField(
        EventProposal,
        on_delete=models.CASCADE,
        related_name="cdl_support",
    )

    # General toggle for CDL support
    needs_support = models.BooleanField(default=False)

    # Manual completion flag to move items to Analysis page
    completed = models.BooleanField(default=False, help_text="When true, this event's CDL work is considered completed and shown under Analysis")
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cdl_completed_events",
    )

    # ─── Poster Details ─────────────────────────────────────────────
    poster_required = models.BooleanField(default=False)
    poster_choice = models.CharField(
        max_length=20, choices=PosterChoice.choices, blank=True
    )
    organization_name = models.CharField(max_length=255, blank=True)
    poster_time = models.CharField(max_length=100, blank=True)
    poster_date = models.DateField(null=True, blank=True)
    poster_venue = models.CharField(max_length=255, blank=True)
    resource_person_name = models.CharField(max_length=255, blank=True)
    resource_person_designation = models.CharField(max_length=255, blank=True)
    poster_event_title = models.CharField(max_length=255, blank=True)
    poster_summary = models.TextField(blank=True)
    poster_design_link = models.URLField(blank=True)

    # ─── Other CDL Services ─────────────────────────────────────────
    other_services = models.JSONField(default=list, blank=True)

    # ─── Certificate Requirements ───────────────────────────────────
    certificates_required = models.BooleanField(default=False)
    certificate_help = models.BooleanField(default=False)
    certificate_choice = models.CharField(
        max_length=20, choices=CertificateChoice.choices, blank=True
    )
    certificate_design_link = models.URLField(blank=True)

    # Optional pre-event blog content (unchanged requirement)
    blog_content = models.TextField(blank=True)

    def __str__(self):
        return f"CDL Support for {self.proposal.event_title}"


# ────────────────────────────────────────────────────────────────
#  CDL CERTIFICATE RECIPIENTS (POST-EVENT)
# ────────────────────────────────────────────────────────────────
class CDLCertificateRecipient(models.Model):
    class CertificateType(models.TextChoices):
        CORE_TEAM = "core_team", "Core Team Member"
        EVENT_HEAD = "event_head", "Event Head / Coordinator"
        PARTICIPANT = "participant", "Participant"
        OTHER = "other", "Other"

    support = models.ForeignKey(
        CDLSupport, on_delete=models.CASCADE, related_name="certificate_recipients"
    )
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=255, blank=True)
    certificate_type = models.CharField(max_length=30, choices=CertificateType.choices)
    ai_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_certificate_type_display()})"


# ────────────────────────────────────────────────────────────────
#  CDL COMMUNICATION THREAD
# ────────────────────────────────────────────────────────────────
class CDLMessage(models.Model):
    support = models.ForeignKey(
        CDLSupport, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField(blank=True)
    file = models.FileField(upload_to="cdl_messages/", null=True, blank=True)
    via_email = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Message by {self.sender} on {self.created_at:%Y-%m-%d}"


# ────────────────────────────────────────────────────────────────
#  CDL ASSIGNMENT (WORK TRACKING)
# ────────────────────────────────────────────────────────────────
class CDLAssignment(models.Model):
    class Status(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    proposal = models.OneToOneField(
        "EventProposal", on_delete=models.CASCADE, related_name="cdl_assignment"
    )
    assignee = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="cdl_assignments"
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cdl_assigned_events",
    )
    role = models.CharField(
        max_length=100,
        blank=True,
        help_text="Role context, e.g., 'CDL Head' or 'CDL Employee'",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ASSIGNED
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-assigned_at"]

    def __str__(self):
        return (
            f"{self.proposal.event_title} → "
            f"{self.assignee.get_full_name() or self.assignee.username} "
            f"({self.get_status_display()})"
        )


# ────────────────────────────────────────────────────────────────
#  CDL TASK ASSIGNMENTS (per resource for an event)
# ────────────────────────────────────────────────────────────────
class CDLTaskAssignment(models.Model):
    """Assign a specific CDL resource/task of an event to a member.

    Example resource_key values: 'poster', 'certificates', 'photography', 'videography', etc.
    Values come dynamically from CDLSupport fields (poster_required, certificates_required, other_services list).
    """

    class Status(models.TextChoices):
        BACKLOG = "backlog", "Backlog"
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In Progress"
        DONE = "done", "Done"

    proposal = models.ForeignKey(
        EventProposal, on_delete=models.CASCADE, related_name="cdl_task_assignments"
    )
    resource_key = models.CharField(max_length=100)
    label = models.CharField(
        max_length=200, blank=True, help_text="Display label for custom tasks"
    )
    assignee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cdl_resource_tasks",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ASSIGNED
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cdl_resource_tasks_assigned",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("proposal", "resource_key")
        indexes = [
            models.Index(fields=["assignee"]),
            models.Index(fields=["proposal", "resource_key"]),
        ]

    def __str__(self):
        return f"{self.proposal_id}:{self.resource_key} → {self.assignee_id or 'unassigned'} ({self.status})"


# ────────────────────────────────────────────────────────────────
#  EVENT REPORT
# ────────────────────────────────────────────────────────────────
class EventReport(models.Model):
    """Stores the post-event report, linked to the original proposal."""

    proposal = models.OneToOneField(
        EventProposal, on_delete=models.CASCADE, related_name="event_report"
    )
    location = models.CharField(max_length=200, blank=True)
    blog_link = models.URLField(blank=True)
    actual_event_type = models.CharField(max_length=200, blank=True)
    num_student_volunteers = models.PositiveIntegerField(null=True, blank=True)
    num_participants = models.PositiveIntegerField(null=True, blank=True)
    num_student_participants = models.PositiveIntegerField(blank=True, null=True)
    num_faculty_participants = models.PositiveIntegerField(blank=True, null=True)
    num_external_participants = models.PositiveIntegerField(blank=True, null=True)
    organizing_committee = models.TextField(blank=True)
    actual_speakers = models.TextField(blank=True)
    external_contact_details = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    key_achievements = models.TextField(blank=True)
    notable_moments = models.TextField(blank=True)
    outcomes = models.TextField(blank=True)
    learning_outcomes = models.TextField(blank=True)
    participant_feedback = models.TextField(blank=True)
    measurable_outcomes = models.TextField(blank=True)
    impact_assessment = models.TextField(blank=True)
    analysis = models.TextField(blank=True)
    objective_achievement = models.TextField(blank=True)
    strengths_analysis = models.TextField(blank=True)
    challenges_analysis = models.TextField(blank=True)
    effectiveness_analysis = models.TextField(blank=True)
    lessons_learned = models.TextField(blank=True)
    impact_on_stakeholders = models.TextField(blank=True)
    innovations_best_practices = models.TextField(blank=True)
    pos_pso_mapping = models.TextField(blank=True)
    needs_grad_attr_mapping = models.TextField(blank=True)
    contemporary_requirements = models.TextField(blank=True)
    sdg_value_systems_mapping = models.TextField(blank=True)
    iqac_feedback = models.TextField(blank=True)
    # Session-based review feedback (latest feedback message provided during approve/reject)
    session_feedback = models.TextField(blank=True, help_text="Latest review feedback for current session")
    class ReviewStage(models.TextChoices):
        USER = "user", "With Submitter"
        DIQAC = "diqac", "D-IQAC Coordinator"
        HOD = "hod", "Head of Department"
        UIQAC = "uiqac", "University IQAC Coordinator"
        FINALIZED = "finalized", "Finalized"
    # Current review stage for the report
    review_stage = models.CharField(max_length=20, choices=ReviewStage.choices, default=ReviewStage.USER)
    report_signed_date = models.DateField(default=timezone.now)
    beneficiaries_details = models.TextField(blank=True)
    # Optional notes about attendance to avoid integrity errors if left empty
    attendance_notes = models.TextField(blank=True, default="")
    ai_generated_report = models.TextField(
        blank=True,
        null=True,
        help_text="This field will store the report generated by AI.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Event Report"
        verbose_name_plural = "Event Reports"

    def __str__(self):
        return f"Report for {self.proposal.event_title}"


class EventReportMessage(models.Model):
    """Threaded communication for an EventReport across roles."""

    report = models.ForeignKey(EventReport, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Msg:{self.report_id} by {self.sender_id} @ {self.created_at:%Y-%m-%d %H:%M}"


class EventReportAttachment(models.Model):
    """An attachment (e.g., image, PDF) for an event report."""

    report = models.ForeignKey(
        EventReport, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to="report_attachments/")
    caption = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Attachment for {self.report.proposal.event_title}"


class AttendanceRow(models.Model):
    """Single attendance record linked to an event report."""

    class Category(models.TextChoices):
        STUDENT = "student", "Student"
        FACULTY = "faculty", "Faculty"
        EXTERNAL = "external", "External"

    event_report = models.ForeignKey(
        "emt.EventReport",
        on_delete=models.CASCADE,
        related_name="attendance_rows",
    )
    registration_no = models.CharField(max_length=32)
    full_name = models.CharField(max_length=128)
    student_class = models.CharField(max_length=128)
    absent = models.BooleanField(default=False)
    volunteer = models.BooleanField(default=False)
    category = models.CharField(
        max_length=16,
        choices=Category.choices,
        default=Category.STUDENT,
    )

    def __str__(self):
        return f"{self.full_name} ({self.registration_no})"


# ────────────────────────────────────────────────────────────────
#  STUDENT PROFILE
# ────────────────────────────────────────────────────────────────
class Student(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="student_profile"
    )
    mentor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="mentees"
    )
    events = models.ManyToManyField(
        "EventProposal", blank=True, related_name="participants"
    )
    # Add any other fields you need, for example:
    registration_number = models.CharField(max_length=50, blank=True)
    gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    attendance = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    def __str__(self):
        return self.user.get_full_name() or self.user.username
