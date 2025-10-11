# Generated manually to deduplicate organization roles and enforce case-insensitive uniqueness.

from django.db import migrations, models
from django.db.models.functions import Lower


def dedupe_org_roles(apps, schema_editor):
    OrganizationRole = apps.get_model("core", "OrganizationRole")
    RoleAssignment = apps.get_model("core", "RoleAssignment")

    # Use the historical "all_objects" manager if available; fallback to default manager otherwise.
    try:
        role_qs = OrganizationRole.all_objects.all()
    except AttributeError:
        role_qs = OrganizationRole.objects.all()

    grouped = {}
    for role in role_qs.order_by("organization_id", "id"):
        name_normalized = (role.name or "").strip()
        if not name_normalized:
            continue
        key = (role.organization_id, name_normalized.lower())
        grouped.setdefault(key, []).append(role)

    for (_org_id, _name_lc), roles in grouped.items():
        if len(roles) < 2:
            # Nothing to merge.
            continue

        # Choose a canonical role: prefer active status, then lowest id.
        roles.sort(key=lambda r: (getattr(r, "status", "active") != "active", r.id))
        canonical = roles[0]
        canonical_name = (canonical.name or "").strip()

        if canonical.name != canonical_name:
            canonical.name = canonical_name
            canonical.save(update_fields=["name"])

        for duplicate in roles[1:]:
            RoleAssignment.objects.filter(role_id=duplicate.id).update(role_id=canonical.id)
            duplicate.delete()


def noop(apps, schema_editor):
    # No reverse action; duplicates will already have been merged.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0048_remove_cdlrequest_certificate_design_link_and_more"),
    ]

    atomic = False

    operations = [
        migrations.RunPython(dedupe_org_roles, noop),
        migrations.AddConstraint(
            model_name="organizationrole",
            constraint=models.UniqueConstraint(
                Lower("name"),
                "organization",
                name="core_orgrole_name_ci_unique",
            ),
        ),
    ]
