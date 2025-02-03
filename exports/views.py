from typing import Iterable, Type

from django.db.models import Model
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.views import APIView

from applications.enums import ApplicationAreaType
from applications.models import BerthApplication, WinterStorageApplication
from applications.schema import BerthApplicationNode, WinterStorageApplicationNode
from berth_reservations.oidc import BerthApiTokenAuthentication
from customers.models import CustomerProfile
from customers.schema import ProfileNode
from exports.utils import from_global_ids
from exports.xlsx_writer import (
    BaseExportXlsxWriter,
    BerthApplicationXlsx,
    CustomerXlsx,
    WinterStorageApplicationXlsx,
)


class UserHasViewPermission(DjangoModelPermissions):
    """Checks that the user has the permission to view/export the model."""

    perms_map = {
        "OPTIONS": [],
        "HEAD": [],
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.view_%(model_name)s"],
    }


class ExporterArgumentSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.CharField(min_length=1), required=False
    )
    profileToken = serializers.CharField(
        required=False,
        help_text=_("API token for Helsinki profile GraphQL API"),
    )


class BaseExportView(APIView):
    model: Model
    exporter_class: Type[BaseExportXlsxWriter]
    authentication_classes = [BerthApiTokenAuthentication, SessionAuthentication]
    permission_classes = [UserHasViewPermission]

    def get_queryset(self, ids: Iterable = None):
        if ids:
            return self.model.objects.filter(pk__in=ids)
        return self.model.objects.all()

    def get_exporter_kwargs(self, arguments):
        if ids := arguments.get("ids"):
            qs = self.get_queryset(ids)
        else:
            qs = self.get_queryset()

        return {"queryset": qs}

    def post(self, request, *args, **kwargs):
        serializer = ExporterArgumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        arguments = serializer.validated_data
        exporter = self.exporter_class(**self.get_exporter_kwargs(arguments))

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = (
            f"attachment; filename={exporter.filename}.xlsx"
        )

        response.content = exporter.serialize()
        return response


class CustomerExportView(BaseExportView):
    model = CustomerProfile
    exporter_class = CustomerXlsx

    def get_queryset(self, ids: Iterable = None):
        if ids:
            ids = from_global_ids(ids, ProfileNode)
        return super().get_queryset(ids=ids)

    def get_exporter_kwargs(self, arguments):
        kwargs = super().get_exporter_kwargs(arguments)

        if profile_token := arguments.get("profileToken"):
            kwargs["profile_token"] = profile_token
        else:
            raise serializers.ValidationError("profileToken required.")

        return kwargs


class BerthApplicationExportView(BaseExportView):
    model = BerthApplication
    exporter_class = BerthApplicationXlsx

    def get_queryset(self, ids: Iterable = None):
        if ids:
            ids = from_global_ids(ids, BerthApplicationNode)
        return super().get_queryset(ids=ids)


class WinterStorageApplicationExportView(BaseExportView):
    model = WinterStorageApplication
    exporter_class = WinterStorageApplicationXlsx

    def get_queryset(self, ids: Iterable = None):
        if ids:
            ids = from_global_ids(ids, WinterStorageApplicationNode)
        return (
            super().get_queryset(ids=ids).filter(area_type=ApplicationAreaType.MARKED)
        )


class UnmarkedWinterStorageApplicationExportView(BaseExportView):
    model = WinterStorageApplication
    exporter_class = WinterStorageApplicationXlsx

    def get_queryset(self, ids: Iterable = None):
        if ids:
            ids = from_global_ids(ids, WinterStorageApplicationNode)
        return (
            super().get_queryset(ids=ids).filter(area_type=ApplicationAreaType.UNMARKED)
        )
