# transcript/urls.py
from django.urls import path
from . import views

app_name = 'transcript'

urlpatterns = [
    path('', views.graduate_transcript, name='graduate_transcript'),
]
