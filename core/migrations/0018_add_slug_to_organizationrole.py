from django.db import migrations, models
from django.utils.text import slugify


def populate_slugs(apps, schema_editor):
    OrganizationRole = apps.get_model('core', 'OrganizationRole')
    for role in OrganizationRole.objects.all():
        base = slugify(role.name)
        slug = base
        counter = 2
        existing = set(
            OrganizationRole.objects.filter(organization_id=role.organization_id).exclude(pk=role.pk).values_list('slug', flat=True)
        )
        while slug in existing or slug == "":
            slug = f"{base}-{counter}"
            counter += 1
        role.slug = slug
        role.save(update_fields=['slug'])

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_merge_20250730_0935'),
    ]

    operations = [
        migrations.AddField(
            model_name='organizationrole',
            name='slug',
            field=models.SlugField(blank=True, editable=False, max_length=100),
        ),
        migrations.RunPython(populate_slugs, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name='organizationrole',
            unique_together={('organization', 'name'), ('organization', 'slug')},
        ),
    ]
