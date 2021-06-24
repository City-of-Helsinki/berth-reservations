import datetime
import logging

from anymail.exceptions import AnymailError
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.models import Permission
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from django_ilmoitin.utils import send_notification
from parler.admin import TranslatableAdmin
from pytz import timezone

from .enums import ApplicationAreaType
from .models import (
    BerthApplication,
    BerthSwitch,
    BerthSwitchReason,
    HarborChoice,
    WinterStorageApplication,
    WinterStorageAreaChoice,
)
from .notifications import NotificationType
from .utils import (
    export_berth_applications_as_xlsx,
    export_winter_storage_applications_as_xlsx,
)

logger = logging.getLogger(__name__)


class ApplicationTypeFilter(admin.SimpleListFilter):
    title = _("Application type")

    parameter_name = "berth_switch"

    def lookups(self, request, model_admin):
        return (("0", _("Application")), ("1", _("Switch application")))

    def queryset(self, request, queryset):
        kwargs = {"{}".format(self.parameter_name): None}
        if self.value() == "0":
            return queryset.filter(**kwargs)
        if self.value() == "1":
            return queryset.exclude(**kwargs)
        return queryset


class HarborChoiceInline(admin.TabularInline):
    model = HarborChoice
    ordering = ("priority",)
    fields = ("priority", "harbor")
    extra = 10
    max_num = 10

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super(HarborChoiceInline, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )
        if db_field.name == "harbor":
            field.queryset = field.queryset.translated("fi")
        return field


class BerthApplicationInline(admin.StackedInline):
    model = BerthApplication
    extra = 0


class BerthSwitchAdmin(admin.ModelAdmin):
    model = BerthSwitch
    list_display = ("id", "berth", "reason", "berth_applications")
    readonly_fields = ("berth_applications",)
    search_fields = (
        "id",
        "number",
        "pier__identifier",
        "pier__harbor__translations__name",
        "pier__harbor_id",
    )
    autocomplete_fields = ("berth",)

    def berth_applications(self, obj):
        return ", ".join([str(application) for application in obj.applications.all()])

    berth_applications.short_description = _("Applications")


class BerthApplicationAdmin(admin.ModelAdmin):
    inlines = [HarborChoiceInline]
    readonly_fields = [
        "application_type",
        "created_at",
        "get_berth_switch_id",
        "get_berth_switch_berth",
        "get_berth_switch_reason",
    ]
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "application_type",
                    "created_at",
                    "status",
                    "customer",
                    "priority",
                ]
            },
        ),
        (
            _("Contact information"),
            {
                "fields": [
                    "first_name",
                    "last_name",
                    "email",
                    "phone_number",
                    "address",
                    "zip_code",
                    "municipality",
                    "company_name",
                    "business_id",
                ]
            },
        ),
        (
            _("Main boat information"),
            {
                "fields": [
                    "boat_type",
                    "boat_registration_number",
                    "boat_name",
                    "boat_model",
                    "boat_length",
                    "boat_width",
                    "boat_draught",
                    "boat_weight",
                    "accessibility_required",
                ]
            },
        ),
        (
            _("Large vessel information"),
            {
                "fields": [
                    "boat_propulsion",
                    "boat_hull_material",
                    "boat_intended_use",
                    "renting_period",
                    "rent_from",
                    "rent_till",
                    "boat_is_inspected",
                    "boat_is_insured",
                    "agree_to_terms",
                ]
            },
        ),
        (
            _("Switch berth information"),
            {
                "fields": [
                    "get_berth_switch_id",
                    "get_berth_switch_berth",
                    "get_berth_switch_reason",
                ]
            },
        ),
        (
            _("Other information"),
            {
                "fields": [
                    "language",
                    "accept_boating_newsletter",
                    "accept_fitness_news",
                    "accept_library_news",
                    "accept_other_culture_news",
                    "information_accuracy_confirmed",
                    "application_code",
                ]
            },
        ),
    ]
    list_display = (
        "id",
        "created_at",
        "first_name",
        "last_name",
        "application_type",
        "status",
    )
    autocomplete_fields = ("customer",)
    list_filter = (
        ApplicationTypeFilter,
        "status",
        "priority",
    )
    search_fields = ("id", "first_name", "last_name")
    autocomplete_fields = ("customer",)
    actions = ["export_applications", "resend_application_confirmation"]

    def application_type(self, obj):
        return _("Application") if obj.berth_switch is None else _("Switch application")

    def get_berth_switch_id(self, obj):
        return obj.berth_switch.id

    get_berth_switch_id.short_description = _("Id")

    def get_berth_switch_berth(self, obj):
        return (
            f"{obj.berth_switch.berth.pier.harbor.name} "
            f"({obj.berth_switch.berth.pier.identifier}) "
            f"{obj.berth_switch.berth.number}"
        )

    get_berth_switch_berth.short_description = _("Berth")

    def get_berth_switch_reason(self, obj):
        return obj.berth_switch.reason.title

    get_berth_switch_reason.short_description = _("Reason")

    def export_applications(self, request, queryset):
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        local_datetime_now_as_str = datetime.datetime.now(
            timezone(settings.TIME_ZONE)
        ).strftime("%Y-%m-%d_%H-%M-%S")
        filename = "berth_applications_" + local_datetime_now_as_str
        response["Content-Disposition"] = "attachment; filename=%s.xlsx" % filename

        response.content = export_berth_applications_as_xlsx(queryset)
        return response

    export_applications.short_description = _(
        "Download list of chosen applications in Excel file"
    )

    def resend_application_confirmation(self, request, queryset):
        resent_count = 0
        for application in queryset:
            context = {
                "subject": NotificationType.BERTH_APPLICATION_CREATED.label,
                **application.get_notification_context(),
            }
            try:
                send_notification(
                    application.email,
                    NotificationType.BERTH_APPLICATION_CREATED.value,
                    context,
                    application.language,
                )
                resent_count += 1
            except (OSError, AnymailError):
                logger.error(
                    "Failed to resend confirmation for berth application {}".format(
                        application.id
                    )
                )

        self.message_user(
            request,
            _("Resent confirmation for %d berth application(s)") % resent_count,
            messages.SUCCESS,
        )

    resend_application_confirmation.short_description = _(
        "Send confirmation again for chosen application"
    )
    resend_application_confirmation.allowed_permissions = ("resend",)

    def has_resend_permission(self, request):
        opts = self.opts
        codename = "resend_application"
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))


class WinterStorageAreaChoiceInline(admin.TabularInline):
    model = WinterStorageAreaChoice
    ordering = ("priority",)
    fields = ("priority", "winter_storage_area")
    extra = 5
    max_num = 5


class WinterStorageApplicationInline(admin.StackedInline):
    model = WinterStorageApplication
    extra = 0


class WinterStorageApplicationAdmin(admin.ModelAdmin):
    inlines = [WinterStorageAreaChoiceInline]
    readonly_fields = [
        "created_at",
        "area_type",
    ]
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "created_at",
                    "status",
                    "customer",
                    "storage_method",
                    "trailer_registration_number",
                    "priority",
                ]
            },
        ),
        (
            _("Contact information"),
            {
                "fields": [
                    "first_name",
                    "last_name",
                    "email",
                    "phone_number",
                    "address",
                    "zip_code",
                    "municipality",
                    "company_name",
                    "business_id",
                ]
            },
        ),
        (
            _("Main boat information"),
            {
                "fields": [
                    "boat_type",
                    "boat_registration_number",
                    "boat_name",
                    "boat_model",
                    "boat_length",
                    "boat_width",
                ]
            },
        ),
        (
            _("Other information"),
            {
                "fields": [
                    "language",
                    "accept_boating_newsletter",
                    "accept_fitness_news",
                    "accept_library_news",
                    "accept_other_culture_news",
                    "information_accuracy_confirmed",
                    "application_code",
                ]
            },
        ),
    ]
    list_display = (
        "id",
        "created_at",
        "first_name",
        "last_name",
        "area_type",
        "status",
    )
    autocomplete_fields = ("customer",)
    list_filter = ("area_type", "status", "priority")
    actions = ["export_applications", "resend_application_confirmation"]
    search_fields = ("id", "first_name", "last_name")

    def export_applications(self, request, queryset):
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        local_datetime_now_as_str = datetime.datetime.now(
            timezone(settings.TIME_ZONE)
        ).strftime("%Y-%m-%d_%H-%M-%S")
        filename = "winter_storage_applications_" + local_datetime_now_as_str
        response["Content-Disposition"] = "attachment; filename=%s.xlsx" % filename

        response.content = export_winter_storage_applications_as_xlsx(queryset)
        return response

    export_applications.short_description = _(
        "Download list of chosen applications in Excel file"
    )

    def resend_application_confirmation(self, request, queryset):
        resent_count = 0
        for application in queryset:
            try:
                notification_type = (
                    NotificationType.UNMARKED_WINTER_STORAGE_APPLICATION_CREATED
                    if application.area_type == ApplicationAreaType.UNMARKED
                    else NotificationType.WINTER_STORAGE_APPLICATION_CREATED
                )
                context = {
                    "subject": notification_type.label,
                    **application.get_notification_context(),
                }
                send_notification(
                    application.email,
                    notification_type.value,
                    context,
                    application.language,
                )
                resent_count += 1
            except (OSError, AnymailError):
                logger.error(
                    "Failed to resend confirmation for winter storage application {}".format(
                        application.id
                    )
                )

        self.message_user(
            request,
            _("Resent confirmation for %d winter storage application(s)")
            % resent_count,
            messages.SUCCESS,
        )

    resend_application_confirmation.short_description = _(
        "Send confirmation again for chosen application"
    )
    resend_application_confirmation.allowed_permissions = ("resend",)

    def has_resend_permission(self, request):
        opts = self.opts
        codename = "resend_application"
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))


class BerthSwitchReasonAdmin(TranslatableAdmin):
    pass


admin.site.register(BerthApplication, BerthApplicationAdmin)
admin.site.register(WinterStorageApplication, WinterStorageApplicationAdmin)
admin.site.register(BerthSwitch, BerthSwitchAdmin)
admin.site.register(BerthSwitchReason, BerthSwitchReasonAdmin)

# Register Permission model for GUI management of permissions
admin.site.register(Permission)
