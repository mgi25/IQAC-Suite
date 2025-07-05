# transcript/urls.py
from django.urls import path
from . import views

app_name = "transcript"

urlpatterns = [
    path('', views.home, name='home'),
    path('validate-roll/', views.validate_roll_no, name='validate_roll'),
    path('view/<str:roll_no>/', views.transcript_view, name='transcript'),
    path('pdf/<str:roll_no>/', views.transcript_pdf, name='transcript_pdf'),
    path('events/<str:roll_no>/', views.all_events_view, name='all_events'),

    # 🔽 Top button: Single combined PDF for entire course
    path('download-pdfs/course/<str:roll_no>/', views.download_course_pdf_combined, name='download_course_pdfs'),

    # 🔽 Middle button: Zip of individual PDFs
    path('download-pdfs/course/zip/<str:roll_no>/', views.download_course_individual_pdfs, name='download_course_individual_pdfs'),
]
