from django.db import models
from django.contrib.auth.models import AbstractUser

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


