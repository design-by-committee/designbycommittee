from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, ObjectList, TabbedInterface
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting
from wagtail.fields import StreamField
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from pages.blocks import FooterColumnBlock


def link(text, url):
    return {"text": text, "url": url}


DEFAULT_FOOTER_COLUMNS = [
    {"type": "column", "value": {"heading": "Websites for", "links": [
        link("Comedians", "/comedy/"),
        link("Edinburgh Fringe 2027 shows", "/edfringe/"),
        link("Comedy clubs and venues", "/comedy-venue-websites/"),
        link("English-language comedy in Europe", "/english-comedy-europe/"),
    ]}},
    {"type": "column", "value": {"heading": "Resources", "links": [
        link("Comedian website guide", "/comedian-website-guide/"),
        link("Packages and prices", "/comedy/#packages"),
        link("Questions", "/comedy/#faq"),
    ]}},
    {"type": "column", "value": {"heading": "Committee", "links": [
        link("About us", "/comedy/#about"),
        link("Landing page design", "/"),
        link("Andres Lucero on LinkedIn", "https://www.linkedin.com/in/andreslucero/"),
    ]}},
]


@register_setting(icon="cog")
class SiteSettings(BaseSiteSetting):
    company_name = models.CharField(
        max_length=255,
        default="Design by Committee BV",
        help_text="Shown in the footer copyright line.",
    )
    lead_notification_email = models.EmailField(
        blank=True,
        help_text="Form submissions are emailed here. Leave empty to only keep them under Leads in the admin.",
    )
    default_social_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Used when a page has no social image of its own.",
    )

    # Search engines and AI assistants: the organisation behind the site (JSON-LD on every page, llms.txt)
    site_name = models.CharField(
        max_length=255,
        default="Design by Committee",
        help_text="The site’s name in search results, social previews (og:site_name) and structured data.",
    )
    alternate_name = models.CharField(
        "Short name",
        max_length=255,
        blank=True,
        default="Committee",
        help_text="Another name people use for the business, e.g. Committee. Optional.",
    )
    organisation_type = models.CharField(
        max_length=40,
        choices=[
            ("ProfessionalService", "Professional service (a business that serves clients remotely or on site)"),
            ("Organization", "Organisation"),
        ],
        default="ProfessionalService",
        help_text="How search engines classify the business (schema.org type).",
    )
    organisation_description = models.TextField(
        "Description",
        blank=True,
        default=(
            "Design by Committee is a web design studio that builds custom websites for comedians, comedy shows and "
            "comedy venues on WordPress or Wagtail, with fixed prices and sites live in weeks, as well as "
            "conversion-focused landing pages. It works with clients in the UK and across Europe, including shows "
            "going to the Edinburgh Festival Fringe."
        ),
        help_text=(
            "One or two plain sentences about what the business does and for whom. Search engines and AI assistants "
            "use it to describe you, and it opens llms.txt."
        ),
    )
    logo = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Square logo, at least 112×112 pixels (PNG or JPG). Used by search engines.",
    )
    public_email = models.EmailField(
        "Public contact email",
        blank=True,
        help_text="A contact address search engines and AI assistants may show. Leave empty to keep it off the site.",
    )
    founder_name = models.CharField(max_length=255, blank=True, default="Andres Lucero")
    founder_url = models.URLField(
        "Founder profile",
        blank=True,
        default="https://www.linkedin.com/in/andreslucero/",
        help_text="E.g. the founder’s LinkedIn profile.",
    )
    address_locality = models.CharField(
        "Town or city",
        max_length=255,
        blank=True,
        help_text="Where the business is based, e.g. Utrecht. Optional; no street address is shown.",
    )
    address_country = models.CharField(
        "Country",
        max_length=100,
        blank=True,
        default="Netherlands",
        help_text="E.g. Netherlands or United Kingdom.",
    )
    areas_served = models.TextField(
        blank=True,
        default="United Kingdom\nIreland\nEurope",
        help_text="Countries or regions you work in, one per line. Pages can override this.",
    )
    knows_about = models.TextField(
        "Specialities",
        blank=True,
        default=(
            "Website design for comedians\nComedy show websites\nComedy venue websites\nEdinburgh Festival Fringe\n"
            "WordPress\nWagtail\nLanding page design\nConversion rate optimisation"
        ),
        help_text="Topics the business is expert in, one per line.",
    )
    same_as = models.TextField(
        "Profiles elsewhere",
        blank=True,
        help_text=(
            "Addresses of the business’s own profiles on other sites (LinkedIn company page, Instagram, Google "
            "Business Profile, directories), one per line. Helps search engines connect them to this site."
        ),
    )
    google_site_verification = models.CharField(
        max_length=255,
        blank=True,
        help_text="The content of Google Search Console’s HTML tag, e.g. abc123… (only the code, not the whole tag).",
    )
    bing_site_verification = models.CharField(
        max_length=255,
        blank=True,
        help_text="The content of Bing Webmaster Tools’ msvalidate.01 meta tag (only the code).",
    )
    llms_txt_details = models.TextField(
        "Extra llms.txt text",
        blank=True,
        help_text=(
            "Optional facts for AI assistants, added to /llms.txt after the description (Markdown). E.g. what "
            "you don’t do, who you’ve worked with, how to get a quote."
        ),
    )

    # Footer on every page
    footer_text = models.TextField(
        "Footer introduction",
        blank=True,
        default=(
            "A web design studio in Utrecht, the Netherlands. We build websites for comedians, comedy shows and venues "
            "across the UK and Europe."
        ),
        help_text="One or two sentences under the logo.",
    )
    footer_button_text = models.CharField("Footer button text", max_length=60, blank=True, default="Get a quote")
    footer_button_link = models.CharField(
        "Footer button link",
        max_length=255,
        blank=True,
        default="/comedy/#quote",
        help_text="A path (/comedy/#quote) or a full address. Leave the text or link empty to hide the button.",
    )
    footer_columns = StreamField(
        [("column", FooterColumnBlock())],
        blank=True,
        default=DEFAULT_FOOTER_COLUMNS,
        use_json_field=True,
        verbose_name="Footer link columns",
        help_text="Titled groups of links, shown side by side. Three columns fit best.",
    )

    edit_handler = TabbedInterface(
        [
            ObjectList(
                [
                    FieldPanel("company_name"),
                    FieldPanel("lead_notification_email"),
                    FieldPanel("default_social_image"),
                ],
                heading="General",
            ),
            ObjectList(
                [
                    MultiFieldPanel(
                        [
                            FieldPanel("site_name"),
                            FieldPanel("alternate_name"),
                            FieldPanel("organisation_type"),
                            FieldPanel("organisation_description"),
                            FieldPanel("logo"),
                            FieldPanel("public_email"),
                        ],
                        heading="Organisation",
                    ),
                    MultiFieldPanel(
                        [FieldPanel("founder_name"), FieldPanel("founder_url")],
                        heading="Founder",
                    ),
                    MultiFieldPanel(
                        [
                            FieldPanel("address_locality"),
                            FieldPanel("address_country"),
                            FieldPanel("areas_served"),
                        ],
                        heading="Location",
                    ),
                    FieldPanel("knows_about"),
                    FieldPanel("same_as"),
                ],
                heading="Search & AI",
            ),
            ObjectList(
                [
                    FieldPanel("footer_text"),
                    MultiFieldPanel(
                        [FieldPanel("footer_button_text"), FieldPanel("footer_button_link")],
                        heading="Button",
                    ),
                    FieldPanel("footer_columns"),
                ],
                heading="Footer",
            ),
            ObjectList(
                [
                    FieldPanel("google_site_verification"),
                    FieldPanel("bing_site_verification"),
                    FieldPanel("llms_txt_details"),
                ],
                heading="Verification & llms.txt",
            ),
        ]
    )

    class Meta:
        verbose_name = "Site settings"

    @staticmethod
    def lines(text):
        """Non-empty lines of a one-per-line field."""
        return [line.strip() for line in (text or "").splitlines() if line.strip()]


@register_snippet
class Testimonial(index.Indexed, models.Model):
    """A client quote, written once and used in the home page carousel and in quote cards."""

    class CardColour(models.TextChoices):
        SOFT_PINK = "soft-pink", "Soft pink"
        TURQUOISE = "turquoise", "Turquoise"
        LIGHT_GREY = "light-grey", "Light grey"

    quote = models.TextField(help_text="The full quote, without quotation marks.")
    short_quote = models.TextField(
        blank=True,
        help_text="Optional shorter version for quote cards on landing pages. Without quotation marks.",
    )
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=255, help_text="E.g. Co-Founder")
    company = models.CharField(max_length=255)
    logo = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Square logo or photo, shown at 60×60. SVG works best.",
    )
    card_colour = models.CharField(
        max_length=20,
        choices=CardColour.choices,
        default=CardColour.SOFT_PINK,
        help_text="Background of the name card in the home page carousel.",
    )

    panels = [
        FieldPanel("quote"),
        FieldPanel("short_quote"),
        MultiFieldPanel([FieldPanel("name"), FieldPanel("role"), FieldPanel("company")], heading="Who said it"),
        FieldPanel("logo"),
        FieldPanel("card_colour"),
    ]

    search_fields = [
        index.SearchField("name"),
        index.SearchField("company"),
        index.SearchField("quote"),
        index.AutocompleteField("name"),
    ]

    class Meta:
        ordering = ["company"]

    def __str__(self):
        return f"{self.name}, {self.company}"

    @property
    def card_quote(self):
        return self.short_quote or self.quote
