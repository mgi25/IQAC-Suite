from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

# ───────────────────────────────
#  New Generic Organization Models
# ───────────────────────────────

# models.py
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
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ("name", "org_type")
        ordering = ["org_type__name", "name"]

    def __str__(self):
        return f"{self.name} ({self.org_type.name})"


class OrganizationRole(models.Model):
    org_type = models.ForeignKey(
        OrganizationType, on_delete=models.CASCADE, related_name="roles"
    )
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ("org_type", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.org_type.name})"

# ───────────────────────────────
#  User Role Assignment (now generic)
# ───────────────────────────────

class RoleAssignment(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('faculty', 'Faculty'),
        ('hod', 'HOD'),
        ('dept_iqac', 'Department IQAC Coordinator'),
        ('club_head', 'Club Head'),
        ('center_head', 'Center Head'),
        ('cell_head', 'Cell Head'),
        ('association_head', 'Association Head'),
        ('dean', 'Dean'),
        ('cdl', 'CDL'),
        ('uni_iqac', 'University IQAC Coordinator'),
        ('admin', 'Admin'),
        ('academic_coordinator', 'Academic Coordinator'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='role_assignments')
    role = models.CharField(max_length=30, choices=ROLE_CHOICES)
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ("user", "role", "organization")

    def __str__(self):
        parts = [self.get_role_display()]
        if self.organization:
            parts.append(f"of {self.organization}")
        return f"{self.user.username} – {' '.join(parts)}"

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
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default="student")

    def __str__(self):
        return f"{self.user.username} ({self.role})"

# ───────────────────────────────
#  Event Proposals & Reports
# ───────────────────────────────

class EventProposal(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True
    )
    user_type = models.CharField(max_length=30)  # summary of main role(s)
    submitted_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="event_proposals"
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    date_submitted = models.DateTimeField(auto_now_add=True)

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("under_review", "Under Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("returned", "Returned for Revision"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    return_comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

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
#  Programs & Outcomes (update FKs if needed)
# ───────────────────────────────

class Program(models.Model):
    name = models.CharField(max_length=150, unique=True)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self):
        return self.name

class ProgramOutcome(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="pos")
    description = models.TextField()
    def __str__(self):
        return f"PO - {self.program.name}"

class ProgramSpecificOutcome(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="psos")
    description = models.TextField()
    def __str__(self):
        return f"PSO - {self.program.name}"

class ApprovalFlowTemplate(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="approval_flow_templates")
    step_order = models.PositiveIntegerField()
    role_required = models.CharField(max_length=50)  # e.g., "faculty", "hod"
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)  # If you want to fix to a person (optional)

    class Meta:
        unique_together = ('organization', 'step_order')
        ordering = ['organization', 'step_order']
