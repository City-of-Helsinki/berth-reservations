from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import ugettext_lazy as _


class Reservation(models.Model):
    created_at = models.DateTimeField(verbose_name=_('created at'), auto_now_add=True)

    first_name = models.CharField(_('first name'), max_length=40, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)
    email = models.EmailField(_('email address'), blank=True)

    data = JSONField(blank=True, null=True)

    def __str__(self):
        return '{}: {} {}'.format(self.pk, self.first_name, self.last_name)
