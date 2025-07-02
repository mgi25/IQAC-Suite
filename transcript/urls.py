from django.urls import path
from . import views

app_name = "transcript"

urlpatterns = [
    path('', views.home, name='home'),  # form page
    path('view/', views.transcript_view, name='transcript'),  # display page
    path('pdf/<str:roll_no>/', views.transcript_pdf, name='transcript_pdf'),  # for download
    path('events/<str:roll_no>/', views.all_events_view, name='all_events'),  # qr event list
]
