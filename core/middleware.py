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


class PrivateByDefaultMiddleware:
    """Mark every response that doesn't set its own Cache-Control as private.

    Render's edge cache (with "All files" caching on) would otherwise keep a 200 response without the header for two
    hours. Pages, media, robots.txt and the sitemap opt in to edge caching explicitly (core/cache.py); everything else,
    such as the admin, previews and form responses, stays private. Static files from WhiteNoise set their own header.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from core.cache import PRIVATE

        response = self.get_response(request)
        cache_control = response.get("Cache-Control", "")
        # A response that sets a cookie is never shared, even if a view marked it public.
        if not cache_control or (response.cookies and "public" in cache_control):
            response["Cache-Control"] = PRIVATE
        return response
