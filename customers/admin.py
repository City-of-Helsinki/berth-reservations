from django.contrib import admin

from .models import CustomerProfile


class CustomerProfileInline(admin.StackedInline):
    model = CustomerProfile
    fk_name = "user"
    extra = 0
