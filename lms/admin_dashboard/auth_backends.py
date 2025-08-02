from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import AuditLog

User = get_user_model()

class LibraryManagementAuditAuthBackend(ModelBackend):
    """
    Library Management System - Custom Authentication Backend
    
    This backend provides:
    - Comprehensive audit logging for all authentication attempts
    - Failed login tracking and account lockout protection
    - Security monitoring and suspicious activity detection
    - Automatic account unlock after timeout periods
    
    Unique identifier: libsys_lms_audit_auth_v1.0
    """
    
    # Unique backend identifier to prevent conflicts
    BACKEND_ID = "libsys_lms_audit_auth_v1.0"
    BACKEND_NAME = "Library Management System Audit Authentication Backend"
    
    def get_backend_info(self):
        """Return backend identification information"""
        return {
            'id': self.BACKEND_ID,
            'name': self.BACKEND_NAME,
            'version': '1.0',
            'description': 'Library Management System Authentication with Audit Logging',
            'features': [
                'audit_logging',
                'failed_attempt_tracking', 
                'account_lockout',
                'suspicious_activity_detection',
                'automatic_unlock'
            ]
        }
    
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
        """Log successful login with backend identification"""
        ip_address = self._get_client_ip(request)
        try:
            AuditLog.objects.create(
                user=user,
                action='LOGIN_SUCCESS',
                details=f"Successful login from IP: {ip_address} [Auth: {self.BACKEND_ID}]",
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
                details=f"Failed login attempt for username '{username}': {reason}. IP: {ip_address} [Auth: {self.BACKEND_ID}]",
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
    
    @classmethod
    def validate_uniqueness(cls):
        """
        Validate that this backend is uniquely configured
        Returns: dict with validation results
        """
        from django.conf import settings
        
        results = {
            'is_unique': True,
            'conflicts': [],
            'warnings': [],
            'backend_info': {
                'id': cls.BACKEND_ID,
                'name': cls.BACKEND_NAME,
                'path': f'{cls.__module__}.{cls.__name__}'
            }
        }
        
        # Check for duplicate backend entries
        auth_backends = getattr(settings, 'AUTHENTICATION_BACKENDS', [])
        backend_path = f'{cls.__module__}.{cls.__name__}'
        
        # Count occurrences of this backend
        backend_count = auth_backends.count(backend_path)
        if backend_count > 1:
            results['is_unique'] = False
            results['conflicts'].append(f"Backend '{backend_path}' appears {backend_count} times in AUTHENTICATION_BACKENDS")
        
        # Check for similar named backends
        for backend in auth_backends:
            if backend != backend_path and ('audit' in backend.lower() or 'logging' in backend.lower()):
                results['warnings'].append(f"Similar backend detected: {backend}")
        
        # Verify backend is properly positioned (should be first for audit logging)
        if auth_backends and auth_backends[0] != backend_path:
            results['warnings'].append(f"Backend should be first in AUTHENTICATION_BACKENDS for proper audit logging")
        
        return results