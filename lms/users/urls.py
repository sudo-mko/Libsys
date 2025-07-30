from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('membership/', views.membership_view, name='membership'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('user-list/', views.user_list, name='user_list'),
    path('create-user/', views.create_user, name='create_user'),
    path('edit-user/<int:user_id>/', views.edit_user, name='edit_user'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('manage-memberships/', views.manage_memberships, name='manage_memberships'),
    # path('unlock-accounts/', views.unlock_accounts, name='unlock_accounts'),
]