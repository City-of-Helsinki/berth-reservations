from django.contrib.admin import site as admin_site
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from parler.admin import TranslatableAdmin
from parler.forms import TranslatableModelForm

from .models import NotificationTemplate


class NotificationTemplateForm(TranslatableModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Do not allow the admin to choose any of the template types that already
        # exist.
        qs = NotificationTemplate.objects.values_list('type', flat=True)
        if self.instance and self.instance.type:
            qs = qs.exclude(id=self.instance.id)
        existing_types = set(enum.value for enum in qs)
        choices = [x for x in self.fields['type'].choices if x[0] not in existing_types]
        self.fields['type'].choices = choices

        admins_qs = get_user_model().objects.exclude(email='').\
            filter(Q(is_superuser=True) | Q(is_staff=True))
        self.fields['admins_to_notify'].choices = [(a.id, a.email) for a in admins_qs]


class NotificationTemplateAdmin(TranslatableAdmin):
    form = NotificationTemplateForm
    fieldsets = [
        (None, {
            'fields': [
                'type',
                'from_email',
            ],
        }),
        (_('User notification'), {
            'fields': [
                'subject',
                'html_body',
                'text_body',
            ],
        }),
        (_('Admin notification'), {
            'fields': [
                'admins_to_notify',
                'admin_notification_subject',
                'admin_notification_text'
            ],
        }),
    ]


admin_site.register(NotificationTemplate, NotificationTemplateAdmin)
