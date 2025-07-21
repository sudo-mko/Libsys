from django.db import models

# Create your models here.
class Fine(models.Model):
    borrowing = models.ForeignKey('borrow.Borrowing', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=6, decimal_places=2)
    days_overdue = models.PositiveIntegerField()
    paid = models.BooleanField()
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Fine for { str(self.borrowing)}"