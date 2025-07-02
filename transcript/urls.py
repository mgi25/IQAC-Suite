from django.urls import path
from . import views

app_name = "transcript"

urlpatterns = [
    path('', views.home, name='home'),  # form page
    path('view/<str:roll_no>/', views.transcript_view, name='transcript'),  # ✅ fixed to accept roll_no
    path('pdf/<str:roll_no>/', views.transcript_pdf, name='transcript_pdf'),
    path('events/<str:roll_no>/', views.all_events_view, name='all_events'),
]
