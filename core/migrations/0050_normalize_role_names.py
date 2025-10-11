from django.db import migrations


def normalize_role_names(apps, schema_editor):
    OrganizationRole = apps.get_model("core", "OrganizationRole")
    try:
        role_qs = OrganizationRole.all_objects.all()
    except AttributeError:
        role_qs = OrganizationRole.objects.all()

    for role in role_qs.iterator():
        name = (role.name or "").strip()
        if not name:
            continue
        normalized = name[0].upper() + name[1:]
        if role.name != normalized:
            role.name = normalized
            role.save(update_fields=["name"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0049_enforce_orgrole_case_insensitive_unique"),
    ]

    operations = [
        migrations.RunPython(normalize_role_names, noop),
    ]
