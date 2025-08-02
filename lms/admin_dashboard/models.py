from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

User = get_user_model()

class SystemSettings(models.Model):
    """Model for storing system configuration settings"""
    SETTING_TYPES = [
        ('SESSION_TIMEOUT', 'Session Timeout'),
        ('PASSWORD_POLICY', 'Password Policy'),
        ('FINE_SETTINGS', 'Fine Settings'),
        ('BORROWING_LIMITS', 'Borrowing Limits'),
        ('RESERVATION_TIMEOUT', 'Reservation Timeout'),
    ]
    
    setting_type = models.CharField(max_length=50, choices=SETTING_TYPES)
    setting_key = models.CharField(max_length=100)
    setting_value = models.TextField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['setting_type', 'setting_key']
        unique_together = [('setting_type', 'setting_key')]
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'
    
    def __str__(self):
        return self.setting_key

class SystemSetting(models.Model):
    """Simplified system setting model for basic key-value pairs"""
    SETTING_TYPES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
    ]
    
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    setting_type = models.CharField(max_length=20, choices=SETTING_TYPES, default='text')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = "System Setting"
        verbose_name_plural = "System Settings"
    
    def __str__(self):
        return self.key

class AuditLog(models.Model):
    """Model for tracking admin actions and system changes"""
    ACTION_CHOICES = [
        # Authentication & Security
        ('LOGIN_SUCCESS', 'Successful Login'),
        ('LOGIN_FAILED', 'Failed Login Attempt'),
        ('LOGOUT', 'User Logout'),
        ('PASSWORD_CHANGE', 'Password Changed'),
        ('ACCOUNT_LOCKED', 'Account Locked'),
        ('ACCOUNT_UNLOCKED', 'Account Unlocked'),
        ('FORCE_LOGOUT', 'Force Logout'),
        ('SESSION_TIMEOUT', 'Session Timeout'),
        ('MULTIPLE_LOGIN_FAILURES', 'Multiple Login Failures'),
        ('SUSPICIOUS_ACTIVITY', 'Suspicious Activity'),
        
        # User Management
        ('USER_CREATE', 'User Created'),
        ('USER_UPDATE', 'User Updated'),
        ('USER_DELETE', 'User Deleted'),
        ('USER_ROLE_CHANGE', 'User Role Changed'),
        
        # Book Management
        ('BOOK_CREATE', 'Book Created'),
        ('BOOK_UPDATE', 'Book Updated'),
        ('BOOK_DELETE', 'Book Deleted'),
        ('BOOK_VIEW', 'Book Viewed'),
        
        # Borrowing Activities
        ('BOOK_BORROW', 'Book Borrowed'),
        ('BOOK_RETURN', 'Book Returned'),
        ('BORROWING_APPROVE', 'Borrowing Approved'),
        ('BORROWING_REJECT', 'Borrowing Rejected'),
        ('EXTENSION_REQUEST', 'Extension Requested'),
        ('EXTENSION_APPROVE', 'Extension Approved'),
        
        # Reservations
        ('RESERVATION_CREATE', 'Reservation Created'),
        ('RESERVATION_APPROVE', 'Reservation Approved'),
        ('RESERVATION_REJECT', 'Reservation Rejected'),
        ('RESERVATION_EXPIRE', 'Reservation Expired'),
        
        # Fines & Payments
        ('FINE_CREATE', 'Fine Created'),
        ('FINE_PAID', 'Fine Paid'),
        ('FINE_WAIVE', 'Fine Waived'),
        ('FINE_UPDATE', 'Fine Updated'),
        
        # System Administration
        ('ADMIN_DASHBOARD_ACCESS', 'Admin Dashboard Access'),
        ('AUDIT_LOGS_ACCESS', 'Audit Logs Access'),
        ('SESSION_MANAGEMENT_ACCESS', 'Session Management Access'),
        ('SETTING_UPDATE', 'System Setting Updated'),
        ('UPDATE_TIMEOUT', 'Session Timeout Updated'),
        ('BULK_OPERATION', 'Bulk Operation Performed'),
        
        # Legacy support
        ('LOGIN', 'User Login'),
        ('BORROWING_CREATE', 'Borrowing Created'),
        ('BORROWING_UPDATE', 'Borrowing Updated'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    details = models.TextField()  # Changed from description to details to match existing schema
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"
    
    @property
    def action_type(self):
        """For backward compatibility with template"""
        return self.action
    
    def get_action_type_display(self):
        """For backward compatibility with template"""
        return self.get_action_display()
    
    @property
    def description(self):
        """For backward compatibility with existing code"""
        return self.details

class PasswordHistory(models.Model):
    """Track password history for users"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_history')
    password_hash = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name = 'Password History'
        verbose_name_plural = 'Password History'
        ordering = ['-created_at']

class UserSession(models.Model):
    """Track user sessions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_activity = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    timeout_minutes = models.IntegerField(default=15, help_text="Session timeout in minutes")
    
    class Meta:
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'
        ordering = ['-last_activity']