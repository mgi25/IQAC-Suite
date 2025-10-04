from django.db import migrations, models, connection


def add_missing_columns(apps, schema_editor):
    # Check existing columns on emt_eventreport
    with connection.cursor() as cursor:
        table = 'emt_eventreport'
        existing_cols = {col.name for col in connection.introspection.get_table_description(cursor, table)}

    EventReport = apps.get_model('emt', 'EventReport')

    if 'session_feedback' not in existing_cols:
        field = models.TextField(blank=True, help_text='Latest review feedback for current session')
        field.set_attributes_from_name('session_feedback')
        schema_editor.add_field(EventReport, field)

    if 'review_stage' not in existing_cols:
        field = models.CharField(max_length=20, choices=[
            ('user', 'With Submitter'),
            ('diqac', 'D-IQAC Coordinator'),
            ('hod', 'Head of Department'),
            ('uiqac', 'University IQAC Coordinator'),
            ('finalized', 'Finalized'),
        ], default='user')
        field.set_attributes_from_name('review_stage')
        schema_editor.add_field(EventReport, field)


def noop_reverse(apps, schema_editor):
    # Non-destructive migration; nothing to remove on reverse
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('emt', '0030_eventreport_review_stage_and_more'),
    ]

    operations = [
        migrations.RunPython(add_missing_columns, noop_reverse),
    ]
