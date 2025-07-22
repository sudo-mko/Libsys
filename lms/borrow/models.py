from django.db import models
import string
import random
from django.utils import timezone
from datetime import timedelta

# Create your models here.
class Borrowing(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('borrowed', 'Borrowed'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
        ('expired', 'Expired'),  # For expired pickup codes
    ]

    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    book = models.ForeignKey('library.Book', on_delete=models.CASCADE)
    borrow_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    is_extended = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    pickup_code = models.CharField(max_length=10, null=True, blank=True, unique=True)
    approved_date = models.DateTimeField(null=True, blank=True)
    pickup_date = models.DateTimeField(null=True, blank=True)  # When librarian confirms pickup
    rejected_date = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='rejected_borrowings')
    rejection_reason = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{str(self.user)} - {str(self.book)}"

    def generate_pickup_code(self):
        """Generate a unique 10-character alphanumeric pickup code"""
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            if not Borrowing.objects.filter(pickup_code=code).exists():
                self.pickup_code = code
                break
        return self.pickup_code

    def is_code_expired(self):
        """Check if the pickup code has expired (3 days after approval)"""
        if not self.approved_date:
            return False
        expiration_date = self.approved_date + timedelta(days=3)
        return timezone.now() > expiration_date

    def days_until_code_expiry(self):
        """Calculate days until code expires"""
        if not self.approved_date:
            return None
        expiration_date = self.approved_date + timedelta(days=3)
        days_left = (expiration_date - timezone.now()).days
        return max(0, days_left)  # Don't return negative days



class ExtensionRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    borrowing = models.ForeignKey(Borrowing, on_delete=models.CASCADE)
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_extensions')
    approval_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ('borrowing',)  # Ensures only one extension request per borrowing
    
    def __str__(self):
        return f"Extension Request - {self.borrowing.user.username} - {self.borrowing.book.title}" # type: ignore
        