from django.urls import path
from . import views

app_name = 'borrow'

urlpatterns = [
    path('', views.borrow_list, name='borrow_list'),
    path('borrow/<int:book_id>/', views.borrow_book, name='borrow_book'),
    path('history/', views.borrowing_history, name='borrowing_history'),
    path('request-extension/<int:borrowing_id>/', views.request_extension, name='request_extension'),
    path('extension-requests/', views.extension_requests_list, name='extension_requests_list'),
    path('approve-extension-confirm/<int:extension_id>/', views.approve_extension_confirm, name='approve_extension_confirm'),
    path('approve-extension/<int:extension_id>/', views.approve_extension, name='approve_extension'),
    path('reject-extension/<int:extension_id>/', views.reject_extension, name='reject_extension'),
    
    # New borrowing workflow URLs
    path('pending-requests/', views.pending_requests_list, name='pending_requests_list'),
    path('approve-request/<int:borrowing_id>/', views.approve_borrowing_request, name='approve_borrowing_request'),
    path('reject-request/<int:borrowing_id>/', views.reject_borrowing_request, name='reject_borrowing_request'),
    path('pickup-code-entry/', views.pickup_code_entry, name='pickup_code_entry'),
    path('cancel-request/<int:borrowing_id>/', views.cancel_borrowing_request, name='cancel_borrowing_request'),
]


