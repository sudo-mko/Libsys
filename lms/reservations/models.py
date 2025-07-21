from django.db import models

# Create your models here.
class Reservation(models.Model):
    TYPE_CHOICES = [
        ('regular', 'Regular'),
        ('priority', 'Priority'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('expired', 'Expired'),
        ('rejected', 'Rejected'), 
    ]
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    book = models.ForeignKey('library.Book', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{str(self.user)} - {str(self.book)}"


