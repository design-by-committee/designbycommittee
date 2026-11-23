from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting
from wagtail.search import index
from wagtail.snippets.models import register_snippet


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

    panels = [
        FieldPanel("company_name"),
        FieldPanel("lead_notification_email"),
        FieldPanel("default_social_image"),
    ]

    class Meta:
        verbose_name = "Site settings"


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
