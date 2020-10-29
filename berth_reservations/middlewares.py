from django.conf import settings


class HostFixupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """
        Forces X_FORWARDED_HOST to a fixed value, for
        those nasty proxy setups there
        """
        request.META["HTTP_X_FORWARDED_HOST"] = settings.FORCED_HOST
        return self.get_response(request)
