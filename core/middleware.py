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


class PackagePriceMiddleware:
    """Fill price placeholders ({solo.price}, {solo.pounds}) in pages, previews and llms.txt (pages/prices.py).

    Admin screens are left alone, so editors see and save the placeholders, not the prices. It sits after
    ConditionalGetMiddleware in MIDDLEWARE, so ETags are computed from the filled-in page.
    """

    CONTENT_TYPES = ("text/html", "text/markdown")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not self.applies(request, response):
            return response
        from core.models import SiteSettings
        from pages.prices import fill_prices

        charset = response.charset or "utf-8"
        text = response.content.decode(charset)
        filled = fill_prices(text, SiteSettings.for_request(request).pounds_per_euro)
        if filled != text:
            response.content = filled.encode(charset)
            if response.has_header("Content-Length"):
                response["Content-Length"] = str(len(response.content))
        return response

    def applies(self, request, response):
        if response.streaming or response.status_code != 200:
            return False
        if not response.get("Content-Type", "").startswith(self.CONTENT_TYPES):
            return False
        path = request.path
        if path.startswith(("/static/", "/media/", "/documents/")):
            return False
        # Admin screens keep the placeholders; page previews (rendered pages inside the admin) are filled in
        return not path.startswith("/admin/") or "/preview/" in path
