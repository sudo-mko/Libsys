from django.db import models

# Create your models here.
class Borrowing(models.Model):
    STATUS_CHOICES = [
        ('borrowed', 'Borrowed'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
    ]

    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    book = models.ForeignKey('library.Book', on_delete=models.CASCADE)
    borrow_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    is_extended = models.BooleanField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)


    def __str__(self):
        return f"{str(self.user)} - {str(self.book)}"



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
        