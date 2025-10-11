from django.db import migrations


def create_student_achievement_table(apps, schema_editor):
    table_name = 'core_studentachievement'
    existing_tables = schema_editor.connection.introspection.table_names()
    if table_name in existing_tables:
        return

    StudentAchievement = apps.get_model('core', 'StudentAchievement')
    schema_editor.create_model(StudentAchievement)


def noop_reverse(apps, schema_editor):
    """Intentionally leave the table in place on reverse."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0046_studentachievement'),
    ]

    operations = [
        migrations.RunPython(create_student_achievement_table, noop_reverse),
    ]
