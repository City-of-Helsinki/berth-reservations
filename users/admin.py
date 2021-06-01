from django.contrib import admin
from django.contrib.auth import get_user_model

from customers.admin import CustomerProfileInline


class UserAdmin(admin.ModelAdmin):
    list_filter = ("groups",)
    list_display = (
        "id",
        "customer",
        "__str__",
    )
    inlines = (CustomerProfileInline,)
    readonly_fields = ("password",)
    search_fields = (
        "id",
        "email",
        "first_name",
        "last_name",
    )


admin.site.register(get_user_model(), UserAdmin)
