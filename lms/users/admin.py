from django.contrib import admin
from .models import User, MembershipType
# Register your models here.

admin.site.register(User)
admin.site.register(MembershipType)
