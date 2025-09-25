from django.db import migrations, models


def ensure_requires_extraction_column(apps, schema_editor):
    Attachment = apps.get_model("emt", "EventReportAttachment")
    table_name = Attachment._meta.db_table
    column_name = "requires_extraction"

    connection = schema_editor.connection
    with connection.cursor() as cursor:
        existing_columns = {
            column.name
            for column in connection.introspection.get_table_description(cursor, table_name)
        }

    if column_name in existing_columns:
        return

    field = models.BooleanField(default=False)
    field.set_attributes_from_name(column_name)
    schema_editor.add_field(Attachment, field)


class Migration(migrations.Migration):

    dependencies = [
        ("emt", "0031_ensure_generated_payload_column"),
    ]

    operations = [
        migrations.RunPython(
            ensure_requires_extraction_column, migrations.RunPython.noop
        ),
    ]
