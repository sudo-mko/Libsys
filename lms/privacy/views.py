from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import logout
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
import json

def privacy_policy(request):
    """Privacy Policy page"""
    return render(request, 'privacy/privacy_policy.html')

def cookie_policy(request):
    """Cookie Policy page"""
    return render(request, 'privacy/cookie_policy.html')

@login_required
def export_data(request):
    """Export user's personal data in JSON format"""
    user_data = {
        'username': request.user.username,
        'email': request.user.email,
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'phone_number': request.user.phone_number,
        'role': request.user.role,
        'created_at': request.user.created_at.isoformat() if request.user.created_at else None,
        'last_login': request.user.last_login.isoformat() if request.user.last_login else None,
        'is_active': request.user.is_active,
        'date_joined': request.user.date_joined.isoformat(),
    }
    
    # Add membership info if exists
    if hasattr(request.user, 'membership') and request.user.membership:
        user_data['membership'] = {
            'name': request.user.membership.name,
            'monthly_fee': str(request.user.membership.monthly_fee),
            'annual_fee': str(request.user.membership.annual_fee),
            'max_books': request.user.membership.max_books,
            'loan_period_days': request.user.membership.loan_period_days,
        }
    
    response = JsonResponse(user_data, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="my_data_{request.user.username}.json"'
    return response

@login_required
@require_http_methods(["GET", "POST"])
def delete_account(request):
    """Delete user account (Right to be Forgotten)"""
    if request.method == 'POST':
        # Anonymize user data instead of hard deletion
        user = request.user
        
        # Store original data for audit purposes
        original_username = user.username
        original_email = user.email
        
        # Anonymize the user data
        user.username = f"deleted_user_{user.id}_{timezone.now().strftime('%Y%m%d')}"
        user.email = f"deleted_{user.id}_{timezone.now().strftime('%Y%m%d')}@deleted.com"
        user.first_name = "Deleted"
        user.last_name = "User"
        user.phone_number = "0000000000"
        user.is_active = False
        
        # Clear sensitive fields
        user.set_unusable_password()
        
        user.save()
        
        # Log the deletion for audit purposes
        try:
            from admin_dashboard.models import AuditLog
            AuditLog.objects.create(
                user=user,
                action='USER_DELETE',
                details=f"Account deletion requested. Original: {original_username} ({original_email})",
                ip_address=request.META.get('REMOTE_ADDR')
            )
        except Exception:
            pass  # Don't fail if audit logging fails
        
        logout(request)
        messages.success(request, "Your account has been successfully deleted. Thank you for using our library system.")
        return redirect('library:home')
    
    return render(request, 'privacy/delete_account_confirm.html')

@login_required
@csrf_protect
@require_http_methods(["POST"])
def update_consent(request):
    """Update user consent preferences"""
    privacy_consent = request.POST.get('privacy_consent') == 'on'
    marketing_consent = request.POST.get('marketing_consent') == 'on'
    
    # Update user consent fields if they exist
    if hasattr(request.user, 'privacy_consent'):
        request.user.privacy_consent = privacy_consent
        request.user.marketing_consent = marketing_consent
        request.user.consent_date = timezone.now()
        request.user.consent_ip = request.META.get('REMOTE_ADDR')
        request.user.save()
    
    messages.success(request, "Your consent preferences have been updated.")
    return redirect('users:profile')

def test_gdpr(request):
    """Test page for GDPR features"""
    return render(request, 'privacy/test_gdpr.html')

def cookie_consent_status(request):
    """API endpoint to check cookie consent status"""
    if request.user.is_authenticated:
        consent_status = {
            'has_consent': request.user.privacy_consent if hasattr(request.user, 'privacy_consent') else False,
            'consent_date': request.user.consent_date.isoformat() if hasattr(request.user, 'consent_date') and request.user.consent_date else None,
        }
    else:
        consent_status = {
            'has_consent': False,
            'consent_date': None,
        }
    
    return JsonResponse(consent_status)
