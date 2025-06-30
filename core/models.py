from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('faculty', 'Faculty'),
        ('hod', 'HOD'),
        ('dept_iqac', 'Department IQAC Coordinator'),
        ('club', 'Club'),
        ('center', 'Center'),
        ('dean', 'Dean'),
        ('director', 'Director'),
        ('cdl', 'CDL'),
        ('uni_iqac', 'University IQAC Coordinator'),
        ('admin', 'Admin'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='student')

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


class EventProposal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
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
