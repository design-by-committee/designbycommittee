from django.http import HttpResponse


class HealthCheckMiddleware:
    """Answer Render's health check at /healthz/ before anything else runs.

    It sits first in MIDDLEWARE so the check doesn't depend on the Host header (ALLOWED_HOSTS), the HTTPS redirect,
    the database or Wagtail's page tree.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/healthz/":
            return HttpResponse("ok", content_type="text/plain")
        return self.get_response(request)
