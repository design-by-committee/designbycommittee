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


class CardLinkTests(SiteTestCase):
    def test_case_study_links_to_the_live_site(self):
        from pages.models import CaseStudy

        CaseStudy.objects.filter(title="Fallout Theater").update(link_text="Visit the site", link_url="https://example.com/")
        self.assertContains(
            self.client.get("/comedy/"), '<a href="https://example.com/" class="arrow-right c-card__link">Visit the site</a>'
        )

    def test_fringe_package_selects_performer(self):
        from leads.forms import PACKAGE_CLIENT_TYPES

        self.assertEqual(PACKAGE_CLIENT_TYPES["fringe"], "Performer")


class IllustratedPointsTests(SiteTestCase):
    def test_points_with_screenshots(self):
        from pages.content_ops import apply_changes

        image = self.comedy.body[0].value["screenshot"]
        apply_changes(self.comedy, [{"op": "insert", "type": "illustrated_points", "value": {
            "anchor": "include",
            "heading": "The essentials",
            "points": [{
                "title": "A short bio",
                "text": "First paragraph.\r\n\r\nSecond paragraph.",
                "image": {"image": image.pk, "alt_text": "A bio page", "decorative": False},
                "address": "yourname.com/about",
            }],
        }}])
        self.comedy.save_revision().publish()
        response = self.client.get("/comedy/")
        self.assertContains(response, '<h3>A short bio</h3>')
        self.assertContains(response, "<p>Second paragraph.</p>")
        self.assertContains(response, '<span class="c-browser__url">yourname.com/about</span>')
        self.assertContains(response, 'alt="A bio page"')


class TextPhotoTests(SiteTestCase):
    def test_text_section_with_a_photo(self):
        from pages.content_ops import apply_changes

        image = self.comedy.body[0].value["screenshot"]
        apply_changes(self.comedy, [{"op": "insert", "type": "text", "value": {
            "anchor": "about", "heading": "About Committee", "body": "<p>Hello.</p>",
            "image": {"image": image.pk, "alt_text": "Two live shows", "decorative": False},
        }}])
        self.comedy.save_revision().publish()
        response = self.client.get("/comedy/")
        self.assertContains(response, '<div class="c-wrap c-text-photo">')
        # The images-in-main height cap (small.css, medium.css) would squash the photo at full width
        import re
        from pathlib import Path

        from django.conf import settings

        css = (Path(settings.BASE_DIR) / "static/css/comedy.css").read_text()
        rule = re.search(r"\.c-text-photo__image \{.*?\n\}", css, re.DOTALL).group(0)
        self.assertIn("max-height: none", rule)
        self.assertContains(response, 'alt="Two live shows"')


class IconGridAndPackageIntroTests(SiteTestCase):
    def edit(self, changes):
        from pages.content_ops import apply_changes

        apply_changes(self.comedy, changes)
        self.comedy.save_revision().publish()
        return self.client.get("/comedy/")

    def test_icon_grid(self):
        response = self.edit([{"op": "insert", "type": "icon_grid", "value": {
            "heading": "If you’re running a show", "columns": "2",
            "items": [{"icon": "qr", "title": "A QR code for print", "text": "<p>Opens a <b>ticket page</b>.</p>"}],
            "footnote": '<p>See the <a href="/edfringe/">Fringe package</a>.</p>',
        }}])
        self.assertContains(response, '<ul class="c-icon-grid c-icon-grid--2">')
        self.assertContains(response, '<svg class="c-icon__svg"')
        self.assertContains(response, "<h3>A QR code for print</h3>")
        self.assertContains(response, "<b>ticket page</b>")
        self.assertContains(response, '<a href="/edfringe/">Fringe package</a>')

    def test_a_single_package_sits_beside_its_introduction(self):
        from pages.content_ops import stream_data

        packages = next(block for block in self.comedy.body if block.block_type == "packages")
        raw = next(block for block in stream_data(self.comedy.body) if block["type"] == "packages")
        first_package = raw["value"]["packages"][0]["value"]
        response = self.edit([
            {"op": "set", "block": packages.id, "path": "lead", "value": '<p><a href="/comedy/#packages">All packages</a></p>'},
            {"op": "set", "block": packages.id, "path": "packages", "value": [first_package]},
        ])
        self.assertContains(response, '<div class="c-package-single">')
        # The heading sits in the left column with the introduction, not above both columns
        self.assertRegex(response.content.decode(), r'<div class="c-package-single">\s*<div>\s*<h2 ')
        self.assertContains(response, '<div class="c-packages c-packages--single">')

    def test_several_packages_put_the_introduction_above(self):
        packages = next(block for block in self.comedy.body if block.block_type == "packages")
        response = self.edit([{"op": "set", "block": packages.id, "path": "lead", "value": "<p>Fixed prices.</p>"}])
        self.assertContains(response, '<div class="c-prose c-packages__lead"><p>Fixed prices.</p></div>')
        self.assertNotContains(response, "c-package-single")


class HeroMockupAndColumnImageTests(SiteTestCase):
    def test_editor_mockups(self):
        from pages.content_ops import apply_changes

        self.assertContains(self.client.get("/comedy/"), '<div class="c-admin__bar">Edit show</div>')
        apply_changes(self.comedy, [{"op": "set", "block": "screenshot_hero", "path": "editor_mockup", "value": "review"}])
        self.comedy.save_revision().publish()
        response = self.client.get("/comedy/")
        self.assertContains(response, '<div class="c-admin__bar">Add review</div>')
        self.assertNotContains(response, "Edit show")

    def test_column_pictures(self):
        from pages.content_ops import apply_changes

        image = self.comedy.body[0].value["screenshot"]
        apply_changes(self.comedy, [{"op": "set", "block": "columns", "path": "columns.0.image",
                                     "value": {"image": image.pk, "alt_text": "A flyer and a phone", "decorative": False}}])
        self.comedy.save_revision().publish()
        response = self.client.get("/comedy/")
        self.assertContains(response, 'class="c-why__image"')
        self.assertContains(response, 'alt="A flyer and a phone"')


class FaqTests(SiteTestCase):
    def test_blank_lines_in_an_answer_start_new_paragraphs(self):
        faq = next(block for block in self.comedy.body if block.block_type == "faq")
        question = faq.value["questions"][0].value
        question.answer = "First paragraph.\r\n\r\nSecond paragraph."
        question.save()
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

    def test_footer_columns_from_site_settings(self):
        response = self.client.get("/")
        self.assertContains(response, '<h2 class="footer__heading">Websites for</h2>')
        self.assertContains(response, '<a href="/edfringe/">Edinburgh Fringe 2027 shows</a>')
        self.assertContains(response, '<a href="/comedy/#quote" class="btn btn-prim footer__cta">Get a quote</a>')
        self.assertContains(self.client.get("/comedy/"), '<a href="/comedy/" aria-current="page">Comedians</a>')

    def test_footer_without_columns_lists_pages_shown_in_menus(self):
        from core.models import SiteSettings

        settings = SiteSettings.objects.get()
        settings.footer_columns = []
        settings.save()
        response = self.client.get("/")
        self.assertContains(response, '<h2 class="footer__heading">Pages</h2>')
        self.assertContains(response, 'href="/comedy/">Comedy</a>')

    def test_footer_and_structured_data_show_kvk_and_vat(self):
        import json

        from core.models import SiteSettings

        SiteSettings.objects.filter().update(kvk_number="12345678", vat_number="NL123456789B01")
        html = self.client.get("/").content.decode()
        self.assertIn('Chamber of Commerce)">KvK</abbr> 12345678</span>', html)
        self.assertIn("<span>VAT (BTW) NL123456789B01</span>", html)
        graph = json.loads(re.search(r'ld\+json">(.*?)</script>', html, re.DOTALL).group(1))["@graph"]
        self.assertEqual(graph[0]["vatID"], "NL123456789B01")
        self.assertEqual(graph[0]["identifier"]["value"], "12345678")
        self.assertIn("- VAT number: NL123456789B01", self.client.get("/llms.txt").content.decode())

    def test_footer_shows_the_location(self):
        from core.models import SiteSettings

        SiteSettings.objects.filter().update(address_locality="Utrecht")
        self.assertContains(self.client.get("/"), "<span>Utrecht, Netherlands</span>")

    def test_company_name_ending_in_a_full_stop(self):
        from core.models import SiteSettings

        SiteSettings.objects.filter().update(company_name="Design by Committee B.V.")
        self.assertContains(self.client.get("/"), "Design by Committee B.V. All rights reserved.")


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

    def test_package_snippet_screens(self):
        from pages.models import Package

        self.assertContains(self.client.get("/admin/snippets/pages/package/"), "Solo")
        response = self.client.get(f"/admin/snippets/pages/package/edit/{Package.objects.get(code='solo').pk}/")
        for field in ("name", "price", "price_is_minimum", "features"):
            self.assertContains(response, f'name="{field}"')

    def test_page_promote_tab(self):
        response = self.client.get(f"/admin/pages/{self.comedy.pk}/edit/")
        self.assertEqual(response.status_code, 200)
        for field in ("noindex", "service_name", "service_audience", "areas_served", "extra_json_ld"):
            self.assertContains(response, f'name="{field}"')


class PackageSnippetTests(SiteTestCase):
    """Packages are written once (Snippets → Packages) and chosen by pages."""

    def test_one_edit_changes_every_place_the_package_appears(self):
        import json

        from pages.models import Package

        solo = Package.objects.get(code="solo")
        solo.price = 525
        solo.features = "Home and gigs pages\nA press page"
        solo.save()
        html = self.client.get("/comedy/").content.decode()
        self.assertIn('<span class="c-package__amount">€525</span>', html)
        self.assertIn("<li>A press page</li>", html)
        graph = json.loads(re.search(r'ld\+json">(.*?)</script>', html, re.DOTALL).group(1))["@graph"]
        offers = {o["name"]: o for o in next(n for n in graph if n["@type"] == "Service")["hasOfferCatalog"]["itemListElement"]}
        self.assertEqual(offers["Solo"]["price"], "525")
        self.assertIn("- Solo (€525 one-off): For comedians; Live in 2–4 weeks; Home and gigs pages; A press page",
                      self.client.get("/llms.txt").content.decode())

    def test_approximate_pounds(self):
        from decimal import Decimal

        from pages.models import Package

        def pounds(price, rate="0.834"):
            return Package(price=Decimal(price), currency="EUR").approximate_pounds(Decimal(rate) if rate else None)

        self.assertEqual(pounds(500), "£420")
        self.assertEqual(pounds(750), "£630")
        self.assertEqual(pounds(1200), "£1,000")
        self.assertEqual(pounds(3500), "£2,900")
        self.assertIsNone(pounds(500, rate=None))
        self.assertIsNone(Package(price=Decimal(500), currency="GBP").approximate_pounds(Decimal("0.834")))

    def test_pounds_follow_the_section_toggle_and_the_site_rate(self):
        from core.models import SiteSettings
        from pages.content_ops import apply_changes

        packages = next(block for block in self.comedy.body if block.block_type == "packages")
        apply_changes(self.comedy, [{"op": "set", "block": packages.id, "path": "show_pounds", "value": True}])
        self.comedy.save_revision().publish()
        self.assertContains(self.client.get("/comedy/"), '<span class="c-package__approx">(about £410)</span>')  # €495
        SiteSettings.objects.filter().update(pounds_per_euro=None)
        self.assertNotContains(self.client.get("/comedy/"), "c-package__approx")

    def test_page_specific_featured_badge_and_button(self):
        response = self.client.get("/comedy/")
        self.assertContains(response, '<p class="c-package__badge">Best for Fringe runs</p>')
        self.assertContains(response, ">Choose Solo</a>")


class PricePlaceholderTests(SiteTestCase):
    """{solo.price} and {solo.pounds} in page copy show the package's current price."""

    def setUp(self):
        self.comedy.seo_title = "Comedian websites from {solo.price} | Committee"
        self.comedy.search_description = "Fixed prices from {solo.price} (about {solo.pounds})."
        faq = next(block for block in self.comedy.body if block.block_type == "faq")
        question = faq.value["questions"][0].value
        question.answer = "Solo is {solo.price}, Venue from {venue.price}. {nope.price} stays."
        question.save()
        self.comedy.save_revision().publish()

    def test_copy_meta_structured_data_and_llms_txt(self):
        html = self.client.get("/comedy/").content.decode()
        self.assertIn("<title>Comedian websites from €495 | Committee</title>", html)
        self.assertIn('<meta name="description" content="Fixed prices from €495 (about £410).">', html)
        self.assertIn("Solo is €495, Venue from €1,950. {nope.price} stays.", html)
        self.assertIn('"description":"Fixed prices from €495 (about £410)."', html)  # JSON-LD
        self.assertNotIn("{solo.", html)
        self.assertIn("Fixed prices from €495 (about £410).", self.client.get("/llms.txt").content.decode())

    def test_a_package_edit_updates_the_copy(self):
        from pages.models import Package

        Package.objects.filter(code="solo").update(price=550)
        self.assertContains(self.client.get("/comedy/"), "<title>Comedian websites from €550 | Committee</title>")

    def test_admin_keeps_the_placeholders(self):
        from django.contrib.auth import get_user_model

        self.client.force_login(get_user_model().objects.create_superuser("editor", "e@example.com", "x"))
        edit = self.client.get(f"/admin/pages/{self.comedy.pk}/edit/").content.decode()
        self.assertIn("Comedian websites from {solo.price} | Committee", edit)

    def test_etag_matches_the_filled_page(self):
        first = self.client.get("/comedy/")
        again = self.client.get("/comedy/", HTTP_IF_NONE_MATCH=first["ETag"])
        self.assertEqual(again.status_code, 304)
        from pages.models import Package

        Package.objects.filter(code="solo").update(price=560)
        self.assertEqual(self.client.get("/comedy/", HTTP_IF_NONE_MATCH=first["ETag"]).status_code, 200)


class SharedComponentTests(SiteTestCase):
    """Case studies, questions and whole sections are written once and chosen by pages."""

    def make_shared(self, block_type):
        """Move the comedy page's section of `block_type` into a Shared section, and place that on the page."""
        import json

        from pages.content_ops import stream_data
        from pages.models import SharedSection

        raw = next(block for block in stream_data(self.comedy.body) if block["type"] == block_type)
        section = SharedSection.objects.create(name=f"Shared {block_type}", body=json.dumps([raw]))
        body = [b if b["type"] != block_type else {"type": "shared_section", "value": section.pk, "id": b["id"]}
                for b in stream_data(self.comedy.body)]
        self.comedy.body = json.dumps(body)
        self.comedy.save_revision().publish()
        return section

    def test_shared_section_renders_and_one_edit_changes_it(self):
        section = self.make_shared("steps")
        self.assertContains(self.client.get("/comedy/"), "How it works")
        data = section.body.raw_data[0]
        data["value"]["heading"] = "How we work"
        section.body = [dict(data)]
        section.save()
        self.assertContains(self.client.get("/comedy/"), ">How we work</h2>")

    def test_faq_in_a_shared_section_is_still_structured_data(self):
        import json

        self.make_shared("faq")
        html = self.client.get("/comedy/").content.decode()
        graph = json.loads(re.search(r'ld\+json">(.*?)</script>', html, re.DOTALL).group(1))["@graph"]
        webpage = next(node for node in graph if node["@id"].endswith("#webpage"))
        self.assertEqual(webpage["@type"], ["WebPage", "FAQPage"])

    def test_quote_form_in_a_shared_section_still_takes_enquiries(self):
        from django.core import mail

        from leads.models import FormSubmission
        from leads.tests import ENQUIRY, JSON

        self.make_shared("enquiry_form")
        self.assertEqual(self.comedy.form_names(), {"comedy-enquiry"})
        with self.settings(LEAD_RATE_LIMIT=100):
            response = self.client.post("/comedy/", ENQUIRY, **JSON)
        self.assertEqual(response.json(), {"ok": True})
        self.assertEqual(FormSubmission.objects.get().form_name, "comedy-enquiry")
        self.assertLessEqual(len(mail.outbox), 1)

    def test_shared_question_and_one_off_question(self):
        import json

        from pages.content_ops import apply_changes
        from pages.models import Question

        faq = next(block for block in self.comedy.body if block.block_type == "faq")
        apply_changes(self.comedy, [{"op": "set", "block": faq.id, "path": "questions", "value": [
            {"type": "question", "value": Question.objects.create(question="Shared?", answer="Yes, shared.").pk},
            {"type": "custom", "value": {"question": "Only here?", "answer": "Yes, one-off."}},
        ]}])
        self.comedy.save_revision().publish()
        html = self.client.get("/comedy/").content.decode()
        self.assertIn("<summary>Shared?</summary>", html)
        self.assertIn("<summary>Only here?</summary>", html)
        graph = json.loads(re.search(r'ld\+json">(.*?)</script>', html, re.DOTALL).group(1))["@graph"]
        names = [q["name"] for q in next(n for n in graph if n["@id"].endswith("#webpage"))["mainEntity"]]
        self.assertEqual(names, ["Shared?", "Only here?"])

    def test_snippet_screens(self):
        from django.contrib.auth import get_user_model

        self.client.force_login(get_user_model().objects.create_superuser("editor", "e@example.com", "x"))
        for model in ("casestudy", "question", "sharedsection"):
            self.assertEqual(self.client.get(f"/admin/snippets/pages/{model}/").status_code, 200, model)
            self.assertEqual(self.client.get(f"/admin/snippets/pages/{model}/add/").status_code, 200, model)
