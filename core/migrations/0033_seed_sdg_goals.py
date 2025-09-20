from django.db import migrations

from core.models import SDG_GOALS


def seed_sdg_goals(apps, schema_editor):
    SDGGoal = apps.get_model("core", "SDGGoal")
    for name in SDG_GOALS:
        SDGGoal.objects.get_or_create(name=name)
    SDGGoal.objects.exclude(name__in=SDG_GOALS).delete()


def reverse_seed(apps, schema_editor):
    SDGGoal = apps.get_model("core", "SDGGoal")
    SDGGoal.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0032_popsochangenotification_popsoassignment"),
    ]

    operations = [
        migrations.RunPython(seed_sdg_goals, reverse_seed),
    ]
