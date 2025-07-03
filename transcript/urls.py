from django.urls import path
from . import views

app_name = "transcript"

urlpatterns = [
    path('', views.home, name='home'),  # form page
    
    # ✅ New: AJAX endpoint to validate roll number
    path('validate-roll/', views.validate_roll_no, name='validate_roll'),

    path('view/<str:roll_no>/', views.transcript_view, name='transcript'),  # view transcript
    path('pdf/<str:roll_no>/', views.transcript_pdf, name='transcript_pdf'),  # generate PDF
    path('events/<str:roll_no>/', views.all_events_view, name='all_events'),  # view all events
]
