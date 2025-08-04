from django.db import models
from django.core.exceptions import ValidationError

# Create your models here.
class Author(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Category(models.Model):
    category_name = models.CharField(max_length=100)

    def __str__(self):
        return self.category_name

class Book(models.Model):
    title = models.CharField(max_length=100)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    isbn = models.CharField(max_length=13, unique=True)
    publication_date = models.DateField()
    branch = models.ForeignKey('branches.Branch', on_delete=models.CASCADE)
    edition = models.IntegerField()
    description = models.TextField()
    cover = models.ImageField(upload_to='book_covers/', null=True, blank=True)

    def clean(self):
        """Custom validation for Book model"""
        errors = {}
        
        # Validate ISBN length (should be 10 or 13 digits)
        if self.isbn:
            # Remove any hyphens or spaces
            clean_isbn = ''.join(filter(str.isdigit, self.isbn))
            if len(clean_isbn) < 10:
                errors['isbn'] = 'ISBN must be at least 10 digits long.'
        
        # Validate edition number
        if self.edition is not None and self.edition <= 0:
            errors['edition'] = 'Edition number must be positive (greater than 0).'
        
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.title

