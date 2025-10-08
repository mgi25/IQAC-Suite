from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),  # Built-in Django admin
    path("", include("core.urls")),  # core: dashboard, login, etc.
    path("accounts/", include("allauth.urls")),  # login/logout
    path("suite/", include(("emt.urls", "emt"), namespace="emt")),  # emt app
    # Legacy prefix to support older links that still reference '/emt/'
    path(
        "emt/", include(("emt.urls", "emt"), namespace="emt_legacy")
    ),  # backward compatibility
    path("transcript/", include("transcript.urls")),  # transcript module
]

# This block enables the Debug Toolbar and media file serving in development.
if settings.DEBUG:
    if getattr(settings, "USE_DEBUG_TOOLBAR", False):
        from importlib import import_module

        debug_toolbar = import_module("debug_toolbar")
        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns

    # This line enables media file serving (for student photos) in development.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
