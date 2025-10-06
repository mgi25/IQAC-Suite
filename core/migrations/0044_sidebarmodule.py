from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0043_proofreadsubmission_proofreaditem"),
    ]

    operations = [
        migrations.CreateModel(
            name="SidebarModule",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=100, unique=True)),
                ("label", models.CharField(max_length=120)),
                ("order", models.PositiveIntegerField(db_index=True, default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=models.deletion.CASCADE, related_name="children", to="core.sidebarmodule")),
            ],
            options={"ordering": ["parent__id", "order", "key"]},
        ),
    ]
