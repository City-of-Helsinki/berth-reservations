from django.urls import path

from exports.views import (
    BerthApplicationExportView,
    CustomerExportView,
    WinterStorageApplicationExportView,
)

urlpatterns = [
    path(
        "customers/xlsx/",
        CustomerExportView.as_view(),
        name="customer_xlsx",
    ),
    path(
        "berth-applications/xlsx/",
        BerthApplicationExportView.as_view(),
        name="berth_applications_xlsx",
    ),
    path(
        "winter-storage-applications/xlsx/",
        WinterStorageApplicationExportView.as_view(),
        name="winter_storage_applications_xlsx",
    ),
]
