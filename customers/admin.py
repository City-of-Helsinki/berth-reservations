import json

from django.contrib import admin, messages
from django.forms import forms
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import path

from applications.admin import BerthApplicationInline, WinterStorageApplicationInline
from leases.admin import BerthLeaseInline, WinterStorageLeaseInline
from payments.admin import OrderInline

from .models import Boat, BoatCertificate, CustomerProfile, Organization


class ImportProfilesFromJsonForm(forms.Form):
    json_file = forms.FileField(required=True, label="Please select a json file")


class CustomerProfileInline(admin.StackedInline):
    model = CustomerProfile
    fk_name = "user"
    extra = 0


class BoatInline(admin.StackedInline):
    model = Boat
    fk_name = "owner"
    extra = 0


class BoatCertificateInline(admin.StackedInline):
    model = BoatCertificate
    fk_name = "boat"
    extra = 0


class OrganizationInline(admin.StackedInline):
    model = Organization
    fk_name = "customer"
    extra = 0


class BoatAdmin(admin.ModelAdmin):
    inlines = (BoatCertificateInline,)


class BoatCertificateAdmin(admin.ModelAdmin):
    pass


class OrganizationAdmin(admin.ModelAdmin):
    pass


class CustomerProfileAdmin(admin.ModelAdmin):
    inlines = (
        BoatInline,
        OrganizationInline,
        BerthApplicationInline,
        BerthLeaseInline,
        WinterStorageApplicationInline,
        WinterStorageLeaseInline,
        OrderInline,
    )

    change_list_template = "admin/customers/profiles_changelist.html"

    def get_readonly_fields(self, request, obj=None):
        if obj:
            # Mark id field as readonly for existing objects
            return self.readonly_fields + ("id",)
        return self.readonly_fields

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path("upload-json/", self.upload_json, name="upload-json")]
        return my_urls + urls

    def upload_json(self, request):
        try:
            if request.method == "POST":
                data = json.loads(request.FILES["json_file"].read())
                result = CustomerProfile.objects.import_customer_data(data)
                response = JsonResponse(result)
                response["Content-Disposition"] = "attachment; filename=export.json"
                return response
            else:
                form = ImportProfilesFromJsonForm()
                return render(
                    request, "admin/customers/upload_json.html", {"form": form},
                )
        except Exception as err:
            messages.error(request, err)
            form = ImportProfilesFromJsonForm()
            return render(request, "admin/customers/upload_json.html", {"form": form},)


admin.site.register(Boat, BoatAdmin)
admin.site.register(BoatCertificate, BoatCertificateAdmin)
admin.site.register(Organization, OrganizationAdmin)
admin.site.register(CustomerProfile, CustomerProfileAdmin)
