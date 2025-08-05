from django.utils import timezone
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from datetime import timedelta
from django.conf import settings


class SessionTimeoutMiddleware:
    """
    Middleware to handle automatic session timeout for user inactivity
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            # Get user's custom timeout or default
            timeout_minutes = self._get_user_timeout(request)
            
            if timeout_minutes:
                now = timezone.now()
                last_activity = request.session.get('last_activity')
                
                if last_activity:
                    last_activity = timezone.datetime.fromisoformat(last_activity)
                    if now - last_activity > timedelta(minutes=timeout_minutes):
                        # Session has timed out
                        self._log_session_timeout(request)
                        self._cleanup_user_session(request)
                        logout(request)
                        messages.warning(request, f"Your session has expired due to {timeout_minutes} minutes of inactivity. Please log in again.")
                        return redirect(reverse('users:login'))
                
                # Update last activity
                request.session['last_activity'] = now.isoformat()
                
                # Update or create UserSession record
                self._update_user_session(request, timeout_minutes)
        
        response = self.get_response(request)
        return response
    
    def _get_user_timeout(self, request):
        """Get timeout for user - check UserSession first, then defaults"""
        try:
            from .models import UserSession
            session_key = request.session.session_key
            
            if session_key:
                user_session = UserSession.objects.filter(
                    session_key=session_key,
                    user=request.user
                ).first()
                
                if user_session:
                    return user_session.timeout_minutes
            
            # Fall back to role-based defaults
            return self.get_timeout_minutes(request.user)
        except Exception:
            return 15  # Default fallback
    
    def _update_user_session(self, request, timeout_minutes):
        """Update or create UserSession record for tracking"""
        try:
            from .models import UserSession
            session_key = request.session.session_key
            
            if session_key:
                user_session, created = UserSession.objects.get_or_create(
                    session_key=session_key,
                    defaults={
                        'user': request.user,
                        'is_active': True,
                        'timeout_minutes': timeout_minutes,
                    }
                )
                
                if not created:
                    user_session.last_activity = timezone.now()
                    user_session.is_active = True
                    user_session.timeout_minutes = timeout_minutes
                    user_session.save()
        except Exception:
            # Don't break the request if session tracking fails
            pass
    
    def _cleanup_user_session(self, request):
        """Mark user session as inactive"""
        try:
            from .models import UserSession
            session_key = request.session.session_key
            
            if session_key:
                UserSession.objects.filter(
                    session_key=session_key
                ).update(is_active=False)
        except Exception:
            pass
    
    def _log_session_timeout(self, request):
        """Log session timeout event"""
        try:
            from .models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action='SESSION_TIMEOUT',
                details="Session automatically timed out due to inactivity"
            )
        except Exception:
            pass
    
    def get_timeout_minutes(self, user):
        """Get timeout minutes based on user role from system settings"""
        # Try to get timeout from system settings first
        try:
            from utils.system_settings import SystemSettingsHelper
            
            # Get role-specific timeout or fallback to general setting
            role_specific_key = f"{user.role}_session_timeout_minutes"
            timeout = SystemSettingsHelper.get_setting(role_specific_key, None, 'number')
            
            if timeout is None:
                # Fallback to general session timeout setting
                timeout = SystemSettingsHelper.get_session_timeout_minutes(15)
            
            return timeout
            
        except ImportError:
            pass
        
        # Fallback to hardcoded values if system settings not available
        default_timeout = 15
        role_timeouts = getattr(settings, 'SESSION_TIMEOUT_BY_ROLE', {
            'member': 15,
            'librarian': 15,
            'manager': 30,  # Managers might need longer sessions
            'admin': 30,    # Admins might need longer sessions
        })
        
        return role_timeouts.get(user.role, default_timeout)


class PasswordPolicyMiddleware:
    """
    Middleware to enforce password change policy for admin and manager users
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            # Skip password change check for certain URLs
            exempt_urls = [
                reverse('users:logout'),
                reverse('admin_dashboard:change_password'),
                '/admin/password_change/',
                '/admin/logout/',
            ]
            
            # Check if current URL should be exempt
            current_url = request.path
            is_exempt = any(current_url.startswith(url) for url in exempt_urls if url)
            
            if not is_exempt:
                # Check if password change is required (with delay for admin)
                if request.user.should_force_password_change(request):
                    
                    # For admin users, show different message if delay hasn't passed
                    if (request.user.role == 'admin' and 
                        request.session.get('admin_login_time')):
                        
                        remaining_seconds = request.user.get_password_change_remaining_seconds(request)
                        
                        if remaining_seconds > 0:
                            messages.info(request, 
                                f"Password change will be required in {remaining_seconds} seconds.")
                        else:
                            messages.error(request, 
                                "Your password has expired. Please change your password to continue.")
                            return redirect(reverse('admin_dashboard:change_password'))
                    else:
                        messages.error(request, 
                            "Your password has expired. Please change your password to continue.")
                        return redirect(reverse('admin_dashboard:change_password'))
        
        response = self.get_response(request)
        return response