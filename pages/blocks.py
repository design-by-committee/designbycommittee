"""StreamField blocks for the two designs on the site.

- Agency blocks build the home page: they render as columns of the home page's 12-column grid (small.css / medium.css).
- Section blocks build landing pages such as /comedy/: each renders as a full-width <section> (comedy.css).

Block templates keep the original HTML structure and class names, so the stylesheets work unchanged.
"""

from django.core.validators import RegexValidator
from wagtail import blocks
from wagtail.images.blocks import ImageBlock
from wagtail.snippets.blocks import SnippetChooserBlock

# Rich text features for headings and lead paragraphs: the design's emphasis styles only (see core/wagtail_hooks.py)
EMPHASIS = ["text-bold", "text-extrabold"]

anchor_validator = RegexValidator(
    r"^[a-z0-9][a-z0-9-]*$",
    "Use lowercase letters, numbers and hyphens only, e.g. packages",
)


def anchor_block(default=""):
    return blocks.CharBlock(
        required=False,
        default=default,
        max_length=50,
        validators=[anchor_validator],
        label="Anchor",
        help_text="Lets links jump to this section, e.g. “packages” for #packages. Optional.",
    )


LINK_HELP = "A full address (https://…), a path (/comedy/) or a section on this page (#quote)."


class LinkBlock(blocks.StructBlock):
    text = blocks.CharBlock()
    url = blocks.CharBlock(label="Link", help_text=LINK_HELP)

    class Meta:
        icon = "link"
        label = "Button"


class OptionalLinkBlock(LinkBlock):
    text = blocks.CharBlock(required=False)
    url = blocks.CharBlock(required=False, label="Link", help_text=LINK_HELP)

    class Meta:
        icon = "link"
        label = "Link (optional)"


class ExternalLinkBlock(OptionalLinkBlock):
    new_tab = blocks.BooleanBlock(required=False, label="Open in a new tab")


# ---------------------------------------------------------------------------------------------------------------------
# Agency (home page) blocks
# ---------------------------------------------------------------------------------------------------------------------


class AgencyHeroBlock(blocks.StructBlock):
    heading = blocks.RichTextBlock(features=EMPHASIS)
    lead = blocks.RichTextBlock(features=EMPHASIS)
    button = LinkBlock()

    class Meta:
        icon = "title"
        label = "Hero with moped illustration"
        template = "blocks/agency/hero.html"


class AgencyIntroBlock(blocks.StructBlock):
    anchor = anchor_block()
    heading = blocks.RichTextBlock(features=EMPHASIS)
    lead = blocks.RichTextBlock(features=EMPHASIS)
    link = ExternalLinkBlock(help_text="Shown at the end of the text with an arrow.")

    class Meta:
        icon = "doc-full"
        label = "Centred heading and text"
        template = "blocks/agency/intro.html"


class FeatureRowBlock(blocks.StructBlock):
    ILLUSTRATIONS = [
        ("detective", "Detective piggy"),
        ("champion", "Champion piggy"),
        ("laptop", "Laptop piggy"),
    ]
    # Static files in static/img/ with their intrinsic sizes
    ILLUSTRATION_SIZES = {"detective": (303, 385), "champion": (385, 391), "laptop": (384, 367)}

    heading = blocks.CharBlock()
    illustration = blocks.ChoiceBlock(choices=ILLUSTRATIONS)
    illustration_side = blocks.ChoiceBlock(
        choices=[("left", "Left"), ("right", "Right")],
        default="left",
        help_text="On large screens. On phones the illustration always sits under the heading.",
    )
    lead = blocks.RichTextBlock(features=EMPHASIS)
    points = blocks.ListBlock(blocks.CharBlock(label="Point"), label="Bullet points")

    class Meta:
        icon = "image"
        label = "Illustrated feature"
        template = "blocks/agency/feature_row.html"

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context)
        name = value["illustration"]
        width, height = self.ILLUSTRATION_SIZES[name]
        context["illustration"] = {
            "name": name,
            "src": f"img/{name}.png",
            "alt": dict(self.ILLUSTRATIONS)[name],
            "width": width,
            "height": height,
        }
        return context


class CentredButtonBlock(blocks.StructBlock):
    button = LinkBlock()

    class Meta:
        icon = "link"
        label = "Centred button"
        template = "blocks/agency/button.html"


class TestimonialCarouselBlock(blocks.StructBlock):
    testimonials = blocks.ListBlock(SnippetChooserBlock("core.Testimonial", label="Testimonial"))

    class Meta:
        icon = "openquote"
        label = "Testimonial carousel"
        template = "blocks/agency/testimonials.html"


class AssessmentFormBlock(blocks.StructBlock):
    anchor = anchor_block(default="contact")
    heading = blocks.RichTextBlock(features=EMPHASIS)
    lead = blocks.RichTextBlock(features=EMPHASIS)
    thanks_text = blocks.TextBlock(label="Thank-you message")

    class Meta:
        icon = "form"
        label = "Landing page assessment form"
        template = "blocks/agency/assessment_form.html"

    def get_context(self, value, parent_context=None):
        from leads.forms import ASSESSMENT_INTERESTS, AssessmentForm

        context = super().get_context(value, parent_context)
        context["form_name"] = AssessmentForm.form_name
        context["interests"] = ASSESSMENT_INTERESTS
        return context


AGENCY_BLOCKS = [
    ("hero", AgencyHeroBlock()),
    ("intro", AgencyIntroBlock()),
    ("feature", FeatureRowBlock()),
    ("button", CentredButtonBlock()),
    ("testimonials", TestimonialCarouselBlock()),
    ("assessment_form", AssessmentFormBlock()),
]


# ---------------------------------------------------------------------------------------------------------------------
# Section (landing page) blocks
# ---------------------------------------------------------------------------------------------------------------------

BACKGROUNDS = [("", "Light"), ("paper", "Paper (warm off-white)"), ("dark", "Dark")]
CARD_COLOURS = [("pink", "Pink"), ("teal", "Teal"), ("blue", "Blue")]


class SectionBlock(blocks.StructBlock):
    """Fields shared by every landing page section."""

    anchor = anchor_block()
    background = blocks.ChoiceBlock(choices=BACKGROUNDS, default="", required=False)
    heading = blocks.CharBlock()

    def get_context(self, value, parent_context=None):
        """Adds `background_class` and `title_id` (for aria-labelledby) to every section template."""
        context = super().get_context(value, parent_context)
        block_id = str((parent_context or {}).get("block_id") or "")
        section_id = value.get("anchor") or f"section-{block_id[:8]}"
        context["title_id"] = f"{section_id}-title"
        context["background_class"] = {"paper": "c-paper", "dark": "c-dark"}.get(value.get("background") or "", "")
        return context


class ScreenshotHeroBlock(blocks.StructBlock):
    heading = blocks.CharBlock()
    lead = blocks.TextBlock()
    primary_button = LinkBlock(label="Main button")
    secondary_button = OptionalLinkBlock(label="Second button (optional)")
    proof = blocks.CharBlock(required=False, label="Small print under the buttons")
    screenshot = ImageBlock(help_text="Shown in a browser frame. About 1120 pixels wide works best.")
    screenshot_address = blocks.CharBlock(required=False, label="Address shown in the browser frame")
    show_editor_mockup = blocks.BooleanBlock(
        required=False,
        default=True,
        label="Show the “Edit show” editor mockup next to the screenshot",
    )
    caption = blocks.CharBlock(required=False)

    class Meta:
        icon = "title"
        label = "Hero with screenshot"
        template = "blocks/sections/screenshot_hero.html"


class CardBlock(blocks.StructBlock):
    title = blocks.CharBlock()
    meta = blocks.CharBlock(required=False, help_text="Small line under the title (used in the “work” layout).")
    text = blocks.TextBlock()
    colour = blocks.ChoiceBlock(choices=CARD_COLOURS, default="pink")

    class Meta:
        icon = "doc-full"
        label = "Card"


class CardsBlock(SectionBlock):
    layout = blocks.ChoiceBlock(
        choices=[("cards", "Cards (short text)"), ("work", "Case studies (title, meta line, longer text)")],
        default="cards",
    )
    cards = blocks.ListBlock(CardBlock())
    testimonial = SnippetChooserBlock(
        "core.Testimonial",
        required=False,
        help_text="Optional quote card under the cards. Uses the testimonial’s short quote if it has one.",
    )

    class Meta:
        icon = "table"
        label = "Coloured cards"
        template = "blocks/sections/cards.html"


class ColumnBlock(blocks.StructBlock):
    title = blocks.CharBlock()
    text = blocks.TextBlock()
    link = OptionalLinkBlock()


class ColumnsBlock(SectionBlock):
    columns = blocks.ListBlock(ColumnBlock())

    class Meta:
        icon = "list-ul"
        label = "Columns"
        template = "blocks/sections/columns.html"


class TimelineStepBlock(blocks.StructBlock):
    when = blocks.CharBlock()
    what = blocks.TextBlock()


class TimelineBlock(SectionBlock):
    lead = blocks.TextBlock(required=False)
    timeline = blocks.ListBlock(TimelineStepBlock())
    panel_heading = blocks.CharBlock(label="Checklist panel heading")
    panel_items = blocks.ListBlock(blocks.CharBlock(label="Item"), label="Checklist")
    panel_button = LinkBlock(label="Checklist panel button")
    panel_button_package = blocks.CharBlock(
        required=False,
        label="Package the panel button preselects",
        help_text="The package code in the quote form, e.g. solo, show or venue. Optional.",
    )
    footnote = blocks.TextBlock(required=False)

    class Meta:
        icon = "date"
        label = "Timeline with checklist"
        template = "blocks/sections/timeline.html"


class StepBlock(blocks.StructBlock):
    title = blocks.CharBlock()
    text = blocks.TextBlock()


class StepsBlock(SectionBlock):
    lead = blocks.TextBlock(required=False)
    steps = blocks.ListBlock(StepBlock())

    class Meta:
        icon = "list-ol"
        label = "Numbered steps"
        template = "blocks/sections/steps.html"


class PackageBlock(blocks.StructBlock):
    name = blocks.CharBlock()
    code = blocks.ChoiceBlock(
        choices=[("solo", "solo"), ("show", "show"), ("venue", "venue")],
        help_text="Which option the quote form preselects when someone clicks this package’s button.",
    )
    audience = blocks.CharBlock(help_text="E.g. For comedians")
    price_prefix = blocks.CharBlock(required=False, help_text="E.g. from")
    price = blocks.CharBlock(help_text="E.g. €495")
    price_suffix = blocks.CharBlock(required=False, help_text="E.g. one-off")
    timeframe = blocks.CharBlock(required=False, help_text="E.g. Live in 2–4 weeks")
    features = blocks.ListBlock(blocks.CharBlock(label="Feature"))
    button_text = blocks.CharBlock()
    button_link = blocks.CharBlock(default="#quote", help_text="Usually the quote form’s anchor, e.g. #quote")
    featured = blocks.BooleanBlock(required=False, help_text="Highlight this package (dark card).")
    badge = blocks.CharBlock(required=False, help_text="Label above a featured package, e.g. Best for Fringe runs")

    class Meta:
        icon = "tag"
        label = "Package"


class PackagesBlock(SectionBlock):
    packages = blocks.ListBlock(PackageBlock())
    fine_print = blocks.TextBlock(required=False)

    class Meta:
        icon = "tag"
        label = "Packages and prices"
        template = "blocks/sections/packages.html"


class QuestionBlock(blocks.StructBlock):
    question = blocks.CharBlock()
    answer = blocks.TextBlock()


class FaqBlock(SectionBlock):
    lead = blocks.RichTextBlock(features=["link"], required=False)
    questions = blocks.ListBlock(QuestionBlock())

    class Meta:
        icon = "help"
        label = "Questions (FAQ)"
        template = "blocks/sections/faq.html"


class EnquiryFormBlock(SectionBlock):
    anchor = anchor_block(default="quote")
    background = blocks.ChoiceBlock(choices=BACKGROUNDS, default="dark", required=False)
    lead = blocks.TextBlock(required=False)
    submit_label = blocks.CharBlock(default="Send my enquiry", label="Button text")
    thanks_text = blocks.TextBlock(label="Thank-you message")

    class Meta:
        icon = "form"
        label = "Quote request form"
        template = "blocks/sections/enquiry_form.html"

    def get_context(self, value, parent_context=None):
        from leads import forms

        context = super().get_context(value, parent_context)
        context["form_name"] = forms.ComedyEnquiryForm.form_name
        context["client_types"] = forms.CLIENT_TYPES
        context["packages"] = forms.PACKAGES
        context["deadlines"] = forms.DEADLINES
        return context


class TextSectionBlock(SectionBlock):
    body = blocks.RichTextBlock(features=["h3", "bold", "italic", "link", "ol", "ul"])

    class Meta:
        icon = "pilcrow"
        label = "Text"
        template = "blocks/sections/text.html"


SECTION_BLOCKS = [
    ("screenshot_hero", ScreenshotHeroBlock()),
    ("cards", CardsBlock()),
    ("columns", ColumnsBlock()),
    ("timeline", TimelineBlock()),
    ("steps", StepsBlock()),
    ("packages", PackagesBlock()),
    ("faq", FaqBlock()),
    ("enquiry_form", EnquiryFormBlock()),
    ("text", TextSectionBlock()),
]

# Blocks that contain a lead form, keyed by the form's name (see leads/forms.py)
FORM_BLOCK_TYPES = {
    "assessment_form": "landing-page-assessment",
    "enquiry_form": "comedy-enquiry",
}
