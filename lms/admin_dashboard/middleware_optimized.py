from django.utils import timezone
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from datetime import timedelta
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

# Cache timeouts
SESSION_CHECK_CACHE_TIMEOUT = 60  # 1 minute
TIMEOUT_CHECK_CACHE_TIMEOUT = 30  # 30 seconds

class OptimizedSessionTimeoutMiddleware:
    """
    Optimized middleware to handle automatic session timeout with reduced validation frequency
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            # Cache session validation to reduce database queries
            session_cache_key = f'session_valid_{request.user.id}'
            session_valid = cache.get(session_cache_key)
            
            if session_valid is None:
                # Only perform full session check if not cached
                session_valid = self._perform_session_check(request)
                cache.set(session_cache_key, session_valid, SESSION_CHECK_CACHE_TIMEOUT)
            
            if not session_valid:
                # Session is invalid, logout user
                self._handle_session_timeout(request)
                return redirect(reverse('users:login'))
            
            # Update last activity (cached to reduce database writes)
            self._update_last_activity_cached(request)
        
        response = self.get_response(request)
        return response
    
    def _perform_session_check(self, request):
        """Perform full session validation check"""
        try:
            # Get user's timeout setting
            timeout_minutes = self._get_user_timeout_cached(request)
            
            if timeout_minutes:
                now = timezone.now()
                last_activity = request.session.get('last_activity')
                
                if last_activity:
                    last_activity = timezone.datetime.fromisoformat(last_activity)
                    if now - last_activity > timedelta(minutes=timeout_minutes):
                        return False
                
                # Update last activity
                request.session['last_activity'] = now.isoformat()
            
            return True
        except Exception as e:
            logger.error(f"Session check failed: {e}")
            return False
    
    def _get_user_timeout_cached(self, request):
        """Get user timeout with caching"""
        cache_key = f'user_timeout_{request.user.id}'
        timeout = cache.get(cache_key)
        
        if timeout is None:
            timeout = self._get_user_timeout(request)
            cache.set(cache_key, timeout, SESSION_CHECK_CACHE_TIMEOUT)
        
        return timeout
    
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
    
    def _update_last_activity_cached(self, request):
        """Update last activity with caching to reduce database writes"""
        cache_key = f'last_activity_{request.user.id}'
        last_update = cache.get(cache_key)
        
        if last_update is None:
            # Update database only if not recently updated
            self._update_user_session(request)
            cache.set(cache_key, timezone.now(), TIMEOUT_CHECK_CACHE_TIMEOUT)
    
    def _update_user_session(self, request):
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
                        'timeout_minutes': self._get_user_timeout_cached(request),
                    }
                )
                
                if not created:
                    user_session.last_activity = timezone.now()
                    user_session.is_active = True
                    user_session.save(update_fields=['last_activity', 'is_active'])
        except Exception as e:
            logger.warning(f"Failed to update user session: {e}")
    
    def _handle_session_timeout(self, request):
        """Handle session timeout"""
        try:
            # Log session timeout
            from .models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action='SESSION_TIMEOUT',
                details="Session automatically timed out due to inactivity"
            )
            
            # Cleanup user session
            self._cleanup_user_session(request)
            
            # Logout user
            logout(request)
            messages.warning(request, "Your session has expired due to inactivity. Please log in again.")
            
        except Exception as e:
            logger.error(f"Failed to handle session timeout: {e}")
    
    def _cleanup_user_session(self, request):
        """Mark user session as inactive"""
        try:
            from .models import UserSession
            session_key = request.session.session_key
            
            if session_key:
                UserSession.objects.filter(
                    session_key=session_key
                ).update(is_active=False)
        except Exception as e:
            logger.warning(f"Failed to cleanup user session: {e}")
    
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
            'manager': 30,
            'admin': 30,
        })
        
        return role_timeouts.get(user.role, default_timeout)


class OptimizedPasswordPolicyMiddleware:
    """
    Optimized middleware to enforce password change policy with reduced checks
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            # Cache password policy check
            policy_cache_key = f'password_policy_{request.user.id}'
            policy_check = cache.get(policy_cache_key)
            
            if policy_check is None:
                # Only check password policy if not cached
                policy_check = self._check_password_policy(request)
                cache.set(policy_cache_key, policy_check, SESSION_CHECK_CACHE_TIMEOUT)
            
            if policy_check:
                # Password change required
                messages.error(request, 
                    "Your password has expired. Please change your password to continue.")
                return redirect(reverse('admin_dashboard:change_password'))
        
        response = self.get_response(request)
        return response
    
    def _check_password_policy(self, request):
        """Check if password change is required"""
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
            return request.user.should_force_password_change(request)
        
        return False


class CacheInvalidationMiddleware:
    """
    Middleware to invalidate relevant caches when data changes
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Invalidate session caches on logout
        if request.path == reverse('users:logout'):
            if request.user.is_authenticated:
                cache.delete(f'session_valid_{request.user.id}')
                cache.delete(f'user_timeout_{request.user.id}')
                cache.delete(f'last_activity_{request.user.id}')
                cache.delete(f'password_policy_{request.user.id}')
        
        return response 