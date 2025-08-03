from django.urls import path
from . import views

app_name = 'privacy'

urlpatterns = [
    path('policy/', views.privacy_policy, name='privacy_policy'),
    path('cookies/', views.cookie_policy, name='cookie_policy'),
    path('export-data/', views.export_data, name='export_data'),
    path('delete-account/', views.delete_account, name='delete_account'),
    path('consent/', views.update_consent, name='update_consent'),
    path('test/', views.test_gdpr, name='test_gdpr'),
    path('api/consent-status/', views.cookie_consent_status, name='cookie_consent_status'),
] 