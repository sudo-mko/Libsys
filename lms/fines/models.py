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
        Calculate overdue fine based on configurable tiered system:
        Tier 1 (1-3 days): configurable rate per day
        Tier 2 (4-7 days): configurable rate per day  
        Tier 3 (8+ days): configurable rate per day
        """
        if days_overdue <= 0:
            return Decimal('0.00')
        
        # Import here to avoid circular imports
        try:
            from utils.system_settings import SystemSettingsHelper
            tier_1_days = SystemSettingsHelper.get_setting('fine_tier_1_days', 3, 'number')
            tier_1_rate = SystemSettingsHelper.get_setting('fine_tier_1_rate', Decimal('2.00'), 'decimal')
            tier_2_days = SystemSettingsHelper.get_setting('fine_tier_2_days', 7, 'number')
            tier_2_rate = SystemSettingsHelper.get_setting('fine_tier_2_rate', Decimal('5.00'), 'decimal')
            tier_3_rate = SystemSettingsHelper.get_setting('fine_tier_3_rate', Decimal('10.00'), 'decimal')
        except ImportError:
            # Fallback to hardcoded values
            tier_1_days, tier_1_rate = 3, Decimal('2.00')
            tier_2_days, tier_2_rate = 7, Decimal('5.00')
            tier_3_rate = Decimal('10.00')
        
        total_fine = Decimal('0.00')
        
        if days_overdue <= tier_1_days:
            # Tier 1: configurable rate per day
            total_fine = tier_1_rate * days_overdue
        elif days_overdue <= tier_2_days:
            # First tier at tier 1 rate, remaining days at tier 2 rate
            total_fine = tier_1_rate * tier_1_days + tier_2_rate * (days_overdue - tier_1_days)
        else:
            # First tiers at their rates, remaining at tier 3 rate
            tier_2_extra_days = tier_2_days - tier_1_days
            total_fine = (tier_1_rate * tier_1_days + 
                         tier_2_rate * tier_2_extra_days + 
                         tier_3_rate * (days_overdue - tier_2_days))
        
        return total_fine

    @staticmethod  
    def calculate_damaged_fine(book_price):
        """
        Calculate damaged/lost book fine: Full book price + configurable processing fee
        """
        # Import here to avoid circular imports
        try:
            from utils.system_settings import SystemSettingsHelper
            processing_fee = SystemSettingsHelper.get_setting('damaged_book_processing_fee', Decimal('50.00'), 'decimal')
        except ImportError:
            processing_fee = Decimal('50.00')  # Fallback to hardcoded value
            
        return Decimal(str(book_price)) + processing_fee