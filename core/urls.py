from django.urls import path
from . import views
from core import views as core_views
from core.views import custom_logout
from . import views_admin_org_users as orgu

urlpatterns = [
    # ────────────────────────────────────────────────
    # Authentication
    # ────────────────────────────────────────────────
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('accounts/logout/', custom_logout, name='account_logout'),
    path('register/', views.registration_form, name='registration_form'),

    # ────────────────────────────────────────────────
    # General Dashboard and Proposal Views
    # ────────────────────────────────────────────────
    path('', views.dashboard, name='dashboard'),
    path('cdl/', views.cdl_dashboard, name='cdl_dashboard'),
    path('propose-event/', views.propose_event, name='propose_event'),
    path('proposal-status/<int:pk>/', views.proposal_status, name='proposal_status'),
    path('proposal/<int:proposal_id>/detail/', views.proposal_detail, name='proposal_detail'),
    path('user-dashboard/', views.user_dashboard, name='user_dashboard'),
    path('event/<int:proposal_id>/details/', views.student_event_details, name='student_event_details'),
    # Calendar APIs
    path('api/calendar/', views.api_calendar_events, name='api_calendar_events'),
    path('api/calendar/faculty/create/', views.api_create_faculty_meeting, name='api_create_faculty_meeting'),
    
    # Dashboard Enhancement APIs
    path('api/dashboard/places/', views.api_dashboard_places, name='api_dashboard_places'),
    path('api/dashboard/people/', views.api_dashboard_people, name='api_dashboard_people'),
    path('api/user/proposals/', views.api_user_proposals, name='api_user_proposals'),
    path('api/student/performance-data/', views.api_student_performance_data, name='api_student_performance_data'),
    path('api/student/contributions/', views.api_student_contributions, name='api_student_contributions'),
    path('api/user/events-data/', views.api_user_events_data, name='api_user_events_data'),

    # ────────────────────────────────────────────────
    # Admin - User Management
    # ────────────────────────────────────────────────
    path('core-admin/user-management/', views.admin_user_panel, name='admin_user_panel'),
    path('core-admin/users/', views.admin_user_management, name='admin_user_management'),
    path('core-admin/users/<int:user_id>/edit/', views.admin_user_edit, name='admin_user_edit'),
    path('core-admin/users/<int:user_id>/deactivate/', views.admin_user_deactivate, name='admin_user_deactivate'),
    path('core-admin/users/<int:user_id>/activate/', views.admin_user_activate, name='admin_user_activate'),
    path('core-admin/users/<int:user_id>/impersonate/', views.admin_impersonate_user, name='admin_impersonate_user'),
    path('core-admin/stop-impersonation/', views.stop_impersonation, name='stop_impersonation'),

    # ────────────────────────────────────────────────
    # Admin - Role Management
    # ────────────────────────────────────────────────
    path('core-admin/user-roles/', views.admin_role_management, name='admin_role_management'),
    path('core-admin/user-roles/<int:organization_id>/', views.admin_role_management, name='admin_role_management_org'),
    path('core-admin/user-roles/<int:organization_id>/add/', views.add_org_role, name='add_org_role'),
    path('core-admin/user-roles/add/', views.add_role, name='add_role'),
    path('core-admin/user-roles/role/<int:role_id>/update/', views.update_org_role, name='update_org_role'),
    path('core-admin/user-roles/role/<int:role_id>/toggle/', views.toggle_org_role, name='toggle_org_role'),
    path('core-admin/user-roles/role/<int:role_id>/delete/', views.delete_org_role, name='delete_org_role'),

    # ────────────────────────────────────────────────
    # Admin - Event Proposals
    # ────────────────────────────────────────────────
    path('core-admin/event-proposals/', views.admin_event_proposals, name='admin_event_proposals'),
    path('core-admin/event-proposal/<int:proposal_id>/json/', views.event_proposal_json, name='event_proposal_json'),
    path('core-admin/event-proposal/<int:proposal_id>/action/', views.event_proposal_action, name='event_proposal_action'),
    path('core-admin/proposal/<int:proposal_id>/detail/', views.admin_proposal_detail, name='admin_proposal_detail'),

    # ────────────────────────────────────────────────
    # Admin - Reports
    # ────────────────────────────────────────────────
    path('core-admin/reports/', views.admin_reports_view, name='admin_reports'),
    path('core-admin/reports/<int:report_id>/approve/', views.admin_reports_approve, name='admin_reports_approve'),
    path('core-admin/reports/<int:report_id>/reject/', views.admin_reports_reject, name='admin_reports_reject'),

    # ────────────────────────────────────────────
    # Admin - History
    # ────────────────────────────────────────────
    path('core-admin/history/', views.admin_history, name='admin_history'),
    path('core-admin/history/<int:pk>/', views.admin_history_detail, name='admin_history_detail'),

    # ────────────────────────────────────────────────
    # Admin - Master Data & Settings
    # ────────────────────────────────────────────────
    path('core-admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('core-admin/master-data/', views.admin_master_data, name='admin_master_data'),
    path('core-admin/master-data-dashboard/', views.master_data_dashboard, name='master_data_dashboard'),
    path('core-admin/settings/', views.admin_settings_dashboard, name='admin_settings'),
    path('core-admin/settings/<str:model_name>/add/', views.admin_master_data_add, name='admin_settings_add'),
    path('core-admin/settings/<str:model_name>/<int:pk>/edit/', views.admin_master_data_edit, name='admin_settings_edit'),
    path('core-admin/settings/<str:model_name>/<int:pk>/delete/', views.admin_master_data_delete, name='admin_settings_delete'),
    path('core-admin/academic-years/', views.admin_academic_year_settings, name='admin_academic_year_settings'),
    path('core-admin/academic-years/<int:pk>/archive/', views.academic_year_archive, name='academic_year_archive'),
    path('core-admin/academic-years/<int:pk>/restore/', views.academic_year_restore, name='academic_year_restore'),

    # ────────────────────────────────────────────────
    # Admin - Approval Flow Management
    # ────────────────────────────────────────────────
    path('core-admin/approval-flow/', views.admin_approval_flow, name='admin_approval_flow'),
    path('core-admin/approval-flow/<int:org_id>/', views.admin_approval_flow_manage, name='admin_approval_flow_manage'),
    path('core-admin/approval-flow/<int:org_id>/get/', views.get_approval_flow, name='get_approval_flow'),
    path('core-admin/approval-flow/<int:org_id>/save/', views.save_approval_flow, name='save_approval_flow'),
    path('core-admin/approval-flow/<int:org_id>/delete/', views.delete_approval_flow, name='delete_approval_flow'),

    # ────────────────────────────────────────────────
    # Admin - Approval Dashboard
    # ────────────────────────────────────────────────
    path('core-admin/approval/', views.admin_approval_dashboard, name='admin_approval_dashboard'),

    # ────────────────────────────────────────────────
    # Admin - PSO/PO Management
    # ────────────────────────────────────────────────
    #path('core-admin/outcomes/', views.admin_outcome_dashboard, name='admin_outcome_dashboard'),
    path('core-admin/pso-po/', views.admin_pso_po_management, name='admin_pso_po_management'),
    #path('core-admin/sdg-goals/', views.admin_sdg_management, name='admin_sdg_management'),
    path('core-admin/pso-po/data/<str:org_type>/<int:org_id>/', views.get_pso_po_data, name='get_pso_po_data'),
    path('core-admin/pso-po/add/<str:outcome_type>/', views.add_outcome, name='add_outcome'),
    path('core-admin/pso-po/delete/<str:outcome_type>/<int:outcome_id>/', views.delete_outcome, name='delete_outcome'),

    # ────────────────────────────────────────────────
    # Admin - Organization User Management
    # ────────────────────────────────────────────────
    path("core-admin/org-users/", orgu.entrypoint, name="admin_org_users_entry"),
    path(
        "core-admin/org-users/<int:org_id>/",
        orgu.select_role,
        name="admin_org_users_select_role",
    ),
    path(
        "core-admin/org-users/<int:org_id>/students/",
        orgu.student_flow,
        name="admin_org_users_students",
    ),
    path(
        "core-admin/org-users/<int:org_id>/faculty/",
        orgu.faculty_flow,
        name="admin_org_users_faculty",
    ),
    path(
        "core-admin/org-users/<int:org_id>/faculty/<int:member_id>/",
        orgu.faculty_detail,
        name="admin_org_users_faculty_detail",
    ),
    path(
        "core-admin/org-users/<int:org_id>/faculty/<int:member_id>/toggle/",
        orgu.faculty_toggle_active,
        name="admin_org_users_faculty_toggle",
    ),
    path(
        "core-admin/org-users/<int:org_id>/create-class/",
        orgu.create_class,
        name="admin_org_create_class",
    ),
    path(
        "core-admin/org-users/<int:org_id>/upload-csv/",
        orgu.upload_csv,
        name="admin_org_users_upload_csv",
    ),
    path(
        "core-admin/org-users/<int:org_id>/class/<int:class_id>/",
        orgu.class_detail,
        name="admin_org_users_class_detail",
    ),
    path(
        "core-admin/org-users/<int:org_id>/class/<int:class_id>/remove/<int:student_id>/",
        orgu.class_remove_student,
        name="admin_org_users_class_remove_student",
    ),
    path(
        "core-admin/org-users/<int:org_id>/class/<int:class_id>/toggle/",
        orgu.class_toggle_active,
        name="admin_org_users_class_toggle",
    ),
    path(
        "core-admin/org-users/<int:org_id>/csv-template/",
        orgu.csv_template,
        name="admin_org_users_csv_template",
    ),
    path(
        "core-admin/org-users/fetch/children/<int:org_id>/",
        orgu.fetch_children,
        name="admin_org_fetch_children",
    ),
    path(
        "core-admin/org-users/fetch/by-type/<int:type_id>/",
        orgu.fetch_by_type,
        name="admin_org_fetch_by_type",
    ),
    path(
        "core-admin/org-users/<int:org_id>/classes/",
        core_views.class_rosters,
        name="class_rosters",
    ),
    path(
        "core-admin/org-users/<int:org_id>/classes/<str:class_name>/",
        core_views.class_roster_detail,
        name="class_roster_detail",
    ),

    # ────────────────────────────────────────────────
    # Core APIs (Admin Dashboard)
    # ────────────────────────────────────────────────
    path('core-admin/api/auth/me', views.api_auth_me, name='api_auth_me'),
    path('core-admin/api/faculty/overview', views.api_faculty_overview, name='api_faculty_overview'),
    path('core-admin/api/approval-flow/<int:org_id>/', views.api_approval_flow_steps, name='api_approval_flow_steps'),
    path('core-admin/api/org-users/<int:org_id>/', views.organization_users, name='organization_users'),
    path('core-admin/api/org-type/<int:org_type_id>/organizations/', views.api_org_type_organizations, name='api_org_type_organizations'),
    path('core-admin/api/org-type/<int:org_type_id>/roles/', views.api_org_type_roles, name='api_org_type_roles'),
    path('core-admin/api/organization/<int:org_id>/roles/', views.api_organization_roles, name='api_organization_roles'),
    path('core-admin/api/search-users/', views.search_users, name='search_users'),
    path('core-admin/api/search/', views.api_global_search, name='api_global_search'),

    # Misc APIs used by dashboards
    path('api/event-contribution-data', views.event_contribution_data, name='event_contribution_data'),
    
    # Multi-select filter APIs
    #path('core-admin/api/filter/organizations/', views.api_filter_organizations, name='api_filter_organizations'),
    path('core-admin/api/filter/roles/', views.api_filter_roles, name='api_filter_roles'),
    path('core-admin/api/search/org-types/', views.api_search_org_types, name='api_search_org_types'),

    # PSO & PO Management APIs
    path('core/api/programs/<int:org_id>/', views.api_organization_programs, name='api_organization_programs'),
    path('core/api/create-program/', views.create_program_for_organization, name='create_program_for_organization'),
    path('core/api/program-outcomes/<int:program_id>/', views.api_program_outcomes, name='api_program_outcomes'),
    path('core/api/manage-program-outcomes/', views.manage_program_outcomes, name='manage_program_outcomes'),
    
    # PO/PSO Assignment Management APIs
    path('core/api/faculty-users/<int:org_id>/', views.api_available_faculty_users, name='api_available_faculty_users'),
    path('core/api/debug-org-users/<int:org_id>/', views.api_debug_org_users, name='api_debug_org_users'),
    path('core/api/popso-assignments/', views.api_popso_assignments, name='api_popso_assignments'),
    path('core/api/popso-assignments/<int:org_id>/', views.api_popso_assignments, name='api_popso_assignments_org'),
    path('core/api/log-popso-change/', views.api_log_popso_change, name='api_log_popso_change'),
    path('core/api/popso-manager-status/', views.api_popso_manager_status, name='api_popso_manager_status'),

    # ────────────────────────────────────────────────
    # Admin Dashboard API
    # ────────────────────────────────────────────────
    path('admin-dashboard-api/', views.admin_dashboard_api, name='admin_dashboard_api'),


    # ────────────────────────────────────────────────

    # ────────────────────────────────────────────────
    # General APIs (Public/Non-Admin)
    # ────────────────────────────────────────────────
    path('api/organizations/', views.api_organizations, name='api_organizations'),
    path('api/roles/', views.api_roles, name='api_roles'),
    path('api/event-contribution/', views.event_contribution_data, name='event_contribution_data'),
    path('api/auth/me', views.api_auth_me, name='frontend_api_auth_me'),
    path('api/faculty/overview', views.api_faculty_overview, name='frontend_api_faculty_overview'),
    path('api/faculty/events', views.api_faculty_events, name='api_faculty_events'),
    path('api/faculty/students', views.api_faculty_students, name='api_faculty_students'),
    path('api/student/overview', views.api_student_overview, name='api_student_overview'),
    path('api/student/events', views.api_student_events, name='api_student_events'),
    path('api/student/achievements', views.api_student_achievements, name='api_student_achievements'),
    
    
    
    
    
    # Data Export URLs
    path('data-export-filter/', views.data_export_filter_view, name='data_export_filter'),
    path('api/filter-suggestions/', views.filter_suggestions_api, name='filter_suggestions_api'),
    path('api/execute-filter/', views.execute_filter_api, name='execute_filter_api'),
    path('api/export-data/csv/', views.export_data_csv, name='export_data_csv'),
    path('api/export-data/excel/', views.export_data_excel, name='export_data_excel'),
    path('settings/pso-po-management/', views.settings_pso_po_management,name='settings_pso_po_management'),

     path('dashboard/', views.dashboard, name='dashboard'),

     path("cdl/head/", views.cdl_head_dashboard, name="cdl_head_dashboard"),
     path("cdl/work/", views.cdl_work_dashboard, name="cdl_work_dashboard"),
]
