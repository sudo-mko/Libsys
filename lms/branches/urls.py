from django.urls import path
from . import views

app_name = 'branches'

urlpatterns = [
    path('manage_branches/', views.manage_branches, name='manage_branches'),
    path('create/', views.create_branch, name='create_branch'),
    path('edit/<int:branch_id>/', views.edit_branch, name='edit_branch'),
    path('delete/<int:branch_id>/', views.delete_branch, name='delete_branch'),
    path('sections/', views.manage_sections, name='manage_sections'),
    path('sections/create/', views.create_section, name='create_section'),
    path('sections/edit/<int:section_id>/', views.edit_section, name='edit_section'),
    path('sections/delete/<int:section_id>/', views.delete_section, name='delete_section'),
] 