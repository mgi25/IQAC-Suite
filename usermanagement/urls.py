from django.urls import path

from . import views

app_name = "usermanagement"

urlpatterns = [
    path("join-requests/", views.join_requests, name="join_requests"),
]
