from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('login/',  views.login_view,  name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Home/Dashboard
    path('',            views.dashboard,       name='dashboard'),
    path('dashboard/',  views.admin_dashboard, name='admin_dashboard'),

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
    # path('admin/users/', views.admin_user_panel, name='admin_user_panel'),
]
