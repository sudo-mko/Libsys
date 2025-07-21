from django.db import models

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

    def __str__(self):
        return self.title

