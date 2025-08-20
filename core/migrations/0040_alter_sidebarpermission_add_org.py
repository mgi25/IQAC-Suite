from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0039_sidebarpermission'),
    ]

    operations = [
        migrations.AddField(
            model_name='sidebarpermission',
            name='organization',
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.CASCADE, to='core.organization'),
        ),
        migrations.AlterField(
            model_name='sidebarpermission',
            name='items',
            field=models.JSONField(default=dict, blank=True),
        ),
        migrations.AlterUniqueTogether(
            name='sidebarpermission',
            unique_together={('user', 'role', 'organization')},
        ),
    ]
