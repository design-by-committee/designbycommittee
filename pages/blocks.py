"""StreamField blocks for the two designs on the site.

- Agency blocks build the home page: they render as columns of the home page's 12-column grid (small.css / medium.css).
- Section blocks build landing pages such as /comedy/: each renders as a full-width <section> (comedy.css).

Block templates keep the original HTML structure and class names, so the stylesheets work unchanged.
"""

from django.core.validators import RegexValidator
from wagtail import blocks
from wagtail.images.blocks import ImageBlock
from wagtail.snippets.blocks import SnippetChooserBlock

from .icons import CHOICES as ICON_CHOICES

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


class FooterColumnBlock(blocks.StructBlock):
    """A titled group of links in the site footer (Settings → Site settings → Footer)."""

    heading = blocks.CharBlock(help_text="E.g. Websites for")
    links = blocks.ListBlock(LinkBlock(label="Link"))

    class Meta:
        icon = "list-ul"
        label = "Column"


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

BACKGROUNDS = [
    ("", "Light"),
    ("paper", "Paper (warm off-white)"),
    ("blue", "Light blue"),
    ("pink", "Light pink"),
    ("dark", "Dark"),
]
BACKGROUND_CLASSES = {"paper": "c-paper", "blue": "c-tint c-tint--blue", "pink": "c-tint c-tint--pink", "dark": "c-dark"}
HEADING_HELP = "In the light design, put *asterisks* around the words to show in extra bold, e.g. *What agents need* from your store."
CARD_COLOURS = [("pink", "Pink"), ("teal", "Teal"), ("blue", "Blue")]


class SectionBlock(blocks.StructBlock):
    """Fields shared by every landing page section."""

    anchor = anchor_block()
    background = blocks.ChoiceBlock(choices=BACKGROUNDS, default="", required=False)
    heading = blocks.CharBlock(help_text=HEADING_HELP)

    def get_context(self, value, parent_context=None):
        """Adds `background_class` and `title_id` (for aria-labelledby) to every section template."""
        context = super().get_context(value, parent_context)
        block_id = str((parent_context or {}).get("block_id") or "")
        section_id = value.get("anchor") or f"section-{block_id[:8]}"
        context["title_id"] = f"{section_id}-title"
        context["background_class"] = BACKGROUND_CLASSES.get(value.get("background") or "", "")
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
        label="Show an editor mockup next to the screenshot",
    )
    editor_mockup = blocks.ChoiceBlock(
        choices=[
            ("show", "Edit show (date, doors, lineup, ticket link)"),
            ("review", "Add review (show, quote, source, star rating)"),
        ],
        default="show",
        required=False,
        label="Which editor mockup",
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
    image = ImageBlock(
        required=False,
        label="Screenshot",
        help_text="Optional. Shown in a browser frame at the top of the card (“work” layout). A 1280×800 screenshot works best.",
    )
    link = OptionalLinkBlock(
        label="Link (optional)",
        help_text="E.g. Visit madcowcomedy.nl and https://madcowcomedy.nl/ for a case study’s live site.",
    )

    class Meta:
        icon = "doc-full"
        label = "Card"


class CardsBlock(SectionBlock):
    layout = blocks.ChoiceBlock(
        choices=[
            ("cards", "Cards (short text)"),
            ("work", "Case studies typed in here (use a Case studies section instead)"),
        ],
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


class CaseStudiesBlock(SectionBlock):
    case_studies = blocks.ListBlock(
        SnippetChooserBlock("pages.CaseStudy", label="Case study"),
        help_text="Choose from Snippets → Case studies. Edit one there to change it on every page.",
    )
    testimonial = SnippetChooserBlock(
        "core.Testimonial",
        required=False,
        help_text="Optional quote card under the case studies. Uses the testimonial’s short quote if it has one.",
    )
    footnote = blocks.TextBlock(required=False, label="Text under the case studies (optional)")

    class Meta:
        icon = "doc-full-inverse"
        label = "Case studies"
        template = "blocks/sections/case_studies.html"


class ColumnBlock(blocks.StructBlock):
    image = ImageBlock(
        required=False,
        label="Picture (optional)",
        help_text="Shown above the title. A 3:2 picture (e.g. 1200×800) works best; use the same shape for every column.",
    )
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
        help_text=(
            "solo, fringe, show or venue: selects Performer, Performer, Showrunner or Venue owner in the quote form. "
            "Optional."
        ),
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
    extra_title = blocks.CharBlock(
        required=False,
        label="Optional extra step: title",
        help_text="A separate, unnumbered step below the others, labelled “Optional extra”, e.g. Hosting and launch.",
    )
    extra_text = blocks.TextBlock(required=False, label="Optional extra step: text")

    class Meta:
        icon = "list-ol"
        label = "Numbered steps"
        template = "blocks/sections/steps.html"


class PackageChoiceBlock(blocks.StructBlock):
    """A package (Snippets → Packages) as shown on this page: its card can be featured here and not elsewhere."""

    package = SnippetChooserBlock("pages.Package")
    featured = blocks.BooleanBlock(required=False, help_text="Highlight this package on this page (dark card).")
    badge = blocks.CharBlock(required=False, help_text="Label above the card, e.g. Best for Fringe runs")
    button_text = blocks.CharBlock(required=False, help_text="Defaults to “Choose” and the package name.")
    button_link = blocks.CharBlock(default="#quote", help_text="Usually the quote form’s anchor, e.g. #quote")

    class Meta:
        icon = "tag"
        label = "Package"


class PackagesBlock(SectionBlock):
    lead = blocks.RichTextBlock(
        features=["bold", "italic", "link"],
        required=False,
        label="Introduction (optional)",
        help_text="With a single package, it sits beside the card; with several, above them.",
    )
    packages = blocks.ListBlock(
        PackageChoiceBlock(),
        help_text="Choose from Snippets → Packages. Edit a package there to change it on every page.",
    )
    show_pounds = blocks.BooleanBlock(
        required=False,
        default=True,
        label="Show approximate prices in pounds",
        help_text="Next to euro prices, using the rate in Site settings.",
    )
    fine_print = blocks.TextBlock(required=False)

    class Meta:
        icon = "tag"
        label = "Packages and prices"
        template = "blocks/sections/packages.html"


class QuestionBlock(blocks.StructBlock):
    question = blocks.CharBlock()
    answer = blocks.TextBlock(help_text="Leave a blank line to start a new paragraph.")


class FaqBlock(SectionBlock):
    lead = blocks.RichTextBlock(features=["link"], required=False)
    questions = blocks.StreamBlock(
        [
            ("question", SnippetChooserBlock("pages.Question", label="Shared question", icon="help")),
            ("custom", QuestionBlock(label="One-off question", icon="edit")),
        ],
        help_text=(
            "Shared questions come from Snippets → Questions and change everywhere when edited there. Use a one-off "
            "question for something only this page needs."
        ),
    )

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
        return context


class IllustratedPointBlock(blocks.StructBlock):
    title = blocks.CharBlock()
    text = blocks.TextBlock(help_text="Leave a blank line to start a new paragraph.")
    image = ImageBlock(
        label="Screenshot",
        help_text="Shown in a browser frame next to the text. About 1200×750 pixels works best.",
    )
    address = blocks.CharBlock(required=False, label="Address shown in the browser frame", help_text="E.g. yourname.com/gigs")

    class Meta:
        icon = "image"
        label = "Point"


class IllustratedPointsBlock(SectionBlock):
    lead = blocks.TextBlock(required=False)
    points = blocks.ListBlock(IllustratedPointBlock())

    class Meta:
        icon = "image"
        label = "Points with screenshots"
        template = "blocks/sections/illustrated_points.html"


class IconItemBlock(blocks.StructBlock):
    icon = blocks.ChoiceBlock(choices=ICON_CHOICES)
    title = blocks.CharBlock()
    text = blocks.RichTextBlock(features=["bold", "italic", "link"])

    class Meta:
        icon = "pick"
        label = "Item"


class IconGridBlock(SectionBlock):
    lead = blocks.TextBlock(required=False)
    columns = blocks.ChoiceBlock(
        choices=[("3", "Three columns (short text)"), ("2", "Two columns (longer text)")],
        default="3",
        help_text="On wide screens. Phones always show one column.",
    )
    items = blocks.ListBlock(IconItemBlock())
    footnote = blocks.RichTextBlock(features=["bold", "italic", "link"], required=False, label="Text under the grid")

    class Meta:
        icon = "pick"
        label = "Icon grid"
        template = "blocks/sections/icon_grid.html"


class TextSectionBlock(SectionBlock):
    body = blocks.RichTextBlock(features=["h3", "bold", "italic", "link", "ol", "ul"])
    image = ImageBlock(
        required=False,
        label="Photo (optional)",
        help_text="Shown beside the text on wide screens, under it on phones. PNGs with transparency work too.",
    )

    class Meta:
        icon = "pilcrow"
        label = "Text"
        template = "blocks/sections/text.html"


class ReportRowBlock(blocks.StructBlock):
    STATUSES = [("ok", "✓ Done (teal)"), ("warn", "! Needs work (coral)"), ("todo", "○ Not started (grey)")]

    label = blocks.CharBlock(help_text="E.g. Shopify Catalog eligibility")
    status = blocks.ChoiceBlock(choices=STATUSES, default="ok")
    status_text = blocks.CharBlock(help_text="E.g. Eligible, Needs work, Not started")

    class Meta:
        icon = "list-ul"
        label = "Row"


class ReportHeroBlock(blocks.StructBlock):
    """A light hero with a sample report card beside the heading (the agent readiness page)."""

    heading = blocks.CharBlock(help_text=HEADING_HELP)
    lead = blocks.TextBlock()
    primary_button = LinkBlock(label="Main button")
    secondary_button = OptionalLinkBlock(label="Second button (optional)")
    proof = blocks.CharBlock(required=False, label="Small print under the buttons")
    report_title = blocks.CharBlock(default="Agent readiness report", label="Report title")
    report_subtitle = blocks.CharBlock(required=False, label="Report subtitle", help_text="E.g. yourstore.com · Example")
    rows = blocks.ListBlock(ReportRowBlock(), label="Report rows")
    caption = blocks.CharBlock(required=False, help_text="Under the report, e.g. what the report’s summary looks like.")

    class Meta:
        icon = "list-ul"
        label = "Hero with sample report"
        template = "blocks/sections/report_hero.html"


class ChecklistItemBlock(blocks.StructBlock):
    title = blocks.CharBlock(help_text="Shown in bold, e.g. Shopify Catalog eligibility")
    text = blocks.CharBlock(required=False, help_text="Follows the title on the same line.")

    class Meta:
        icon = "tick"
        label = "Item"


class IllustratedChecklistBlock(SectionBlock):
    """A checklist beside one of the site's piggy illustrations."""

    lead = blocks.TextBlock(required=False)
    illustration = blocks.ChoiceBlock(choices=FeatureRowBlock.ILLUSTRATIONS, default="detective")
    items = blocks.ListBlock(ChecklistItemBlock())

    class Meta:
        icon = "tick"
        label = "Checklist with illustration"
        template = "blocks/sections/illustrated_checklist.html"

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context)
        name = value["illustration"]
        width, height = FeatureRowBlock.ILLUSTRATION_SIZES[name]
        context["illustration"] = {"src": f"img/{name}.png", "width": width, "height": height}
        return context


class AuditFormBlock(SectionBlock):
    """The Agent Readiness Audit request form (leads.forms.AgentAuditForm)."""

    anchor = anchor_block(default="audit")
    lead = blocks.TextBlock(required=False)
    submit_label = blocks.CharBlock(default="Request an audit", label="Button text")
    thanks_text = blocks.TextBlock(label="Thank-you message")

    class Meta:
        icon = "form"
        label = "Agent readiness audit form"
        template = "blocks/sections/audit_form.html"

    def get_context(self, value, parent_context=None):
        from leads import forms

        context = super().get_context(value, parent_context)
        form = forms.AgentAuditForm
        context["form_name"] = form.form_name
        context["product_counts"] = forms.PRODUCT_COUNTS
        context["countries"] = forms.COUNTRIES
        context["help_topics"] = forms.HELP_TOPICS
        return context


SHAREABLE_BLOCKS = [
    ("screenshot_hero", ScreenshotHeroBlock()),
    ("cards", CardsBlock()),
    ("columns", ColumnsBlock()),
    ("timeline", TimelineBlock()),
    ("steps", StepsBlock()),
    ("packages", PackagesBlock()),
    ("case_studies", CaseStudiesBlock()),
    ("faq", FaqBlock()),
    ("enquiry_form", EnquiryFormBlock()),
    ("text", TextSectionBlock()),
    ("illustrated_points", IllustratedPointsBlock()),
    ("icon_grid", IconGridBlock()),
    ("report_hero", ReportHeroBlock()),
    ("illustrated_checklist", IllustratedChecklistBlock()),
    ("audit_form", AuditFormBlock()),
]


# Landing page sections: every section type, plus a Shared section (which holds one of the others)
SECTION_BLOCKS = SHAREABLE_BLOCKS + [
    (
        "shared_section",
        SnippetChooserBlock(
            "pages.SharedSection",
            icon="snippet",
            label="Shared section",
            template="blocks/sections/shared_section.html",
            help_text="A section written once under Snippets → Shared sections and used on several pages.",
        ),
    ),
]

# Blocks that contain a lead form, keyed by the form's name (see leads/forms.py)
FORM_BLOCK_TYPES = {
    "assessment_form": "landing-page-assessment",
    "enquiry_form": "comedy-enquiry",
    "audit_form": "shopify-agent-audit",
}
