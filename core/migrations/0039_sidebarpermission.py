from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0038_merge_20250816_1901'),
    ]

    operations = [
    migrations.CreateModel(
            name='SidebarPermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        ('role', models.CharField(blank=True, max_length=50)),
        ('items', models.JSONField(blank=True, default=dict)),
        ('user', models.ForeignKey(blank=True, null=True, on_delete=models.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
        'unique_together': {('user', 'role')},
            },
        ),
    ]
