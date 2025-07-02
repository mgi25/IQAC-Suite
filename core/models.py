from django.db import models
from django.contrib.auth.models import User

# --- Department, Club, Center Models ---

class Department(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Club(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Center(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

# --- User Role Assignment ---

class RoleAssignment(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('faculty', 'Faculty'),
        ('hod', 'HOD'),
        ('dept_iqac', 'Department IQAC Coordinator'),
        ('club_head', 'Club Head'),
        ('center_head', 'Center Head'),
        ('dean', 'Dean'),
        ('director', 'Director'),
        ('cdl', 'CDL'),
        ('uni_iqac', 'University IQAC Coordinator'),
        ('admin', 'Admin'),
        ('academic_coordinator', 'Academic Coordinator'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='role_assignments')
    role = models.CharField(max_length=30, choices=ROLE_CHOICES)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL, related_name='role_assignments')
    club = models.ForeignKey(Club, null=True, blank=True, on_delete=models.SET_NULL, related_name='role_assignments')
    center = models.ForeignKey(Center, null=True, blank=True, on_delete=models.SET_NULL, related_name='role_assignments')

    def __str__(self):
        details = [self.get_role_display()]
        if self.department:
            details.append(f"of {self.department}")
        if self.club:
            details.append(f"of {self.club}")
        if self.center:
            details.append(f"of {self.center}")
        return f"{self.user.username} - {' '.join(details)}"

    class Meta:
        unique_together = ('user', 'role', 'department', 'club', 'center')

# --- User Profile ---

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    main_role = models.CharField(max_length=30, blank=True, null=True)

    @property
    def role(self):
        return self.main_role

    @role.setter
    def role(self, value):
        self.main_role = value

    def __str__(self):
        return f"{self.user.username} - {self.main_role or 'No main role'}"

# --- Event Proposals ---

class EventProposal(models.Model):
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    user_type = models.CharField(max_length=30)  # summary of main role(s)
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_proposals')
    title = models.CharField(max_length=200)
    description = models.TextField()
    date_submitted = models.DateTimeField(auto_now_add=True)
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('returned', 'Returned for Revision'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    return_comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

# --- Reports ---

class Report(models.Model):
    REPORT_TYPE_CHOICES = [
        ('annual', 'Annual'),
        ('event', 'Event'),
        ('iqac', 'IQAC'),
        ('custom', 'Custom'),
    ]
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_reports')
    date_submitted = models.DateTimeField(auto_now_add=True)
    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES, default='custom')
    file = models.FileField(upload_to='reports/', blank=True, null=True)
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    feedback = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} - {self.get_report_type_display()} ({self.get_status_display()})"

