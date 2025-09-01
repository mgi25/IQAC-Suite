from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from django.db.models import Q

# Predefined Sustainable Development Goals
SDG_GOALS = [
    "No Poverty",
    "Zero Hunger",
    "Good Health and Well-Being",
    "Quality Education",
    "Gender Equality",
    "Clean Water and Sanitation",
    "Affordable and Clean Energy",
    "Decent Work and Economic Growth",
    "Industry, Innovation and Infrastructure",
    "Reduced Inequalities",
    "Sustainable Cities and Communities",
    "Responsible Consumption and Production",
    "Climate Action",
    "Life Below Water",
    "Life on Land",
    "Peace, Justice and Strong Institutions",
    "Partnerships for the Goals",
]
# ───────────────────────────────
#  New Generic Organization Models
# ───────────────────────────────

class ActiveManager(models.Manager):
    """Default manager that excludes archived records."""

    def get_queryset(self):
        qs = super().get_queryset()
        # Only apply if model has a status field
        if hasattr(self.model, "status"):
            return qs.filter(status="active")
        return qs


class AllObjectsManager(models.Manager):
    """Manager that returns all objects including archived."""
    pass


class ArchivableModel(models.Model):
    """
    Abstract base model to provide unified archive behavior instead of permanent deletion.

    Fields:
    - status: 'active' | 'archived'
    - archived_at, archived_by: metadata for audit and potential restoration.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE, db_index=True
    )
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="archived_%(class)ss"
    )

    # Managers
    objects = ActiveManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def archive(self, by: User | None = None):
        if self.status != self.Status.ARCHIVED:
            self.status = self.Status.ARCHIVED
            self.archived_at = timezone.now()
            self.archived_by = by
            self.save(update_fields=["status", "archived_at", "archived_by"]) 

    def restore(self):
        if self.status != self.Status.ACTIVE:
            self.status = self.Status.ACTIVE
            # keep archived_at/by for audit history
            self.save(update_fields=["status"]) 


class OrganizationType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    can_have_parent = models.BooleanField(default=False)
    parent_type = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='child_types')
    def __str__(self):
        return self.name

class Organization(models.Model):
    """
    Represents a single organization entry (e.g., Commerce Dept, Chess Club, Infotech Society)
    """
    name = models.CharField(max_length=100)
    org_type = models.ForeignKey(OrganizationType, on_delete=models.CASCADE, related_name="organizations")
    is_active = models.BooleanField(default=True)
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.CASCADE, related_name='children'
    )
    code = models.CharField(max_length=64, unique=True, null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("name", "org_type")
        ordering = ["org_type__name", "name"]

    def __str__(self):
        return f"{self.name} ({self.org_type.name})"

class OrganizationRole(ArchivableModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    # Deprecated in favor of `status`; retained for backward compatibility
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)  # <-- Add this line

    class Meta:
        unique_together = ("organization", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.organization.name})"

# ───────────────────────────────
#  User Role Assignment (now generic)
# ───────────────────────────────

class RoleAssignment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='role_assignments')
    role = models.ForeignKey('OrganizationRole', on_delete=models.CASCADE, null=True)
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL, related_name='role_assignments')
    academic_year = models.CharField(max_length=9, null=True, blank=True, db_index=True)
    class_name = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    class Meta:
        unique_together = ("user", "role", "organization")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role"],
                condition=Q(organization__isnull=True),
                name="unique_user_role_global",
            )
        ]
        indexes = [
            models.Index(
                fields=["organization", "academic_year", "class_name"],
                name="core_ra_org_year_class_idx",
            )
        ]

    def __str__(self):
        parts = [self.role.name]  # Use the OrganizationRole name
        if self.organization:
                parts.append(f"of {self.organization}")
        return f"{self.user.username} – {' '.join(parts)}"

    def get_contribution_percentage(self):
        """Calculate user's contribution percentage in this organization"""
        from django.db.models import Q
        from emt.models import EventProposal
        
        # Get total events in organization
        total_events = EventProposal.objects.filter(
            organization=self.organization
        ).count()
        
        if total_events == 0:
            return 0
            
        # Get user's events - count events where user is:
        # 1. The proposer (submitted_by)
        # 2. A faculty in-charge
        # 3. A participant (through Student profile)
        user_events_query = Q(organization=self.organization) & (
            Q(submitted_by=self.user) |  # User is the proposer
            Q(faculty_incharges=self.user) |  # User is faculty in-charge
            Q(participants__user=self.user)  # User is a participant through Student profile
        )
        
        user_events = EventProposal.objects.filter(user_events_query).distinct().count()
        
        return round((user_events / total_events) * 100, 1)


class OrganizationMembership(models.Model):
    ROLE_CHOICES = (("student", "Student"), ("faculty", "Faculty"), ("tutor", "Tutor"))

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="org_memberships")
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    academic_year = models.CharField(max_length=9)  # e.g., "2025-2026"
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default="student")
    is_primary = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "organization", "academic_year")
        indexes = [models.Index(fields=["organization", "academic_year", "role"])]

# ───────────────────────────────
#  User Profile (unchanged)
# ───────────────────────────────

class Profile(models.Model):
    ROLE_CHOICES = [
        ("student", "Student"),
        ("faculty", "Faculty"),
        ("hod", "HOD"),
        ("admin", "Admin"),
        ("club_convenor", "Club Convenor"),
        ("event_coordinator", "Event Coordinator"),
        ("committee_member", "Committee Member"),
        ("iqac_member", "IQAC Member"),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    register_no = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default="student")
    activated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

# ───────────────────────────────
#  Reports
# ───────────────────────────────

class Report(models.Model):
    REPORT_TYPE_CHOICES = [
        ("annual", "Annual"),
        ("event", "Event"),
        ("iqac", "IQAC"),
        ("custom", "Custom"),
    ]
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True
    )
    submitted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_reports",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES)
    file = models.FileField(upload_to="reports/", blank=True, null=True)

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    feedback = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} – {self.get_report_type_display()} ({self.get_status_display()})"

# ───────────────────────────────
#  Programs & Outcomes
# ───────────────────────────────

class Program(ArchivableModel):
    name = models.CharField(max_length=150, unique=True)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self):
        return self.name

class ProgramOutcome(ArchivableModel):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="pos")
    description = models.TextField()
    def __str__(self):
        return f"PO - {self.program.name}"

class ProgramSpecificOutcome(ArchivableModel):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="psos")
    description = models.TextField()
    def __str__(self):
        return f"PSO - {self.program.name}"

# ───────────────────────────────
#  PO/PSO Assignment Model
# ───────────────────────────────

class POPSOAssignment(models.Model):
    """
    Model to track which users are assigned to manage PO/PSO for specific organizations
    """
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="popso_assignments")
    assigned_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="popso_assignments")
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="made_assignments")
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ("organization", "assigned_user")
        ordering = ["-assigned_at"]
    
    def __str__(self):
        return f"{self.assigned_user.get_full_name()} assigned to {self.organization.name}"

# ───────────────────────────────
#  PO/PSO Change Notification Model
# ───────────────────────────────

class POPSOChangeNotification(models.Model):
    """
    Model to track notifications for PO/PSO changes made by assigned users
    """
    ACTION_CHOICES = [
        ('CREATE', 'Created'),
        ('UPDATE', 'Updated'), 
        ('DELETE', 'Deleted'),
    ]
    
    TYPE_CHOICES = [
        ('PO', 'Program Outcome'),
        ('PSO', 'Program Specific Outcome'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="popso_notifications_made")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    outcome_type = models.CharField(max_length=3, choices=TYPE_CHOICES)
    outcome_description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.user.get_full_name()} {self.action.lower()}d {self.outcome_type} for {self.organization.name}"


class SDGGoal(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

# ───────────────────────────────
#  Approval Flow Templates & Config
# ───────────────────────────────

class ApprovalFlowTemplate(ArchivableModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="approval_flow_templates")
    step_order = models.PositiveIntegerField()
    role_required = models.CharField(max_length=50)  # e.g., "faculty", "hod"
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)  # Optional: Fix to a specific user
    optional = models.BooleanField(default=False)

    class Meta:
        unique_together = ('organization', 'step_order')
        ordering = ['organization', 'step_order']

    def get_role_required_display(self):
        """Return a human friendly version of ``role_required``.

        If an :class:`OrganizationRole` exists for this template's organization
        with a name matching ``role_required`` (case-insensitive), use that
        name. Otherwise, return ``role_required`` converted to title case with
        underscores replaced by spaces.
        """

        role = OrganizationRole.objects.filter(
            organization=self.organization,
            name__iexact=self.role_required,
        ).first()
        if role:
            return role.name
        return self.role_required.replace("_", " ").title()

class ApprovalFlowConfig(models.Model):
    """
    Configuration flags for a department's approval flow, e.g. faculty-in-charge first.
    """
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="approval_flow_config",
    )
    require_faculty_incharge_first = models.BooleanField(default=False)

    def __str__(self):
        return f"Config for {self.organization.name}"

# ───────────────────────────────
#  Event Approval Box Visibility (Role & User)
# ───────────────────────────────

class RoleEventApprovalVisibility(models.Model):
    """
    Visibility preference for the dashboard event approvals box by role.
    """
    role = models.OneToOneField(
        OrganizationRole,
        on_delete=models.CASCADE,
        related_name="approval_visibility",
    )
    can_view = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.role} – {'Visible' if self.can_view else 'Hidden'}"

class UserEventApprovalVisibility(models.Model):
    """
    Per-user override for the approvals dashboard box.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="approval_box_overrides",
    )
    role = models.ForeignKey(OrganizationRole, on_delete=models.CASCADE)
    can_view = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user", "role")

    def __str__(self):
        return (
            f"{self.user.username} – {self.role} – {'Visible' if self.can_view else 'Hidden'}"
        )

# ───────────────────────────────
#  Class & Student Models
# ───────────────────────────────

class Class(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="classes",
        null=True,
        blank=True,
    )
    academic_year = models.CharField(max_length=9, null=True, blank=True)
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='classes')
    students = models.ManyToManyField('emt.Student', blank=True, related_name='classes')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

# ───────────────────────────────
#  Faculty Meetings (for org-wide faculty calendars)
# ───────────────────────────────

class FacultyMeeting(models.Model):
    """
    Simple meeting/event created by faculty members. Visible to all faculty
    within the same organization.
    """
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="faculty_meetings")
    scheduled_at = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_faculty_meetings")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-scheduled_at", "-created_at"]

    def __str__(self):
        when = timezone.localtime(self.scheduled_at).strftime('%Y-%m-%d %H:%M') if self.scheduled_at else '—'
        return f"{self.title} @ {when}"
    
class ImpersonationLog(models.Model):
    """Track user impersonation history"""
    original_user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='impersonations_made'
    )
    impersonated_user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='impersonations_received'
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
        
    def __str__(self):
        return f"{self.original_user} -> {self.impersonated_user} at {self.started_at}"


class ActivityLog(models.Model):
    """Generic activity log for auditing system actions"""
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
    )
    action = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.action}"

    def generate_description(self):
        """Build a concise plain-language description when none is provided."""
        params = {}
        if isinstance(self.metadata, dict):
            params = {k: v for k, v in self.metadata.items() if k != "user_agent"}

        username = "someone"
        if self.user:
            username = self.user.get_full_name() or self.user.username

        method, _, path = (self.action or "").partition(" ")
        verb_map = {
            "GET": "viewed",
            "POST": "submitted",
            "PUT": "updated",
            "PATCH": "updated",
            "DELETE": "deleted",
        }
        verb = verb_map.get(method.upper(), method.lower())

        path = path.split("?")[0]
        segments = [seg for seg in path.strip("/").split("/") if not seg.isdigit()]
        resource = " ".join(segments).replace("-", " ").strip() or "resource"

        obj_title = params.get("object_title") or params.get("title")
        description = f"{username} {verb} {resource}".strip()
        if obj_title:
            description += f' "{obj_title}"'

        return description

    def save(self, *args, **kwargs):
        if not self.description:
            self.description = self.generate_description()
        super().save(*args, **kwargs)

# Enhanced views with logging
def log_impersonation_start(request, target_user):
    """Log when impersonation starts"""
    ip = request.META.get('REMOTE_ADDR')
    ua = request.META.get('HTTP_USER_AGENT', '')
    ImpersonationLog.objects.create(
        original_user=request.user,
        impersonated_user=target_user,
        ip_address=ip,
        user_agent=ua
    )
    ActivityLog.objects.create(
        user=request.user,
        action="impersonation_start",
        description=(
            f"Started impersonating {target_user.username}. IP: {ip}. "
            f"User-Agent: {ua}."
        ),
        ip_address=ip,
        metadata={"target_user": target_user.id, "user_agent": ua},
    )

def log_impersonation_end(request):
    """Log when impersonation ends"""
    if 'impersonate_user_id' in request.session:
        try:
            log_entry = ImpersonationLog.objects.filter(
                original_user_id=request.session.get('original_user_id'),
                impersonated_user_id=request.session['impersonate_user_id'],
                ended_at__isnull=True
            ).first()

            if log_entry:
                log_entry.ended_at = timezone.now()
                log_entry.save()
                ip = request.META.get('REMOTE_ADDR')
                ua = request.META.get('HTTP_USER_AGENT', '')
                ActivityLog.objects.create(
                    user=log_entry.original_user,
                    action="impersonation_end",
                    description=(
                        f"Stopped impersonating {log_entry.impersonated_user.username}. "
                        f"IP: {ip}. User-Agent: {ua}."
                    ),
                    ip_address=ip,
                    metadata={
                        "target_user": log_entry.impersonated_user.id,
                        "user_agent": ua,
                    },
                )
        except Exception:
            pass  # Handle gracefully


# ────────────────────────────────────────────────────────────────
#  CDL SUPPORT MODELS
# ────────────────────────────────────────────────────────────────
class CDLRequest(models.Model):
    """Stores Creative & Design Lab requirements for an event proposal."""

    class PosterMode(models.TextChoices):
        MAKE_FROM_SCRATCH = "make", "Ask CDL to make the poster"
        CORRECT_EXISTING = "correct", "Provide my own poster for correction"

    class CertificateMode(models.TextChoices):
        MAKE_FROM_SCRATCH = "make", "Ask CDL to make the certificate"
        CORRECT_EXISTING = "correct", "Provide my own certificate for correction"

    proposal = models.OneToOneField(
        "emt.EventProposal",
        on_delete=models.CASCADE,
        related_name="cdl_request",
    )

    wants_cdl = models.BooleanField(default=False)

    # Poster related
    need_poster = models.BooleanField(default=False)
    poster_mode = models.CharField(
        max_length=20,
        choices=PosterMode.choices,
        blank=True,
    )
    poster_organization_name = models.CharField(max_length=255, blank=True)
    poster_time = models.CharField(max_length=100, blank=True)
    poster_date = models.CharField(max_length=100, blank=True)
    poster_venue = models.CharField(max_length=255, blank=True)
    poster_resource_person = models.CharField(max_length=255, blank=True)
    poster_resource_designation = models.CharField(max_length=255, blank=True)
    poster_title = models.CharField(max_length=255, blank=True)
    poster_summary = models.TextField(blank=True)
    poster_design_link = models.URLField(blank=True)
    poster_final_approved = models.BooleanField(default=False)

    # Other services
    svc_photography = models.BooleanField(default=False)
    svc_videography = models.BooleanField(default=False)
    svc_digital_board = models.BooleanField(default=False)
    svc_voluntary_cards = models.BooleanField(default=False)

    # Certificates
    need_certificate_any = models.BooleanField(default=False)
    need_certificate_cdl = models.BooleanField(default=False)
    certificate_mode = models.CharField(
        max_length=20,
        choices=CertificateMode.choices,
        blank=True,
    )
    certificate_design_link = models.URLField(blank=True)
    combined_design_link = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"CDL Request for {self.proposal}"  # pragma: no cover


class CDLCommunicationThread(models.Model):
    """One chat thread per proposal."""

    proposal = models.OneToOneField(
        "emt.EventProposal",
        on_delete=models.CASCADE,
        related_name="cdl_thread",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Thread for {self.proposal}"  # pragma: no cover


class CDLMessage(models.Model):
    thread = models.ForeignKey(
        CDLCommunicationThread,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="core_cdl_messages",
    )
    body = models.TextField()
    file = models.FileField(upload_to="cdl/messages/", blank=True, null=True)
    sent_via_email = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Message by {self.author} at {self.created_at}"  # pragma: no cover


class CertificateBatch(models.Model):
    class AIStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PASSED = "passed", "Passed"
        FAILED = "failed", "Failed"

    proposal = models.ForeignKey(
        "emt.EventProposal",
        on_delete=models.CASCADE,
        related_name="certificate_batches",
    )
    csv_file = models.FileField(upload_to="cdl/certificates/")
    ai_check_status = models.CharField(
        max_length=20, choices=AIStatus.choices, default=AIStatus.PENDING
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Certificate batch #{self.id} for {self.proposal}"  # pragma: no cover


class CertificateEntry(models.Model):
    class Role(models.TextChoices):
        CORE = "CORE", "Core"
        HEAD = "HEAD", "Head"
        PARTICIPANT = "PARTICIPANT", "Participant"
        OTHER = "OTHER", "Other"

    batch = models.ForeignKey(
        CertificateBatch,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=Role.choices)
    custom_role_text = models.CharField(max_length=255, blank=True)
    ai_valid = models.BooleanField(default=False)
    ai_errors = models.TextField(blank=True)
    ready_for_cdl = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.role})"  # pragma: no cover

class SidebarPermission(models.Model):
    """
    Stores allowed sidebar navigation items for a user or role.
    - Admins always bypass this (see all items).
    - If both user and role are blank → invalid.
    - 'items' stores a list of module keys: ["dashboard", "events", "cdl"].
    """
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, blank=True)
    items = models.JSONField(default=list, blank=True)

    class Meta:
        unique_together = ("user", "role")

    def __str__(self):
        target = self.user.username if self.user else self.role or "(unspecified)"
        return f"Sidebar permissions for {target}"

    @classmethod
    def get_allowed_items(cls, user):
        """
        Compute allowed sidebar items for a user.
        - Superuser/admins always get ALL.
        - Otherwise, combine role + user-specific assignments.
        - Expands children → parents (so parent is always shown if child assigned).
        """
        from core_admin.views import nav_items  # wherever nav_items is defined

        # Admin users see everything
        if user.is_superuser:
            return "ALL"

        # Try to get role safely from profile (if it exists)
        role = getattr(getattr(user, "profile", None), "role", None)
        if role and role.lower() == "admin":
            return "ALL"

        allowed = set()

        # --- Role-based permissions ---
        if role:
            role_perm = cls.objects.filter(role__iexact=role).first()
            if role_perm:
                allowed.update(role_perm.items)

        # --- User-specific overrides ---
        user_perm = cls.objects.filter(user=user).first()
        if user_perm:
            allowed.update(user_perm.items)

        # --- Expand to include parents ---
        def expand_with_parents(selected_ids, navs):
            expanded = set(selected_ids)

            def recurse(items, parent_id=None):
                for item in items:
                    if "children" in item:
                        for child in item["children"]:
                            if child["id"] in expanded:
                                expanded.add(item["id"])  # ensure parent is included
                        recurse(item["children"], item["id"])
            recurse(navs)
            return expanded

        return list(expand_with_parents(allowed, nav_items))

class DashboardAssignment(models.Model):
    """Stores dashboard assignments for users and roles."""
    DASHBOARD_CHOICES = [
        ('admin', 'Admin Dashboard'),
        ('faculty', 'Faculty Dashboard'),
        ('student', 'Student Dashboard'),
        ('cdl_head', 'CDL Head Dashboard'),
        ('cdl_work', 'CDL Work Dashboard'),
    ]
    
    DASHBOARD_PATHS = {
        'admin': 'core/admin_dashboard.html',
        'faculty': 'core/dashboard.html',
        'student': 'core/student_dashboard.html',
        'cdl_head': 'core/cdl_head_dashboard.html',
        'cdl_work': 'core/cdl_work_dashboard.html',
    }
    
    DASHBOARD_URLS = {
        'admin': 'admin_dashboard',
        'faculty': 'dashboard',
        'student': 'dashboard',
        'cdl_head': 'cdl_head_dashboard',
        'cdl_work': 'cdl_work_dashboard',
    }
    
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name='dashboard_assignments')
    role = models.CharField(max_length=50, blank=True)
    organization_type = models.ForeignKey(OrganizationType, null=True, blank=True, on_delete=models.CASCADE)
    dashboard = models.CharField(max_length=20, choices=DASHBOARD_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ("user", "role", "dashboard")
        ordering = ['dashboard']
    
    def __str__(self):
        target = self.user.username if self.user else self.role or "(unspecified)"
        return f"{target} -> {self.get_dashboard_display()}"
    
    @classmethod
    def get_user_dashboards(cls, user):
        """Get all assigned dashboards for a user"""
        # Admin users get all dashboards
        if user.is_superuser:
            return cls.DASHBOARD_CHOICES
        
        # Get user-specific assignments
        user_assignments = cls.objects.filter(
            user=user, 
            is_active=True
        ).values_list('dashboard', flat=True)
        
        # Get role-based assignments
        user_roles = RoleAssignment.objects.filter(user=user).values_list('role__name', flat=True)
        role_assignments = cls.objects.filter(
            role__in=[role.lower() for role in user_roles],
            is_active=True
        ).values_list('dashboard', flat=True)
        
        # Combine and get dashboard info
        all_dashboards = set(user_assignments) | set(role_assignments)
        return [(dash, dict(cls.DASHBOARD_CHOICES)[dash]) for dash in all_dashboards]
