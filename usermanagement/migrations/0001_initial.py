# Generated manually for JoinRequest model
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0047_studentachievement_backfill"),
    ]

    operations = [
        migrations.CreateModel(
            name="JoinRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("Pending", "Pending"), ("Approved", "Approved"), ("Rejected", "Rejected")], default="Pending", max_length=20)),
                ("is_seen", models.BooleanField(default=False)),
                ("requested_on", models.DateTimeField(auto_now_add=True)),
                ("updated_on", models.DateTimeField(auto_now=True)),
                ("response_message", models.TextField(blank=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.organization")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Join Request",
                "verbose_name_plural": "Join Requests",
                "ordering": ("-requested_on",),
            },
        ),
        migrations.AddConstraint(
            model_name="joinrequest",
            constraint=models.UniqueConstraint(
                condition=Q(status="Pending"),
                fields=("user", "organization"),
                name="unique_pending_join_request",
            ),
        ),
    ]
