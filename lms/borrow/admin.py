from django.contrib import admin
from .models import Borrowing, ExtensionRequest

# Register your models here.
admin.site.register(Borrowing)
admin.site.register(ExtensionRequest)
