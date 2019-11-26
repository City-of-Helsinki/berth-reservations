from django.contrib import admin
from django.contrib.auth import get_user_model

from customers.admin import CustomerProfileInline


class UserAdmin(admin.ModelAdmin):
    inlines = (CustomerProfileInline,)
    readonly_fields = ("password",)


admin.site.register(get_user_model(), UserAdmin)
