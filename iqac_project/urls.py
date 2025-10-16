from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),  # Built-in Django admin
    path("", include("core.urls")),  # core: dashboard, login, etc.
    path("accounts/", include("allauth.urls")),  # login/logout
    path("suite/", include(("emt.urls", "emt"), namespace="emt")),  # emt app
    path(
        "emt/", include(("emt.urls", "emt"), namespace="emt_legacy")
    ),  # backward compatibility
    path("transcript/", include("transcript.urls")),  # transcript module
    path(
        "usermanagement/",
        include(("usermanagement.urls", "usermanagement"), namespace="usermanagement"),
    ),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
