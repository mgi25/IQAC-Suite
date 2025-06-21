from django.contrib import admin
from django.urls import path, include
import core.views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),  # core: dashboard, login, etc.
    path('accounts/', include('allauth.urls')),  # login/logout
    path('suite/', include(('emt.urls', 'emt'), namespace='emt')),  # emt app
    path('transcript/', include(('transcript.urls', 'transcript'), namespace='transcript')),  # transcript
]
