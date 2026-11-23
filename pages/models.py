from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page


class LandingPage(Page):
    """A page built from design sections. Used for the home page, /comedy/ and future landing pages.

    Phase 1 stub: the section blocks, theme and header options arrive in Phase 2.
    """

    body = StreamField(
        [("rich_text", blocks.RichTextBlock(label="Text"))],
        blank=True,
        use_json_field=True,
    )

    content_panels = Page.content_panels + [FieldPanel("body")]

    template = "pages/landing_page.html"
