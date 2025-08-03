# core/urls.py

from django.urls import path
from . import views
from core.views import custom_logout

urlpatterns = [
    # ────────────────────────────────────────────────
    # Authentication
    # ────────────────────────────────────────────────
    path('login/',  views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('accounts/logout/', custom_logout, name='account_logout'),

    # ────────────────────────────────────────────────
    # General Dashboard and Proposal Views
    # ────────────────────────────────────────────────
    path('', views.dashboard, name='dashboard'),
    path('cdl/', views.cdl_dashboard, name='cdl_dashboard'),
    path('propose-event/', views.propose_event, name='propose_event'),
    path('proposal-status/<int:pk>/', views.proposal_status, name='proposal_status'),

    # ────────────────────────────────────────────────
    # Admin - User Management
    # ────────────────────────────────────────────────
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('user-management/', views.admin_user_panel, name='admin_user_panel'),
    path('users/', views.admin_user_management, name='admin_user_management'),
    path('users/<int:user_id>/edit/', views.admin_user_edit, name='admin_user_edit'),

    # ────────────────────────────────────────────────
    # Admin - Role Management
    # ────────────────────────────────────────────────
    path('user-roles/', views.admin_role_management, name='admin_role_management'),
    path('user-roles/<int:organization_id>/', views.admin_role_management, name='admin_role_management_org'),
    path('user-roles/<int:organization_id>/add/', views.add_org_role, name='add_org_role'),
    path('user-roles/add/', views.add_role, name='add_role'),
    path('user-roles/role/<int:role_id>/update/', views.update_org_role, name='update_org_role'),
    path('user-roles/role/<int:role_id>/toggle/', views.toggle_org_role, name='toggle_org_role'),
    path('user-roles/role/<int:role_id>/delete/', views.delete_org_role, name='delete_org_role'),

    # ────────────────────────────────────────────────
    # Admin - Event Proposals
    # ────────────────────────────────────────────────
    path('event-proposals/', views.admin_event_proposals, name='admin_event_proposals'),
    path('event-proposal/<int:proposal_id>/json/', views.event_proposal_json, name='event_proposal_json'),
    path('event-proposal/<int:proposal_id>/action/', views.event_proposal_action, name='event_proposal_action'),
    path('proposal/<int:proposal_id>/detail/', views.admin_proposal_detail, name='admin_proposal_detail'),
    path('core-admin/proposal/<int:proposal_id>/detail/', views.admin_proposal_detail, name='admin_proposal_detail'),

    # ────────────────────────────────────────────────
    # Admin - Reports
    # ────────────────────────────────────────────────
    path('reports/', views.admin_reports_view, name='admin_reports'),
    path('reports/<int:report_id>/approve/', views.admin_reports_approve, name='admin_reports_approve'),
    path('reports/<int:report_id>/reject/', views.admin_reports_reject, name='admin_reports_reject'),

    # ────────────────────────────────────────────────
    # Admin - Master Data & Settings
    # ────────────────────────────────────────────────
    path('core-admin/dashboard/', views.admin_dashboard, name='core_admin_dashboard'),
    path('core-admin/master-data/', views.admin_master_data, name='admin_master_data'),
    path('core-admin/master-data-dashboard/', views.master_data_dashboard, name='master_data_dashboard'),
    path('core-admin/settings/', views.admin_settings_dashboard, name='admin_settings'),
    path('core-admin/settings/<str:model_name>/add/', views.admin_master_data_add, name='admin_settings_add'),
    path('core-admin/settings/<str:model_name>/<int:pk>/edit/', views.admin_master_data_edit, name='admin_settings_edit'),
    path('core-admin/settings/<str:model_name>/<int:pk>/delete/', views.admin_master_data_delete, name='admin_settings_delete'),

    # ────────────────────────────────────────────────
    # Admin - Approval Flow Management
    # ────────────────────────────────────────────────
    path('core-admin/approval-flow/', views.admin_approval_flow, name='admin_approval_flow'),
    path('core-admin/approval-flow/<int:org_id>/', views.admin_approval_flow_manage, name='admin_approval_flow_manage'),
    path('core-admin/approval-flow/<int:org_id>/get/', views.get_approval_flow, name='get_approval_flow'),
    path('core-admin/approval-flow/<int:org_id>/save/', views.save_approval_flow, name='save_approval_flow'),
    path('core-admin/approval-flow/<int:org_id>/delete/', views.delete_approval_flow, name='delete_approval_flow'),

    # ────────────────────────────────────────────────
    # Admin - Approval Dashboard & Visibility
    # ────────────────────────────────────────────────
    path('core-admin/approval/', views.admin_approval_dashboard, name='admin_approval_dashboard'),
    path('core-admin/approval-box-visibility/', views.approval_box_visibility_orgs, name='approval_box_visibility_orgs'),
    path('core-admin/approval-box-visibility/<int:org_id>/', views.approval_box_visibility_roles, name='approval_box_roles'),
    path('core-admin/approval-box-visibility/<int:org_id>/role/<int:role_id>/users/', views.approval_box_visibility_users, name='approval_box_users'),
    path('core-admin/approval-box-visibility/role/<int:role_id>/toggle/', views.toggle_role_visibility, name='toggle_role_visibility'),
    path('core-admin/approval-box-visibility/user/<int:user_id>/<int:role_id>/toggle/', views.toggle_user_visibility, name='toggle_user_visibility'),

    # ────────────────────────────────────────────────
    # Admin - PSO/PO Management
    # ────────────────────────────────────────────────
    path('core-admin/pso-po/', views.admin_pso_po_management, name='admin_pso_po_management'),
    path('core-admin/pso-po/data/<str:org_type>/<int:org_id>/', views.get_pso_po_data, name='get_pso_po_data'),
    path('core-admin/pso-po/add/<str:outcome_type>/', views.add_outcome, name='add_outcome'),
    path('core-admin/pso-po/delete/<str:outcome_type>/<int:outcome_id>/', views.delete_outcome, name='delete_outcome'),

    # ────────────────────────────────────────────────
    # AJAX - Academic Year
    # ────────────────────────────────────────────────
    path('core-admin/set-academic-year/', views.set_academic_year, name='set_academic_year'),
    path('core-admin/add-academic-year/', views.add_academic_year, name='add_academic_year'),

    # ────────────────────────────────────────────────
    # APIs
    # ────────────────────────────────────────────────
    path('api/auth/me', views.api_auth_me, name='api_auth_me'),
    path('api/faculty/overview', views.api_faculty_overview, name='api_faculty_overview'),
    path('api/approval-flow/<int:org_id>/', views.api_approval_flow_steps, name='api_approval_flow_steps'),
    path('api/search-users/', views.search_users, name='search_users'),
    path('api/org-users/<int:org_id>/', views.organization_users, name='organization_users'),
    path('api/org-type/<int:org_type_id>/organizations/', views.api_org_type_organizations, name='api_org_type_organizations'),
    path('api/org-type/<int:org_type_id>/roles/', views.api_org_type_roles, name='api_org_type_roles'),
    path('api/organization/<int:org_id>/roles/', views.api_organization_roles, name='api_organization_roles'),
    path('api/search/', views.api_global_search, name='api_global_search'),

    # ────────────────────────────────────────────────
    # Optional: User Dashboard (if not admin)
    # ────────────────────────────────────────────────
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
]
