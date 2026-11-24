import re
import shutil
import tempfile

from django.core.management import call_command
from django.test import TestCase, override_settings

from pages.models import HomePage, LandingPage

MEDIA_ROOT = tempfile.mkdtemp(prefix="dbc-test-media-")


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class SiteTestCase(TestCase):
    """Imports the original site's content once for the whole test class."""

    @classmethod
    def setUpTestData(cls):
        call_command("import_current_site", hostname="testserver", port=80, verbosity=0, stdout=open("/dev/null", "w"))
        cls.home = HomePage.objects.get()
        cls.comedy = LandingPage.objects.get(slug="comedy")

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)


class ImportTests(SiteTestCase):
    def test_pages_are_live_at_the_original_urls(self):
        self.assertEqual(self.home.url, "/")
        self.assertEqual(self.comedy.url, "/comedy/")
        self.assertTrue(self.home.live and self.comedy.live)

    def test_running_again_keeps_admin_edits(self):
        self.comedy.title = "Edited in the admin"
        self.comedy.save_revision().publish()

        call_command("import_current_site", hostname="testserver", port=80, stdout=open("/dev/null", "w"))

        self.comedy.refresh_from_db()
        self.assertEqual(self.comedy.title, "Edited in the admin")


class RenderTests(SiteTestCase):
    def test_home_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<title>Accelerate Growth with Conversion-Optimized Design by Committee</title>")
        self.assertContains(response, '<span class="text-extrabold">Accelerate Growth</span> with Conversion-Optimized')
        self.assertContains(response, 'id="landing-page-assessment"')
        self.assertContains(response, "Henry Flores")
        self.assertContains(response, 'class="carousel__logo"')
        self.assertContains(response, '<html lang="en">')

    def test_comedy_page(self):
        response = self.client.get("/comedy/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<title>WordPress Websites for Comedians and Comedy Shows | Committee</title>")
        self.assertContains(response, '<link rel="canonical" href="http://testserver/comedy/">')
        self.assertContains(response, '<meta property="og:title" content="Fill more seats at every show">')
        self.assertContains(response, 'id="comedy-enquiry"')
        self.assertContains(response, 'data-package="venue"')
        self.assertContains(response, "“Andres created our website")
        self.assertContains(response, '<html lang="en-GB">')

    def test_footer_year_is_current(self):
        from django.utils import timezone

        self.assertContains(self.client.get("/"), f"© {timezone.now().year} Design by Committee BV.")


class PricingButtonTests(SiteTestCase):
    def test_pricing_buttons_name_the_quote_form_option_they_select(self):
        response = self.client.get("/comedy/")
        for code, client_type in (("solo", "Performer"), ("show", "Showrunner"), ("venue", "Venue owner")):
            self.assertContains(response, f'data-package="{code}" data-client-type="{client_type}"')
            # comedy.js checks the radio with this value
            self.assertContains(response, f'name="client-type" value="{client_type}"')


class FaqTests(SiteTestCase):
    def test_blank_lines_in_an_answer_start_new_paragraphs(self):
        body = self.comedy.body
        faq = next(block for block in body if block.block_type == "faq")
        faq.value["questions"][0]["answer"] = "First paragraph.\r\n\r\nSecond paragraph."
        self.comedy.body = body
        self.comedy.save_revision().publish()
        response = self.client.get("/comedy/")
        self.assertContains(response, "<p>First paragraph.</p>")
        self.assertContains(response, "<p>Second paragraph.</p>")


class MobileFieldTests(SiteTestCase):
    """Fields bring up the right phone keyboard and offer autofill."""

    def field_attrs(self, url, name):
        html = self.client.get(url).content.decode()
        tag = re.search(rf'<input[^>]*name="{name}"[^>]*>', html, re.DOTALL).group(0)
        return dict(re.findall(r'([a-z-]+)="([^"]*)"', tag))

    def test_comedy_form(self):
        self.assertEqual(self.field_attrs("/comedy/", "link")["inputmode"], "url")
        self.assertEqual(self.field_attrs("/comedy/", "link")["autocomplete"], "url")
        self.assertEqual(self.field_attrs("/comedy/", "name")["autocomplete"], "name")
        self.assertEqual(self.field_attrs("/comedy/", "email")["type"], "email")

    def test_assessment_form(self):
        self.assertEqual(self.field_attrs("/", "url")["inputmode"], "url")
        self.assertEqual(self.field_attrs("/", "first-name")["autocomplete"], "given-name")
        self.assertEqual(self.field_attrs("/", "last-name")["autocomplete"], "family-name")
        self.assertEqual(self.field_attrs("/", "email")["autocomplete"], "email")


class PageSpeedTests(SiteTestCase):
    def test_pages_only_load_files_from_this_site(self):
        # Fonts and scripts from other hosts block the first render while a new connection is set up
        for url in ("/", "/comedy/"):
            html = self.client.get(url).content.decode()
            sources = re.findall(r'<(?:link|script)[^>]+(?:href|src)="([^"]+)"', html)
            external = [s for s in sources if s.startswith(("http:", "https:", "//")) and "testserver" not in s]
            self.assertEqual(external, [], url)

    def test_fonts_are_preloaded(self):
        self.assertContains(self.client.get("/"), 'as="font" type="font/woff2" crossorigin', count=3)

    def test_assessment_form_uses_native_date_and_time_fields(self):
        response = self.client.get("/")
        self.assertContains(response, '<input type="date" id="date" name="date" required>')
        self.assertContains(response, 'type="time" id="time" name="time" min="09:00" max="18:00" required>')  # any minute

    def test_screenshots_are_responsive_webp(self):
        html = self.client.get("/comedy/").content.decode()
        hero = re.search(r'<img[^>]*fetchpriority="high"[^>]*>', html).group(0)
        self.assertIn("sizes=", hero)
        self.assertEqual(len(re.findall(r"\.webp \d+w", hero)), 3, hero)


class SiteFilesTests(SiteTestCase):
    def test_sitemap_lists_both_pages(self):
        response = self.client.get("/sitemap.xml")
        self.assertContains(response, "<loc>http://testserver/</loc>")
        self.assertContains(response, "<loc>http://testserver/comedy/</loc>")

    @override_settings(INDEXABLE_HOSTS=["testserver"])
    def test_live_host_is_indexable(self):
        response = self.client.get("/robots.txt")
        self.assertContains(response, "Disallow:\n")
        self.assertContains(response, "Sitemap: http://testserver/sitemap.xml")
        self.assertNotContains(self.client.get("/"), 'name="robots"')

    def test_other_hosts_are_not_indexed(self):
        self.assertContains(self.client.get("/robots.txt"), "Disallow: /")
        self.assertContains(self.client.get("/"), '<meta name="robots" content="noindex">')

    def test_old_index_html_redirects_home(self):
        self.assertRedirects(self.client.get("/index.html"), "/", status_code=301)

    def test_health_check(self):
        self.assertContains(self.client.get("/healthz/"), "ok")
