from django.urls import path
from . import views

app_name = 'emt'

urlpatterns = [
    path('suite/', views.iqac_suite_dashboard, name='iqac_suite_dashboard'),

    # NEW: Allow /submit/ and /submit/<int:pk>/ for new and existing proposals (draft)
    path('submit/', views.submit_proposal, name='submit_proposal'),
    path('submit/<int:pk>/', views.submit_proposal, name='submit_proposal_with_pk'),  # <---- Add this!

    path('need-analysis/<int:proposal_id>/', views.submit_need_analysis, name='submit_need_analysis'),
    path('objectives/<int:proposal_id>/', views.submit_objectives, name='submit_objectives'),
    path('expected-outcomes/<int:proposal_id>/', views.submit_expected_outcomes, name='submit_expected_outcomes'),
    path('tentative-flow/<int:proposal_id>/', views.submit_tentative_flow, name='submit_tentative_flow'),
    path('speaker-profile/<int:proposal_id>/', views.submit_speaker_profile, name='submit_speaker_profile'),
    path('expense-details/<int:proposal_id>/', views.submit_expense_details, name='submit_expense_details'),
    path('proposal-status/<int:proposal_id>/', views.proposal_status, name='proposal_status'),
    path('autosave-proposal/', views.autosave_proposal, name='autosave_proposal'),
    # path('<int:proposal_id>/attendance/', views.attendance, name='attendance'),
    path('autosave-need-analysis/', views.autosave_need_analysis, name='autosave_need_analysis'),
    path('pending-reports/', views.pending_reports, name='pending_reports'),
    path('generate-report/<int:proposal_id>/', views.generate_report, name='generate_report'),
    path('report-success/<int:proposal_id>/', views.report_success, name='report_success'),
    path('download/pdf/<int:proposal_id>/', views.download_pdf, name='download_pdf'),
    path('download/word/<int:proposal_id>/', views.download_word, name='download_word'),
    path('generated-reports/', views.generated_reports, name='generated_reports'),
    path('view-report/<int:report_id>/', views.view_report, name='view_report'),
]
