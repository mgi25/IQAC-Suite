# Generated by Django 5.2.3 on 2025-07-25 06:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_organizationrole"),
    ]

    operations = [
        migrations.AddField(
            model_name="organizationrole",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
    ]
