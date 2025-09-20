import logging

from django.conf import settings
from django.contrib.sites.models import Site

logger = logging.getLogger(__name__)


def get_or_create_current_site(request):
    """Return the current Site, creating it from the request host if missing."""
    try:
        return Site.objects.get_current(request)
    except Site.DoesNotExist:
        host = request.get_host()
        site_id = getattr(settings, "SITE_ID", 1)
        site, created = Site.objects.get_or_create(
            id=site_id,
            defaults={"domain": host, "name": host},
        )
        if created:
            logger.info("Created missing Site %s with id %s", host, site_id)
        return site
