from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("emt", "0030_eventreport_status"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE emt_eventreport
                        ADD COLUMN IF NOT EXISTS review_stage VARCHAR(20);
                    """,
                    reverse_sql="""
                        ALTER TABLE emt_eventreport
                        DROP COLUMN IF EXISTS review_stage;
                    """,
                ),
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE emt_eventreport
                        ALTER COLUMN review_stage SET DEFAULT 'draft';
                    """,
                    reverse_sql="""
                        ALTER TABLE emt_eventreport
                        ALTER COLUMN review_stage DROP DEFAULT;
                    """,
                ),
                migrations.RunSQL(
                    sql="""
                        UPDATE emt_eventreport
                        SET review_stage = COALESCE(NULLIF(review_stage, ''), 'draft');
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE emt_eventreport
                        ALTER COLUMN review_stage SET NOT NULL;
                    """,
                    reverse_sql="""
                        ALTER TABLE emt_eventreport
                        ALTER COLUMN review_stage DROP NOT NULL;
                    """,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="eventreport",
                    name="review_stage",
                    field=models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("submitted", "Submitted"),
                            ("under_review", "Under Review"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("finalized", "Finalized"),
                        ],
                        default="draft",
                        editable=False,
                        help_text="Internal field to track the latest review stage for the report.",
                        max_length=20,
                    ),
                ),
            ],
        ),
    ]
