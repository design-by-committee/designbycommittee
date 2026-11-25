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
        self.assertContains(self.client.get("/"), '<meta name="robots" content="max-image-preview:large">')

    def test_other_hosts_are_not_indexed(self):
        self.assertContains(self.client.get("/robots.txt"), "Disallow: /")
        self.assertContains(self.client.get("/"), '<meta name="robots" content="noindex">')
        self.assertNotContains(self.client.get("/"), "max-image-preview")

    def test_old_index_html_redirects_home(self):
        self.assertRedirects(self.client.get("/index.html"), "/", status_code=301)

    def test_health_check(self):
        self.assertContains(self.client.get("/healthz/"), "ok")


class StructuredDataTests(SiteTestCase):
    def json_ld(self, url):
        import json

        html = self.client.get(url).content.decode()
        scripts = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
        self.assertEqual(len(scripts), 1, url)
        return {self.node_type(node): node for node in json.loads(scripts[0])["@graph"]}

    @staticmethod
    def node_type(node):
        types = node["@type"]
        return types[0] if isinstance(types, list) else types

    def test_every_page_describes_the_organisation_and_website(self):
        for url in ("/", "/comedy/"):
            graph = self.json_ld(url)
            organisation = graph["ProfessionalService"]
            self.assertEqual(organisation["name"], "Design by Committee")
            self.assertEqual(organisation["legalName"], "Design by Committee BV")
            self.assertEqual(organisation["founder"]["name"], "Andres Lucero")
            self.assertIn("United Kingdom", organisation["areaServed"])
            self.assertEqual(graph["WebSite"]["publisher"], {"@id": organisation["@id"]})

    def test_faq_section_becomes_faq_page(self):
        webpage = self.json_ld("/comedy/")["WebPage"]
        self.assertEqual(webpage["@type"], ["WebPage", "FAQPage"])
        self.assertEqual(webpage["mainEntity"][0]["@type"], "Question")
        self.assertTrue(webpage["mainEntity"][0]["acceptedAnswer"]["text"])
        self.assertEqual(self.json_ld("/")["WebPage"]["@type"], "WebPage")

    def test_packages_become_offers_with_prices(self):
        service = self.json_ld("/comedy/")["Service"]
        self.assertEqual(service["name"], "Website design for comedians, comedy shows and comedy venues")
        self.assertEqual(service["audience"]["audienceType"], "Comedians, comedy shows and comedy venues")
        offers = {offer["name"]: offer for offer in service["hasOfferCatalog"]["itemListElement"]}
        self.assertEqual((offers["Solo"]["price"], offers["Solo"]["priceCurrency"]), ("495", "EUR"))
        self.assertEqual(offers["Venue"]["priceSpecification"]["minPrice"], "1950")

    def test_breadcrumbs_below_the_home_page(self):
        crumbs = self.json_ld("/comedy/")["BreadcrumbList"]["itemListElement"]
        self.assertEqual([crumb["name"] for crumb in crumbs], ["Home", "Comedy"])
        self.assertNotIn("BreadcrumbList", self.json_ld("/"))

    def test_extra_json_ld_from_the_admin_is_added(self):
        self.comedy.extra_json_ld = '{"@context": "https://schema.org", "@type": "Event", "name": "Fringe </script>"}'
        self.comedy.save_revision().publish()
        graph = self.json_ld("/comedy/")
        self.assertEqual(graph["Event"]["name"], "Fringe </script>")
        self.assertNotIn("@context", graph["Event"])

    def test_extra_json_ld_must_be_a_json_object(self):
        from django.core.exceptions import ValidationError

        from pages.models import validate_json_ld

        for value in ("not json", "[1, 2]", "[]", '"text"'):
            with self.assertRaises(ValidationError, msg=value):
                validate_json_ld(value)
        validate_json_ld('[{"@type": "Event"}]')

    def test_settings_changes_show_up(self):
        from core.models import SiteSettings

        settings = SiteSettings.objects.get()
        settings.same_as = "https://www.instagram.com/example/\n\nhttps://www.linkedin.com/company/example/\n"
        settings.address_locality = "Utrecht"
        settings.save()
        organisation = self.json_ld("/")["ProfessionalService"]
        self.assertEqual(len(organisation["sameAs"]), 2)
        self.assertEqual(organisation["address"], {"@type": "PostalAddress", "addressLocality": "Utrecht", "addressCountry": "Netherlands"})


class PriceParsingTests(SiteTestCase):
    def test_prices(self):
        from pages.structured_data import parse_price

        self.assertEqual(parse_price("€500"), ("500", "EUR"))
        self.assertEqual(parse_price("from €3,500"), ("3500", "EUR"))
        self.assertEqual(parse_price("£1.200"), ("1200", "GBP"))
        self.assertEqual(parse_price("1 950 EUR"), ("1950", "EUR"))
        self.assertIsNone(parse_price("Ask us"))


class SearchTagTests(SiteTestCase):
    def test_social_tags(self):
        response = self.client.get("/comedy/")
        self.assertContains(response, '<meta property="og:site_name" content="Design by Committee">')
        self.assertContains(response, '<meta property="og:locale" content="en_GB">')
        self.assertContains(response, '<meta name="twitter:card" content="summary_large_image">')
        self.assertRegex(response.content.decode(), r'<meta property="og:image:width" content="\d+">')

    def test_verification_codes_from_site_settings(self):
        from core.models import SiteSettings

        response = self.client.get("/")
        self.assertNotContains(response, "google-site-verification")
        SiteSettings.objects.filter().update(google_site_verification="abc123", bing_site_verification="def456")
        response = self.client.get("/")
        self.assertContains(response, '<meta name="google-site-verification" content="abc123">')
        self.assertContains(response, '<meta name="msvalidate.01" content="def456">')

    @override_settings(INDEXABLE_HOSTS=["testserver"])
    def test_hidden_pages_are_noindex_and_left_out_of_the_sitemap(self):
        self.comedy.noindex = True
        self.comedy.save_revision().publish()
        self.assertContains(self.client.get("/comedy/"), '<meta name="robots" content="noindex">')
        self.assertNotContains(self.client.get("/sitemap.xml"), "/comedy/")
        self.assertNotContains(self.client.get("/llms.txt"), "/comedy/")

    def test_footer_links_to_pages_shown_in_menus(self):
        self.assertContains(self.client.get("/"), '<nav class="footer__nav" aria-label="Site">')
        self.assertContains(self.client.get("/"), 'href="/comedy/">Comedy</a>')
        self.assertContains(self.client.get("/comedy/"), 'href="/comedy/" aria-current="page">Comedy</a>')

    def test_company_name_ending_in_a_full_stop(self):
        from core.models import SiteSettings

        SiteSettings.objects.filter().update(company_name="Design by Committee B.V.")
        self.assertContains(self.client.get("/"), "Design by Committee B.V. <span")


class LlmsTxtTests(SiteTestCase):
    def test_llms_txt(self):
        response = self.client.get("/llms.txt")
        self.assertEqual(response["Content-Type"], "text/markdown; charset=utf-8")
        text = response.content.decode()
        self.assertTrue(text.startswith("# Design by Committee\n\n> Design by Committee is a web design studio"))
        self.assertIn("- [WordPress Websites for Comedians and Comedy Shows | Committee](http://testserver/comedy/): ", text)
        self.assertIn("- Solo (€495 one-off): For comedians; Live in 2–4 weeks", text)
        self.assertIn("- Founder: [Andres Lucero](https://www.linkedin.com/in/andreslucero/)", text)

    def test_extra_text_from_site_settings(self):
        from core.models import SiteSettings

        SiteSettings.objects.filter().update(llms_txt_details="We don’t build online shops.")
        self.assertIn("We don’t build online shops.", self.client.get("/llms.txt").content.decode())


class SeoAdminTests(SiteTestCase):
    """Everything in the page head is editable in the admin."""

    def setUp(self):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_superuser("editor", "editor@example.com", "x")
        self.client.force_login(user)

    def test_site_settings_tabs(self):
        from wagtail.models import Site

        site = Site.objects.get(is_default_site=True)
        response = self.client.get(f"/admin/settings/core/sitesettings/{site.pk}/")
        self.assertEqual(response.status_code, 200)
        for field in ("organisation_description", "areas_served", "same_as", "google_site_verification", "llms_txt_details"):
            self.assertContains(response, f'name="{field}"')

    def test_page_promote_tab(self):
        response = self.client.get(f"/admin/pages/{self.comedy.pk}/edit/")
        self.assertEqual(response.status_code, 200)
        for field in ("noindex", "service_name", "service_audience", "areas_served", "extra_json_ld"):
            self.assertContains(response, f'name="{field}"')
