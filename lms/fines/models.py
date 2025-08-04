from django.db import models
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import ValidationError

# Create your models here.
class Fine(models.Model):
    FINE_TYPE_CHOICES = [
        ('overdue', 'Overdue Fine'),
        ('damaged', 'Damaged/Lost Book'),
    ]
    
    borrowing = models.ForeignKey('borrow.Borrowing', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=6, decimal_places=2)
    days_overdue = models.PositiveIntegerField()
    paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    fine_type = models.CharField(max_length=20, choices=FINE_TYPE_CHOICES, default='overdue')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Fine for {str(self.borrowing)} - {self.get_fine_type_display()}: {self.amount} MVR"

    def clean(self):
        """Custom validation for Fine model"""
        errors = {}
        
        # Validate negative amounts
        if self.amount is not None and self.amount < 0:
            errors['amount'] = 'Fine amount cannot be negative.'
        
        if errors:
            raise ValidationError(errors)

    @staticmethod
    def calculate_overdue_fine(days_overdue):
        """
        Calculate overdue fine based on days late:
        1-3 days: 2 MVR per day
        4-7 days: 5 MVR per day  
        8+ days: 10 MVR per day
        """
        if days_overdue <= 0:
            return Decimal('0.00')
        
        total_fine = Decimal('0.00')
        
        if days_overdue <= 3:
            # 1-3 days: 2 MVR per day
            total_fine = Decimal('2.00') * days_overdue
        elif days_overdue <= 7:
            # First 3 days at 2 MVR per day, remaining days at 5 MVR per day
            total_fine = Decimal('2.00') * 3 + Decimal('5.00') * (days_overdue - 3)
        else:
            # First 3 days at 2 MVR, next 4 days at 5 MVR, remaining at 10 MVR
            total_fine = (Decimal('2.00') * 3 + 
                         Decimal('5.00') * 4 + 
                         Decimal('10.00') * (days_overdue - 7))
        
        return total_fine

    @staticmethod  
    def calculate_damaged_fine(book_price):
        """
        Calculate damaged/lost book fine: Full book price + 50 MVR processing fee
        """
        return Decimal(str(book_price)) + Decimal('50.00')