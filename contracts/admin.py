from django.contrib import admin

from .models import VismaBerthContract, VismaWinterStorageContract

admin.site.register([VismaBerthContract, VismaWinterStorageContract])
