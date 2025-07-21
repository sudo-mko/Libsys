from django.db import models

# Create your models here.
class Branch(models.Model):
    branch_name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)

    def __str__(self):
        return self.branch_name



class Section(models.Model):
    name = models.CharField(max_length=100)
    branch_id = models.ForeignKey(Branch, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

