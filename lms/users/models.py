from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError

# Create your models here.

class MembershipType(models.Model):
    name = models.CharField(max_length=50)  # Basic, Premium, Student
    monthly_fee = models.DecimalField(max_digits=6, decimal_places=2)
    annual_fee = models.DecimalField(max_digits=6, decimal_places=2)
    max_books = models.PositiveIntegerField()
    loan_period_days = models.PositiveIntegerField()
    extension_days = models.PositiveIntegerField()

    def clean(self):
        """Custom validation for MembershipType model"""
        errors = {}
        
        # Validate negative fees
        if self.monthly_fee is not None and self.monthly_fee < 0:
            errors['monthly_fee'] = 'Monthly fee cannot be negative.'
        
        if self.annual_fee is not None and self.annual_fee < 0:
            errors['annual_fee'] = 'Annual fee cannot be negative.'
        
        # Validate zero max_books
        if self.max_books is not None and self.max_books <= 0:
            errors['max_books'] = 'Maximum books must be at least 1.'
        
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.name

class User(AbstractUser):
    ROLE_CHOICES = (
        ('member', 'Library Member'),
        ('librarian', 'Librarian'),
        ('manager', 'Library Manager'),
        ('admin', 'Admin'),
    )
    phone_number = models.CharField(max_length=20)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')  # e.g. member, librarian, manager, admin
    membership = models.ForeignKey(MembershipType, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Account lock fields
    failed_login_attempts = models.PositiveIntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    last_failed_attempt = models.DateTimeField(null=True, blank=True)
    
    # Password policy fields
    last_password_change = models.DateTimeField(null=True, blank=True)
    password_change_required = models.BooleanField(default=False)
    
    # GDPR Consent fields
    privacy_consent = models.BooleanField(default=False, help_text="Consent to process personal data")
    marketing_consent = models.BooleanField(default=False, help_text="Consent to receive marketing communications")
    consent_date = models.DateTimeField(null=True, blank=True, help_text="Date when consent was given")
    consent_ip = models.GenericIPAddressField(null=True, blank=True, help_text="IP address when consent was given")
    
    # Add related_name attributes to avoid clash
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='user_custom_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='user_custom_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    def is_account_locked(self):
        """Check if the account is currently locked"""
        if self.account_locked_until:
            if timezone.now() < self.account_locked_until:
                return True
            else:
                # Lock has expired, clear it automatically and give fresh start
                self.account_locked_until = None
                self.failed_login_attempts = 0  # Reset failed attempts for fresh start
                self.save()
                return False
        return False
    
    def get_lock_remaining_seconds(self):
        """Get remaining lock time in seconds"""
        if self.is_account_locked():
            return int((self.account_locked_until - timezone.now()).total_seconds())
        return 0
    
    def should_show_warning(self):
        """Check if we should show warning about approaching lock"""
        lock_settings = getattr(settings, 'ACCOUNT_LOCK_SETTINGS', {})
        warning_threshold = lock_settings.get('WARNING_THRESHOLD', 3)
        return self.failed_login_attempts >= warning_threshold
    
    def increment_failed_attempts(self):
        """Increment failed login attempts and lock if threshold reached"""
        lock_settings = getattr(settings, 'ACCOUNT_LOCK_SETTINGS', {})
        max_attempts = lock_settings.get('MAX_FAILED_ATTEMPTS', 5)
        lock_duration = lock_settings.get('LOCK_DURATION_MINUTES', 5)
        affected_roles = lock_settings.get('AFFECTED_USER_ROLES', ['member'])
        
        # Only apply locking to affected user roles
        if self.role not in affected_roles:
            return
            
        self.failed_login_attempts += 1
        self.last_failed_attempt = timezone.now()
        
        if self.failed_login_attempts >= max_attempts:
            self.account_locked_until = timezone.now() + timedelta(minutes=lock_duration)
            
        self.save()
    
    def reset_lock_status(self, performed_by=None, reason=""):
        """Reset account lock status (for successful login or manual unlock)"""
        self.account_locked_until = None
        self.failed_login_attempts = 0  # Reset failed attempts on unlock
        self.save()
    
    def lock_account_manually(self, performed_by, reason="", duration_minutes=None):
        """Manually lock account (admin action)"""
        from django.conf import settings
        from datetime import timedelta
        
        # Use provided duration or default from settings
        if duration_minutes is None:
            lock_settings = getattr(settings, 'ACCOUNT_LOCK_SETTINGS', {})
            duration_minutes = lock_settings.get('LOCK_DURATION_MINUTES', 30)
        
        self.account_locked_until = timezone.now() + timedelta(minutes=duration_minutes)
        self.save()
    
    def is_password_expired(self):
        """Check if password has expired for admin/manager users"""
        if self.role not in ['admin', 'manager']:
            return False
            
        if not self.last_password_change:
            # If no password change recorded, assume it needs to be changed
            return True
            
        # Check if 6 months have passed
        expiry_date = self.last_password_change + timedelta(days=180)  # 6 months
        return timezone.now() > expiry_date
    
    def should_force_password_change(self, request=None):
        """Check if user should be forced to change password (with 1-minute delay for admin)"""
        # For non-admin users, use the original logic
        if self.role != 'admin':
            return (self.password_change_required or self.is_password_expired())
        
        # For admin users, check if password change is required or expired
        if not (self.password_change_required or self.is_password_expired()):
            return False
        
        # If no request provided, use original logic
        if not request:
            return True
        
        # Check if admin just logged in and delay hasn't passed
        admin_login_time = request.session.get('admin_login_time')
        if admin_login_time:
            from datetime import datetime
            login_time = datetime.fromisoformat(admin_login_time.replace('Z', '+00:00'))
            delay_time = login_time + timedelta(minutes=1)
            return timezone.now() >= delay_time
        
        return True
    
    def get_password_change_remaining_seconds(self, request):
        """Get remaining seconds before password change is required for admin"""
        if self.role != 'admin' or not request:
            return 0
        
        admin_login_time = request.session.get('admin_login_time')
        if admin_login_time:
            from datetime import datetime
            login_time = datetime.fromisoformat(admin_login_time.replace('Z', '+00:00'))
            delay_time = login_time + timedelta(minutes=1)
            remaining_seconds = int((delay_time - timezone.now()).total_seconds())
            return max(0, remaining_seconds)
        
        return 0
    
    def mark_admin_login(self, request):
        """Mark the time when admin logged in for password change delay"""
        if self.role == 'admin' and request:
            request.session['admin_login_time'] = timezone.now().isoformat()
    
    def clear_admin_login_time(self, request):
        """Clear admin login time from session"""
        if request and 'admin_login_time' in request.session:
            del request.session['admin_login_time']
    
    def mark_password_changed(self):
        """Mark that password was changed"""
        self.last_password_change = timezone.now()
        self.password_change_required = False
        self.save()
    
    def force_password_change(self):
        """Force user to change password on next login"""
        self.password_change_required = True
        self.save()