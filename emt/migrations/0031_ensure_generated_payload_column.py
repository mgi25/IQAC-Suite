from django.db import migrations, models


def ensure_generated_payload_column(apps, schema_editor):
    EventReport = apps.get_model("emt", "EventReport")
    table_name = EventReport._meta.db_table
    column_name = "generated_payload"

    connection = schema_editor.connection
    with connection.cursor() as cursor:
        existing_columns = {
            column.name
            for column in connection.introspection.get_table_description(cursor, table_name)
        }

    if column_name in existing_columns:
        return

    field = models.JSONField(blank=True, default=dict)
    field.set_attributes_from_name(column_name)
    schema_editor.add_field(EventReport, field)


class Migration(migrations.Migration):
    dependencies = [
        ("emt", "0030_alter_eventreportattachment_options_and_more"),
    ]

    operations = [
        migrations.RunPython(ensure_generated_payload_column, migrations.RunPython.noop),
    ]
