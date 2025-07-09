from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

# ────────────────────────────────────────────────────────────────
#  Organisations (master tables)
# ────────────────────────────────────────────────────────────────
class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class Club(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class Center(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class Cell(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class Association(models.Model):
    """
    An Association belongs *optionally* to a Department.
    """
    name = models.CharField(max_length=100, unique=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="associations",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        if self.department:
            return f"{self.name} ({self.department})"
        return self.name

# ────────────────────────────────────────────────────────────────
#  User Role Assignment
# ────────────────────────────────────────────────────────────────
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
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)
    club = models.ForeignKey(Club, null=True, blank=True, on_delete=models.SET_NULL)
    center = models.ForeignKey(Center, null=True, blank=True, on_delete=models.SET_NULL)
    cell = models.ForeignKey(Cell, null=True, blank=True, on_delete=models.SET_NULL)
    association = models.ForeignKey(Association, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = (
            "user",
            "role",
            "department",
            "club",
            "center",
            "cell",
            "association",
        )

    def __str__(self):
        parts = [self.get_role_display()]
        if self.department:
            parts.append(f"of {self.department}")
        if self.club:
            parts.append(f"of {self.club}")
        if self.center:
            parts.append(f"of {self.center}")
        if self.cell:
            parts.append(f"of {self.cell}")
        if self.association:
            parts.append(f"of {self.association}")
        return f"{self.user.username} – {' '.join(parts)}"

# ────────────────────────────────────────────────────────────────
#  User Profile (extension of auth.User, optional)
# ────────────────────────────────────────────────────────────────
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

# ────────────────────────────────────────────────────────────────
#  Event Proposals & Reports (legacy part of core app)
# ────────────────────────────────────────────────────────────────
class EventProposal(models.Model):
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True
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
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True
    )
    submitted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_reports",
    )
    date_submitted = models.DateTimeField(auto_now_add=True)
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
