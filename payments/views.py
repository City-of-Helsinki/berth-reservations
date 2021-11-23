from django.conf import settings
from django.http import HttpRequest
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .providers import get_payment_provider


class SuccessView(View):
    def get(self, request: HttpRequest):
        return get_payment_provider(
            request, ui_return_url=settings.VENE_UI_RETURN_URL
        ).handle_success_request()


class FailureView(View):
    def get(self, request: HttpRequest):
        return get_payment_provider(
            request, ui_return_url=settings.VENE_UI_RETURN_URL
        ).handle_failure_request()


@csrf_exempt
def notify_view(request: HttpRequest):
    return get_payment_provider(
        request, ui_return_url=settings.VENE_UI_RETURN_URL
    ).handle_notify_request()


@csrf_exempt
def notify_refund_view(request: HttpRequest):
    return get_payment_provider(request).handle_notify_refund_request()
