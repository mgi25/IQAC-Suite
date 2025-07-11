from django.urls import path
from . import views

app_name = 'emt'

urlpatterns = [
    path('suite/', views.suite_dashboard, name='iqac_suite_dashboard'),

    # NEW: Allow /submit/ and /submit/<int:pk>/ for new and existing proposals (draft)
    path('submit/', views.submit_proposal, name='submit_proposal'),
    path('submit/<int:pk>/', views.submit_proposal, name='submit_proposal_with_pk'),  # <---- Add this!
    path('cdl/submit/', views.submit_request_view, name='cdl_submit'),
    path('need-analysis/<int:proposal_id>/', views.submit_need_analysis, name='submit_need_analysis'),
    path('objectives/<int:proposal_id>/', views.submit_objectives, name='submit_objectives'),
    path('expected-outcomes/<int:proposal_id>/', views.submit_expected_outcomes, name='submit_expected_outcomes'),
    path('tentative-flow/<int:proposal_id>/', views.submit_tentative_flow, name='submit_tentative_flow'),
    path('speaker-profile/<int:proposal_id>/', views.submit_speaker_profile, name='submit_speaker_profile'),
    path('expense-details/<int:proposal_id>/', views.submit_expense_details, name='submit_expense_details'),
    path('proposal-status/<int:proposal_id>/', views.proposal_status_detail, name='proposal_status_detail'),
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
    path('api/departments/', views.api_departments, name='api_departments'),
    path("api/associations/", views.api_associations, name="api_associations"),
    path("api/clubs/", views.api_clubs, name="api_clubs"),
    path("api/centers/", views.api_centers, name="api_centers"),
    path("api/cells/", views.api_cells, name="api_cells"),
    path("api/faculty/", views.api_faculty, name="api_faculty"),
    path("suite/my-approvals/", views.my_approvals, name="my_approvals"),
    path("suite/review-approval/<int:step_id>/", views.review_approval_step, name="review_approval_step"),
    path('cdl/my-requests/', views.my_requests_view, name='cdl_my_requests'),
    path('report/submit/<int:proposal_id>/', views.submit_event_report, name='submit_event_report'),
]
