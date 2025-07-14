from django.urls import path
from . import views
from core.views import custom_logout

urlpatterns = [
    # Authentication
    path('login/',  views.login_view,  name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Home/Dashboard
    path('',            views.dashboard,       name='dashboard'),
    path('dashboard/',  views.admin_dashboard, name='admin_dashboard'),

    # CDL Dashboard
    path('cdl/', views.cdl_dashboard, name='cdl_dashboard'),

    # Event Proposals
    path('propose-event/', views.propose_event, name='propose_event'),
    path('proposal-status/<int:pk>/', views.proposal_status, name='proposal_status'),

    # Admin Panel
    path('users/', views.admin_user_panel, name='admin_user_panel'), 
    path('core-admin/users/', views.admin_user_management, name='admin_user_management'), 
    path('core-admin/users/<int:user_id>/edit/', views.admin_user_edit, name='admin_user_edit'),
    path('core-admin/event-proposals/', views.admin_event_proposals, name='admin_event_proposals'),
    path('core-admin/event-proposal/<int:proposal_id>/json/', views.event_proposal_json, name='event_proposal_json'),
    path('core-admin/event-proposal/<int:proposal_id>/action/', views.event_proposal_action, name='event_proposal_action'),
    path('core-admin/reports/', views.admin_reports, name='admin_reports'),
    path('core-admin/reports/<int:report_id>/approve/', views.admin_reports_approve, name='admin_reports_approve'),
    path('core-admin/reports/<int:report_id>/reject/', views.admin_reports_reject, name='admin_reports_reject'),
    path('core-admin/dashboard/', views.admin_dashboard, name='core_admin_dashboard'),

    # path('admin/users/', views.admin_user_panel, name='admin_user_panel'),
    path('accounts/logout/', custom_logout, name='account_logout'),
    # urls.py
    path('core-admin/settings/', views.admin_settings_dashboard, name='admin_settings'),      # Dashboard (cards)
    path('core-admin/master-data/', views.admin_master_data, name='admin_master_data'),

    # For AJAX or form post requests (optional for delete/update with JS):
    path('core-admin/settings/<str:model_name>/add/', views.admin_master_data_add, name='admin_settings_add'),
    path('core-admin/settings/<str:model_name>/<int:pk>/edit/', views.admin_master_data_edit, name='admin_settings_edit'),
    path('core-admin/settings/<str:model_name>/<int:pk>/delete/', views.admin_master_data_delete, name='admin_settings_delete'),
    path('core-admin/proposal/<int:proposal_id>/detail/', views.admin_proposal_detail, name='admin_proposal_detail'),
    path('core-admin/approval-flow/', views.admin_approval_flow, name='admin_approval_flow'),

]
