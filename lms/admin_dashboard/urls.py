from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.admin_dashboard, name='dashboard'),
    path('users/', views.manage_users, name='manage_users'),
    path('users/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('users/delete/<int:user_id>/', views.delete_user, name='delete_user'),
    path('settings/', views.system_settings, name='system_settings'),
    path('settings/delete/<int:setting_id>/', views.delete_setting, name='delete_setting'),
    path('audit-logs/', views.audit_logs, name='audit_logs'),
    path('change-password/', views.change_password, name='change_password'),
    path('sessions/', views.session_management, name='session_management'),
    
    # Reports URLs
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/users/', views.user_statistics_report, name='user_statistics_report'),
    path('reports/security/', views.security_report, name='security_report'),
    path('reports/activity/', views.activity_report, name='activity_report'),
    path('reports/library/', views.library_operations_report, name='library_operations_report'),
    path('reports/export/', views.export_report, name='export_report'),
]