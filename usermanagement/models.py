from django.conf import settings
from django.db import models
from django.db.models import Q

from core.models import Organization


class JoinRequest(models.Model):
    TYPE_JOIN = "join"
    TYPE_LEAVE = "leave"

    REQUEST_TYPE_CHOICES = [
        (TYPE_JOIN, "Join"),
        (TYPE_LEAVE, "Leave"),
    ]

    STATUS_PENDING = "Pending"
    STATUS_APPROVED = "Approved"
    STATUS_REJECTED = "Rejected"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    request_type = models.CharField(
        max_length=12,
        choices=REQUEST_TYPE_CHOICES,
        default=TYPE_JOIN,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    is_seen = models.BooleanField(default=False)
    requested_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    response_message = models.TextField(blank=True)

    class Meta:
        verbose_name = "Membership Request"
        verbose_name_plural = "Membership Requests"
        ordering = ("-requested_on",)
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization", "request_type"],
                condition=Q(status="Pending"),
                name="unique_pending_join_request",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.organization} ({self.get_request_type_display()} • {self.status})"

    def mark_seen(self):
        if not self.is_seen:
            self.is_seen = True
            self.save(update_fields=["is_seen"])
