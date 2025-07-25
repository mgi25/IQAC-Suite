from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0012_organizationrole'),
    ]

    operations = [
        migrations.DeleteModel(
            name='OrganizationRole',
        ),
        migrations.CreateModel(
            name='OrganizationRole',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('org_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='roles', to='core.organizationtype')),
            ],
            options={
                'ordering': ['name'],
                'unique_together': {('org_type', 'name')},
            },
        ),
    ]
