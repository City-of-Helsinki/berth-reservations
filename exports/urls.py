from django.urls import path

from exports.views import CustomerExportView

urlpatterns = [
    path(
        "customers/xlsx/",
        CustomerExportView.as_view(),
        name="customer_xlsx",
    ),
]
