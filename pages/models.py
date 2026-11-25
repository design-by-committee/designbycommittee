import json
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from core.cache import cache_privately, cache_publicly, is_public_request

from .blocks import AGENCY_BLOCKS, FORM_BLOCK_TYPES, SECTION_BLOCKS, LinkBlock


CURRENCY_SYMBOLS = {"EUR": "€", "GBP": "£", "USD": "$"}


def format_amount(amount, currency="EUR"):
    """€1,200 or €1,200.50: whole amounts without decimals, thousands separated with commas."""
    amount = Decimal(amount)
    text = f"{amount:,.0f}" if amount == amount.to_integral_value() else f"{amount:,.2f}"
    return f"{CURRENCY_SYMBOLS.get(currency, currency + ' ')}{text}"


@register_snippet
class Package(index.Indexed, models.Model):
    """A pricing package, written once and chosen in the "Packages and prices" sections of any page.

    Its price feeds the cards, the pages' structured data (offers) and llms.txt, so a price change shows everywhere.
    """

    class Code(models.TextChoices):
        SOLO = "solo", "solo (Performer)"
        FRINGE = "fringe", "fringe (Performer)"
        SHOW = "show", "show (Showrunner)"
        VENUE = "venue", "venue (Venue owner)"

    class Currency(models.TextChoices):
        EUR = "EUR", "Euro (€)"
        GBP = "GBP", "Pound (£)"
        USD = "USD", "Dollar ($)"

    name = models.CharField(max_length=60, help_text="E.g. Solo")
    code = models.CharField(
        max_length=20,
        choices=Code.choices,
        help_text=(
            "The quote form’s “I’m a…” option that this package’s button selects. Also the name for prices in page "
            "copy: {solo.price} shows the price (€500) and {solo.pounds} the approximate pounds (£420)."
        ),
    )
    audience = models.CharField("Who it’s for", max_length=255, help_text="E.g. For comedians")
    price = models.DecimalField(max_digits=9, decimal_places=2, help_text="The amount only, e.g. 1200")
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.EUR)
    price_is_minimum = models.BooleanField(
        "Starting price",
        default=False,
        help_text="Shows “from” before the price, for packages whose final price depends on the project.",
    )
    price_suffix = models.CharField(
        max_length=60, blank=True, default="one-time fee", help_text="Shown after the price, e.g. one-time fee"
    )
    timeframe = models.CharField(max_length=60, blank=True, help_text="E.g. Live in 2–4 weeks")
    features = models.TextField(help_text="What’s included, one per line.")

    panels = [
        MultiFieldPanel([FieldPanel("name"), FieldPanel("audience"), FieldPanel("code")], heading="Package"),
        MultiFieldPanel(
            [FieldPanel("price"), FieldPanel("currency"), FieldPanel("price_is_minimum"), FieldPanel("price_suffix")],
            heading="Price",
        ),
        FieldPanel("timeframe"),
        FieldPanel("features"),
    ]

    search_fields = [index.SearchField("name"), index.SearchField("audience"), index.AutocompleteField("name")]

    class Meta:
        ordering = ["price", "name"]

    def __str__(self):
        return f"{self.name}: {'from ' if self.price_is_minimum else ''}{self.price_display}"

    @property
    def price_display(self):
        return format_amount(self.price, self.currency)

    @property
    def feature_list(self):
        return [line.strip() for line in self.features.splitlines() if line.strip()]

    @property
    def offer_price(self):
        """The price for structured data: "1200", or "1200.50"."""
        return str(self.price.normalize()) if self.price != self.price.to_integral_value() else str(int(self.price))

    def approximate_pounds(self, pounds_per_euro):
        """"£1,000" for a euro price, rounded to £10 under £1,000 and to £100 above; None if there's no rate."""
        if self.currency != self.Currency.EUR or not pounds_per_euro:
            return None
        pounds = Decimal(self.price) * Decimal(pounds_per_euro)
        step = Decimal(100) if pounds >= 1000 else Decimal(10)
        return format_amount((pounds / step).quantize(Decimal(1), rounding=ROUND_HALF_UP) * step, "GBP")


def validate_json_ld(value):
    """Extra structured data must be a JSON object (or a list of them), as it's added to the page's @graph."""
    try:
        data = json.loads(value)
    except ValueError as error:
        raise ValidationError(f"This isn’t valid JSON: {error}") from error
    items = data if isinstance(data, list) else [data]
    if not items or not all(isinstance(item, dict) for item in items):
        raise ValidationError("Enter a JSON object such as {\"@type\": \"Event\", …}, or a list of them.")


class BasePage(Page):
    """Fields and behaviour shared by every page: search and social tags, structured data and lead form handling."""

    noindex = models.BooleanField(
        "Hide from search engines",
        default=False,
        help_text="Asks search engines not to list this page, and leaves it out of the sitemap and llms.txt.",
    )

    og_title = models.CharField(
        "Social title",
        max_length=255,
        blank=True,
        help_text="Title when the page is shared on social media. Defaults to the page title.",
    )
    og_description = models.TextField(
        "Social description",
        blank=True,
        help_text="Description when the page is shared on social media. Defaults to the search description.",
    )
    og_image = models.ForeignKey(
        "wagtailimages.Image",
        verbose_name="Social image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Image when the page is shared on social media. Defaults to the site’s social image.",
    )

    service_name = models.CharField(
        "Service name",
        max_length=255,
        blank=True,
        help_text=(
            "What this page sells, e.g. Website design for comedians, comedy shows and venues. Describes the "
            "page’s packages to search engines. Defaults to the title tag."
        ),
    )
    service_audience = models.CharField(
        "Who it’s for",
        max_length=255,
        blank=True,
        help_text="E.g. Comedians, comedy shows and comedy venues.",
    )
    areas_served = models.TextField(
        blank=True,
        help_text="Countries or regions, one per line. Leave empty to use the ones in Site settings.",
    )
    extra_json_ld = models.TextField(
        "Extra structured data",
        blank=True,
        validators=[validate_json_ld],
        help_text=(
            "Optional JSON-LD added to the page’s structured data, e.g. {\"@type\": \"Event\", …}. "
            "Organisation, web page, FAQ, breadcrumb and package/price data are already generated from the page "
            "and Site settings."
        ),
    )

    # Language of the page's copy, for <html lang>
    html_lang = "en"

    promote_panels = Page.promote_panels + [
        FieldPanel("noindex"),
        MultiFieldPanel(
            [FieldPanel("og_title"), FieldPanel("og_description"), FieldPanel("og_image")],
            heading="Social sharing",
        ),
        MultiFieldPanel(
            [
                FieldPanel("service_name"),
                FieldPanel("service_audience"),
                FieldPanel("areas_served"),
                FieldPanel("extra_json_ld"),
            ],
            heading="Structured data (for search engines and AI assistants)",
        ),
    ]

    search_fields = Page.search_fields + [index.SearchField("body")]

    class Meta:
        abstract = True

    def social_image(self):
        """The page's social image, or the site's default one."""
        if self.og_image:
            return self.og_image
        from core.models import SiteSettings

        site = self.get_site()
        return SiteSettings.for_site(site).default_social_image if site else None

    def get_sitemap_urls(self, request=None):
        return [] if self.noindex else super().get_sitemap_urls(request)

    def is_indexable(self):
        """Live, public and not hidden from search engines."""
        return self.live and not self.noindex and not self.get_view_restrictions().exists()

    def blocks_of_type(self, block_type):
        return [block.value for block in self.body if block.block_type == block_type]

    def packages(self):
        """The packages chosen in this page's "Packages and prices" sections, in order, without repeats."""
        found = []
        for block in self.blocks_of_type("packages"):
            for item in block["packages"]:
                package = item["package"]
                if package is not None and package not in found:
                    found.append(package)
        return found

    def form_names(self):
        """Names of the lead forms on this page, e.g. {"comedy-enquiry"}."""
        return {FORM_BLOCK_TYPES[block.block_type] for block in self.body if block.block_type in FORM_BLOCK_TYPES}

    def serve(self, request, *args, **kwargs):
        # The page's lead forms post back to the page itself, like they did with Netlify Forms.
        if request.method == "POST" and "form-name" in request.POST:
            from leads.views import handle_submission

            return handle_submission(request, self)
        response = super().serve(request, *args, **kwargs)
        if is_public_request(request) and not self.get_view_restrictions().exists():
            response.render()  # TemplateResponse: render now so the cache headers see the final response
            return cache_publicly(response)
        return cache_privately(response)


class HomePage(BasePage):
    """The home page, in the original agency design."""

    body = StreamField(AGENCY_BLOCKS, blank=True, use_json_field=True)

    content_panels = Page.content_panels + [FieldPanel("body")]

    parent_page_types = ["wagtailcore.Page"]
    subpage_types = ["pages.LandingPage"]
    max_count = 1

    template = "pages/home_page.html"


class LandingPage(BasePage):
    """A landing page built from full-width sections, such as /comedy/."""

    header_links = StreamField(
        [("link", LinkBlock(label="Link"))],
        blank=True,
        use_json_field=True,
        verbose_name="Header links",
        help_text="Links in the page header, usually to sections on this page (#packages).",
    )
    header_button = StreamField(
        [("button", LinkBlock())],
        blank=True,
        max_num=1,
        use_json_field=True,
        verbose_name="Header button",
    )
    body = StreamField(SECTION_BLOCKS, blank=True, use_json_field=True)

    html_lang = "en-GB"

    content_panels = Page.content_panels + [
        MultiFieldPanel([FieldPanel("header_links"), FieldPanel("header_button")], heading="Header"),
        FieldPanel("body"),
    ]

    parent_page_types = ["pages.HomePage"]
    subpage_types = []

    template = "pages/landing_page.html"
