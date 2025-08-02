from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import AuditLog

User = get_user_model()

class AuditingAuthBackend(ModelBackend):
    """
    Custom authentication backend that logs all login attempts
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        
        if username is None or password is None:
            return None
        
        try:
            user = User._default_manager.get_by_natural_key(username)
        except User.DoesNotExist:
            # Log failed login attempt for non-existent user
            self._log_failed_login(request, username, "User does not exist")
            return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            # Successful login
            self._log_successful_login(request, user)
            self._reset_failed_attempts(user)
            return user
        else:
            # Failed login attempt
            self._log_failed_login(request, username, "Invalid password")
            self._handle_failed_attempt(request, user if 'user' in locals() else None)
            return None
    
    def _log_successful_login(self, request, user):
        """Log successful login"""
        ip_address = self._get_client_ip(request)
        try:
            AuditLog.objects.create(
                user=user,
                action='LOGIN_SUCCESS',
                details=f"Successful login from IP: {ip_address}",
                ip_address=ip_address
            )
        except Exception:
            pass
    
    def _log_failed_login(self, request, username, reason):
        """Log failed login attempt"""
        ip_address = self._get_client_ip(request)
        try:
            # Try to get user for logging, but create anonymous log if user doesn't exist
            user = None
            try:
                user = User._default_manager.get_by_natural_key(username)
            except User.DoesNotExist:
                pass
            
            AuditLog.objects.create(
                user=user,
                action='LOGIN_FAILED',
                details=f"Failed login attempt for username '{username}': {reason}. IP: {ip_address}",
                ip_address=ip_address
            )
        except Exception:
            pass
    
    def _handle_failed_attempt(self, request, user):
        """Handle failed login attempt and check for suspicious activity"""
        if user:
            # Update failed login attempts
            user.failed_login_attempts = getattr(user, 'failed_login_attempts', 0) + 1
            user.last_failed_login = timezone.now()
            
            # Check if account should be locked
            max_attempts = getattr(user, 'max_failed_attempts', 5)
            if user.failed_login_attempts >= max_attempts:
                user.account_locked_until = timezone.now() + timedelta(minutes=30)
                user.save()
                
                # Log account lockout
                try:
                    AuditLog.objects.create(
                        user=user,
                        action='ACCOUNT_LOCKED',
                        details=f"Account locked after {user.failed_login_attempts} failed login attempts",
                        ip_address=self._get_client_ip(request)
                    )
                except Exception:
                    pass
            
            # Check for multiple recent failures (suspicious activity)
            elif user.failed_login_attempts >= 3:
                try:
                    AuditLog.objects.create(
                        user=user,
                        action='MULTIPLE_LOGIN_FAILURES',
                        details=f"Multiple failed login attempts ({user.failed_login_attempts}) detected",
                        ip_address=self._get_client_ip(request)
                    )
                except Exception:
                    pass
            
            user.save()
    
    def _reset_failed_attempts(self, user):
        """Reset failed login attempts on successful login"""
        if hasattr(user, 'failed_login_attempts') and user.failed_login_attempts > 0:
            user.failed_login_attempts = 0
            user.last_failed_login = None
            user.account_locked_until = None
            user.save()
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                return x_forwarded_for.split(',')[0].strip()
            else:
                return request.META.get('REMOTE_ADDR', 'Unknown')
        return 'Unknown'
    
    def user_can_authenticate(self, user):
        """
        Check if user can authenticate (not locked)
        """
        # Check if account is locked
        if hasattr(user, 'account_locked_until') and user.account_locked_until:
            if timezone.now() < user.account_locked_until:
                return False
            else:
                # Unlock account if lock period has expired
                user.account_locked_until = None
                user.failed_login_attempts = 0
                user.save()
                
                # Log account unlock
                try:
                    AuditLog.objects.create(
                        user=user,
                        action='ACCOUNT_UNLOCKED',
                        details="Account automatically unlocked after lock period expired",
                        ip_address='System'
                    )
                except Exception:
                    pass
        
        return super().user_can_authenticate(user)