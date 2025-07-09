# transcript/urls.py

from django.urls import path
from . import views

app_name = 'transcript'

urlpatterns = [
    path('', views.home, name='home'),
    path('validate-roll/', views.validate_roll_no, name='validate_roll'),
    path('<str:roll_no>/', views.transcript_view, name='transcript'),
    path('<str:roll_no>/pdf/', views.transcript_pdf, name='transcript_pdf'),
    path('<str:roll_no>/events/', views.all_events_view, name='all_events'),
    path('download/', views.bulk_download_handler, name='bulk_download'),
    path('pdf/all/', views.bulk_download_handler, name='bulk_download'),
]
