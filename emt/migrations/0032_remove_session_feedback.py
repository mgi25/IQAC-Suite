
from django.db import migrations


def drop_session_feedback(apps, schema_editor):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        vendor = connection.vendor
        if vendor == "sqlite":
            cursor.execute("PRAGMA table_info('emt_eventreport')")
            columns = {row[1] for row in cursor.fetchall()}
            if "session_feedback" not in columns:
                return
            cursor.execute("ALTER TABLE emt_eventreport DROP COLUMN session_feedback")
        elif vendor == "postgresql":
            cursor.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = 'emt_eventreport'
                  AND column_name = 'session_feedback'
                """
            )
            if cursor.fetchone() is None:
                return
            cursor.execute("ALTER TABLE emt_eventreport DROP COLUMN session_feedback")
        else:
            raise NotImplementedError(f"Unsupported database vendor: {vendor}")


class Migration(migrations.Migration):

    dependencies = [
        ("emt", "0031_eventreport_review_stage"),
    ]

    operations = [
        migrations.RunPython(drop_session_feedback, migrations.RunPython.noop),
    ]
