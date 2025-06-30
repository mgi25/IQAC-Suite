from django.urls import path
from . import views

urlpatterns = [
    path('login/',         views.login_view,     name='login'),
    path('logout/',        views.logout_view,    name='logout'),
    path('',               views.dashboard,      name='dashboard'),
    path('propose-event/', views.propose_event,  name='propose_event'),
    path('proposal-status/<int:pk>/', views.proposal_status, name='proposal_status'),
    path('proposal-status/<int:proposal_id>/', views.proposal_status, name='proposal_status'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('users/', views.admin_user_panel, name='admin_user_panel'), 
    path('core-admin/users/', views.admin_user_management, name='admin_user_management'), 
    path('core-admin/users/<int:user_id>/edit/', views.admin_user_edit, name='admin_user_edit'),
    #path('admin/users/', views.admin_user_panel, name='admin_user_panel'),
]
