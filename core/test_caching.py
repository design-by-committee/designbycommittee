import io
import re
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import override_settings
from wagtail.images import get_image_model

from core import cache
from core.models import Testimonial
from core.storage import HashedRenditionStorage, is_hashed_rendition
from pages.tests import SiteTestCase

PURGE_SETTINGS = {"RENDER_API_KEY": "test-key", "RENDER_SERVICE_ID": "srv-test"}


class PageCacheHeaderTests(SiteTestCase):
    def test_public_pages_are_cached_at_the_edge_and_revalidated_by_browsers(self):
        for url in ("/", "/comedy/", "/sitemap.xml", "/robots.txt"):
            response = self.client.get(url)
            self.assertEqual(response["Cache-Control"], "public, max-age=0, s-maxage=300, stale-while-revalidate=60", url)
            self.assertFalse(response.cookies, url)  # a Set-Cookie would stop the edge from caching it
            self.assertNotIn("Cookie", response.get("Vary", ""), url)
            self.assertTrue(response.has_header("ETag"), url)

    def test_pages_have_no_csrf_token(self):
        self.assertNotContains(self.client.get("/comedy/"), "csrfmiddlewaretoken")

    def test_revalidation_gets_a_304(self):
        etag = self.client.get("/comedy/")["ETag"]
        self.assertEqual(self.client.get("/comedy/", HTTP_IF_NONE_MATCH=etag).status_code, 304)

    def test_personal_or_one_off_responses_are_private(self):
        self.assertEqual(self.client.get("/comedy/?sent=comedy-enquiry")["Cache-Control"], cache.PRIVATE)
        self.assertEqual(self.client.get("/missing/")["Cache-Control"], cache.PRIVATE)
        self.assertNotIn("public", self.client.get("/admin/login/")["Cache-Control"])

        user = get_user_model().objects.create_superuser("editor", "editor@example.com", "pw")
        self.client.force_login(user)
        self.assertEqual(self.client.get("/comedy/")["Cache-Control"], cache.PRIVATE)

    def test_form_responses_are_private(self):
        response = self.client.post("/comedy/", {"form-name": "comedy-enquiry"}, HTTP_ORIGIN="http://testserver")
        self.assertNotIn("public", response["Cache-Control"])

    @override_settings(**PURGE_SETTINGS)
    def test_pages_stay_cached_longer_when_the_edge_is_purged_on_changes(self):
        self.assertIn("s-maxage=86400", self.client.get("/comedy/")["Cache-Control"])

    @override_settings(EDGE_HTML_MAX_AGE=30)
    def test_edge_max_age_can_be_set(self):
        self.assertIn("s-maxage=30", self.client.get("/comedy/")["Cache-Control"])


class RenditionNameTests(SiteTestCase):
    def test_renditions_get_a_content_hash_in_their_file_name(self):
        image = Testimonial.objects.get(name="Aaron Walther").logo
        rendition = image.get_rendition("fill-120x120")
        self.assertTrue(is_hashed_rendition(rendition.file.name), rendition.file.name)
        self.assertRegex(rendition.url, r"\.fill-120x120\.[0-9a-f]{12}\.svg$")

    def test_pages_link_to_hashed_renditions(self):
        html = self.client.get("/comedy/").content.decode()
        sources = re.findall(r'src="(/media/images/[^"]+)"', html)
        self.assertTrue(sources)
        for source in sources:
            self.assertTrue(is_hashed_rendition(source.removeprefix("/media/")), source)

    def test_same_name_different_content_gets_a_different_file_name(self):
        storage = HashedRenditionStorage()
        first = storage.save("images/photo.width-800.jpg", ContentFile(b"one"))
        second = storage.save("images/photo.width-800.jpg", ContentFile(b"two"))
        self.assertNotEqual(first, second)
        self.assertTrue(is_hashed_rendition(first) and is_hashed_rendition(second))
        self.assertFalse(is_hashed_rendition(storage.save("original_images/photo.jpg", ContentFile(b"x"))))

    def test_hash_renditions_command_replaces_old_unhashed_renditions(self):
        image = Testimonial.objects.get(name="Aaron Walther").logo
        Rendition = get_image_model().get_rendition_model()
        old = Rendition.objects.create(image=image, filter_spec="width-10", file="images/old.width-10.svg", width=10, height=10)

        out = io.StringIO()
        call_command("hash_renditions", stdout=out)
        self.assertIn("Deleted 1", out.getvalue())
        self.assertFalse(Rendition.objects.filter(pk=old.pk).exists())
        call_command("hash_renditions", stdout=out)
        self.assertIn("All image renditions have hashed file names", out.getvalue())


class RunPurgeInline:
    """Stands in for threading.Thread so the purge runs straight away in tests."""

    def __init__(self, target, **kwargs):
        self.target = target

    def start(self):
        self.target()


@override_settings(**PURGE_SETTINGS)
@mock.patch("core.cache.threading.Thread", RunPurgeInline)
class EdgePurgeTests(SiteTestCase):
    def setUp(self):
        patcher = mock.patch("core.cache.purge_edge_cache")
        self.purge = patcher.start()
        self.addCleanup(patcher.stop)
        cache._last_purge["at"] = float("-inf")
        # Each test step below stands for a separate save, more than the debounce window apart
        clock = mock.patch("core.cache.time.monotonic", side_effect=(n * 60.0 for n in range(1, 1000)))
        clock.start()
        self.addCleanup(clock.stop)

    def cms(self, *args):
        call_command("cms", *args, stdout=io.StringIO(), stderr=io.StringIO())

    def test_publishing_purges_once(self):
        changes = '[{"op": "set_field", "field": "seo_title", "value": "New"}, {"op": "set_field", "field": "og_title", "value": "New"}]'
        with self.captureOnCommitCallbacks(execute=True):
            self.cms("pages", "edit", "/comedy/", "--data", changes, "--publish")
        self.assertEqual(self.purge.call_count, 1)

    def test_a_rolled_back_change_doesnt_block_later_purges(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.cms("settings", "update", "sitesettings", "--data", '{"company_name": "Dry"}')  # dry run: rolled back
        self.purge.assert_not_called()
        with self.captureOnCommitCallbacks(execute=True):
            self.cms("settings", "update", "sitesettings", "--data", '{"company_name": "Real"}', "--apply")
        self.assertEqual(self.purge.call_count, 1)

    def test_drafts_and_dry_runs_dont_purge(self):
        changes = '[{"op": "set_field", "field": "seo_title", "value": "Draft"}]'
        with self.captureOnCommitCallbacks(execute=True):
            self.cms("pages", "edit", "/comedy/", "--data", changes)  # dry run
            self.cms("pages", "edit", "/comedy/", "--data", changes, "--draft")
            self.cms("snippets", "update", "testimonial", str(Testimonial.objects.first().pk), "--data", '{"role": "x"}')
        self.purge.assert_not_called()

    def test_snippets_settings_and_images_purge(self):
        testimonial = Testimonial.objects.first()
        with self.captureOnCommitCallbacks(execute=True):
            self.cms("snippets", "update", "testimonial", str(testimonial.pk), "--data", '{"role": "Founder"}', "--apply")
        with self.captureOnCommitCallbacks(execute=True):
            self.cms("settings", "update", "sitesettings", "--data", '{"company_name": "New name"}', "--apply")
        with self.captureOnCommitCallbacks(execute=True):
            self.cms("images", "update", str(testimonial.logo_id), "--data", '{"title": "Renamed"}', "--apply")
        self.assertEqual(self.purge.call_count, 3)

    def test_image_bookkeeping_saves_dont_purge(self):
        image = Testimonial.objects.first().logo
        with self.captureOnCommitCallbacks(execute=True):
            image.save(update_fields=["file_hash"])
        self.purge.assert_not_called()

    @override_settings(RENDER_API_KEY="")
    def test_nothing_is_purged_without_an_api_key(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.cms("settings", "update", "sitesettings", "--data", '{"company_name": "New name"}', "--apply")
        self.purge.assert_not_called()


@override_settings(**PURGE_SETTINGS)
class PurgeRequestTests(SiteTestCase):
    def test_purge_calls_renders_api(self):
        response = mock.MagicMock(status=202)
        response.__enter__.return_value = response
        with mock.patch("core.cache.urllib.request.urlopen", return_value=response) as urlopen:
            self.assertTrue(cache.purge_edge_cache())
        request = urlopen.call_args.args[0]
        self.assertEqual((request.method, request.full_url), ("POST", "https://api.render.com/v1/services/srv-test/cache/purge"))
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")

    def test_failed_purge_is_logged_not_raised(self):
        with mock.patch("core.cache.urllib.request.urlopen", side_effect=OSError("network down")):
            with self.assertLogs("core.cache", "WARNING"):
                self.assertFalse(cache.purge_edge_cache())
