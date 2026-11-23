import tempfile
from pathlib import Path

from django.test import SimpleTestCase, override_settings
from django.urls import path

from core.views import media, robots_txt

urlpatterns = [
    path("robots.txt", robots_txt),
    path("media/<path:path>", media),
]

MEDIA_ROOT = tempfile.mkdtemp(prefix="dbc-test-media-")


@override_settings(ROOT_URLCONF=__name__, MEDIA_ROOT=MEDIA_ROOT)
class CoreViewTests(SimpleTestCase):
    def test_head_requests_are_allowed(self):
        # Link checkers and CDNs use HEAD; Django's require_GET would answer 405.
        Path(MEDIA_ROOT, "logo.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
        self.assertEqual(self.client.head("/robots.txt").status_code, 200)
        response = self.client.head("/media/logo.svg")
        self.assertEqual(response.status_code, 200)
        self.assertIn("max-age=2592000", response["Cache-Control"])

    def test_health_check_ignores_the_host_header(self):
        response = self.client.get("/healthz/", HTTP_HOST="10.0.0.12:10000")
        self.assertEqual(response.content, b"ok")
