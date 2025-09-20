from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0025_class_academic_year_class_organization"),
    ]

    operations = [
        migrations.AddField(
            model_name="roleassignment",
            name="academic_year",
            field=models.CharField(blank=True, db_index=True, max_length=9, null=True),
        ),
        migrations.AddField(
            model_name="roleassignment",
            name="class_name",
            field=models.CharField(blank=True, db_index=True, max_length=64, null=True),
        ),
        migrations.AddIndex(
            model_name="roleassignment",
            index=models.Index(
                fields=["organization", "academic_year", "class_name"],
                name="core_ra_org_year_class_idx",
            ),
        ),
    ]
