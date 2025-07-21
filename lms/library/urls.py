from django.urls import path
from . import views

app_name = 'library'

urlpatterns = [
    path('', views.index, name='home'),
    path('book/<int:book_id>/', views.book_detail, name='book_detail'),
    path('book/add/', views.book_add, name='book_add'),
    path('book/<int:book_id>/update/', views.book_update, name='book_update'),
    path('book/<int:book_id>/delete/', views.book_delete, name='book_delete'),
]





