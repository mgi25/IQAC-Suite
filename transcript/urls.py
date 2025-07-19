from django.urls import path
from . import views

app_name = 'transcript'

urlpatterns = [
    path('', views.home, name='home'),  # Home page
    path('validate-roll/', views.validate_roll_no, name='validate_roll'),  # AJAX validation
    path('<str:roll_no>/', views.transcript_view, name='transcript'),  # View transcript
    path('<str:roll_no>/pdf/', views.transcript_pdf, name='transcript_pdf'),  # Individual PDF download ✅
    path('<str:roll_no>/events/', views.all_events_view, name='all_events'),  # Events per student
    path('download/', views.bulk_download_handler, name='bulk_download'),  # Bulk via POST
    path('pdf/all/', views.bulk_download_handler, name='bulk_download'),  # Bulk via GET/POST alias ✅
]
