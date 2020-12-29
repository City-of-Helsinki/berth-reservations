import json
import logging
import time

from django.conf import settings

logger = logging.getLogger("requests")


__all__ = ["LogRequestFilter", "RequestLogger"]


class LogRequestFilter(logging.Filter):
    """Since the requests are being logged by the RequestLogger,
    we filter the django.server logs to avoid having duplicate logs"""

    def filter(self, record: logging.LogRecord):
        return record.name != "django.server"


class RequestLogger:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        exec_time = time.time()
        response = self.get_response(request)
        exec_time = int((time.time() - exec_time) * 1000)

        try:
            path = request.get_full_path()
            status = response.status_code
            method = request.method
            body = request.body.decode(request.encoding or "utf-8")
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                pass

            message = f"{method} {path} {status}"
            context = {
                "host": request.get_host(),
                "method": method,
                "agent": request.headers.get("USER_AGENT", ""),
                "referrer": request.headers.get("HTTP_REFERER", ""),
                "language": request.headers.get("HTTP_ACCEPT_LANGUAGE", ""),
                "content_length": request.headers.get("HTTP_CONTENT_LENGTH", ""),
                "body": body,
                "path": path,
                "status": status,
                "exec_time": exec_time,
            }
            level = logging.INFO
            if path in settings.REQUEST_LOGGER_IGNORE_PATHS:
                level = logging.DEBUG
            elif 400 >= status > 500:
                level = logging.WARNING
            elif status >= 500:
                level = logging.ERROR

            logger.log(level, message, extra=context)
        except Exception as e:
            logger.exception("Failed logging", exc_info=e)

        return response
