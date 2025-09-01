#!/usr/bin/env bash
set -e
python manage.py findstatic emt/css/styles.css || true
python manage.py collectstatic --noinput
python - <<'PY'
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "iqac_project.settings")
django.setup()
from django.conf import settings
print("STATIC_URL:", settings.STATIC_URL)
print("STATIC_ROOT exists:", (settings.BASE_DIR / "staticfiles").exists())
PY
