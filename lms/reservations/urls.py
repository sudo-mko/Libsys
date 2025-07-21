from django.urls import path
from . import views

app_name = 'reservations'

urlpatterns = [
    path('', views.reservation_list, name='reservation_list'),
    path('reserve/<int:book_id>/', views.reserve_book, name='reserve_book'),
    path('approve-confirm/<int:reservation_id>/', views.approve_reservation_confirm, name='approve_reservation_confirm'),
    path('approve/<int:reservation_id>/', views.approve_reservation, name='approve_reservation'),
    path('reject-confirm/<int:reservation_id>/', views.reject_reservation_confirm, name='reject_reservation_confirm'),
    path('reject/<int:reservation_id>/', views.reject_reservation, name='reject_reservation'),
    path('expire-confirm/<int:reservation_id>/', views.expire_reservation_confirm, name='expire_reservation_confirm'),
    path('expire/<int:reservation_id>/', views.mark_expired, name='mark_expired'),
    path('my-reservations/', views.user_reservations, name='user_reservations'),
    path('cancel/<int:reservation_id>/', views.cancel_reservation, name='cancel_reservation'),
]


