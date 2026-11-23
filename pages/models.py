from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail.search import index

from .blocks import AGENCY_BLOCKS, FORM_BLOCK_TYPES, SECTION_BLOCKS, LinkBlock


class BasePage(Page):
    """Fields and behaviour shared by every page: social sharing tags and lead form handling."""

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

    # Language of the page's copy, for <html lang>
    html_lang = "en"

    promote_panels = Page.promote_panels + [
        MultiFieldPanel(
            [FieldPanel("og_title"), FieldPanel("og_description"), FieldPanel("og_image")],
            heading="Social sharing",
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

    def form_names(self):
        """Names of the lead forms on this page, e.g. {"comedy-enquiry"}."""
        return {FORM_BLOCK_TYPES[block.block_type] for block in self.body if block.block_type in FORM_BLOCK_TYPES}

    def serve(self, request, *args, **kwargs):
        # The page's lead forms post back to the page itself, like they did with Netlify Forms.
        if request.method == "POST" and "form-name" in request.POST:
            from leads.views import handle_submission

            return handle_submission(request, self)
        return super().serve(request, *args, **kwargs)


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
