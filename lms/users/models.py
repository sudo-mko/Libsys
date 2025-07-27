from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta
from django.conf import settings

# Create your models here.

class MembershipType(models.Model):
    name = models.CharField(max_length=50)  # Basic, Premium, Student
    monthly_fee = models.DecimalField(max_digits=6, decimal_places=2)
    annual_fee = models.DecimalField(max_digits=6, decimal_places=2)
    max_books = models.PositiveIntegerField()
    loan_period_days = models.PositiveIntegerField()
    extension_days = models.PositiveIntegerField()

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
    
    def reset_lock_status(self):
        """Reset account lock status (for successful login or manual unlock)"""
        self.account_locked_until = None
        self.save()


