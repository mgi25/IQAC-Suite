from django.db import migrations

def migrate_role_strings_to_fk(apps, schema_editor):
    RoleAssignment = apps.get_model('core', 'RoleAssignment')
    OrganizationRole = apps.get_model('core', 'OrganizationRole')

    for ra in RoleAssignment.objects.all():
        # If you previously had a string role, try to match it to an OrganizationRole by name/org
        # Here, I'm using ra.role as a string (should match the old CharField value)
        if getattr(ra, "role", None) and ra.organization_id:
            org_role = OrganizationRole.objects.filter(
                name=ra.role, organization_id=ra.organization_id
            ).first()
            if org_role:
                ra.role_id = org_role.id
                ra.save()
            # Optionally: create missing roles if not found, or log a warning

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_alter_roleassignment_role'),
    ]

    operations = [
        migrations.RunPython(migrate_role_strings_to_fk, migrations.RunPython.noop),
    ]
