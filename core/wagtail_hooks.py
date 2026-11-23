"""Rich text styles that match the site's CSS: "Bold" and "Extra bold" emphasis.

The design marks emphasis with <span class="text-bold"> (700) and <span class="text-extrabold"> (800) rather
than <b>, so these are registered as their own Draftail inline styles.
"""

from wagtail import hooks
from wagtail.admin.rich_text.converters.html_to_contentstate import InlineStyleElementHandler
from wagtail.admin.rich_text.editors.draftail import features as draftail_features

EMPHASIS_STYLES = [
    # (feature name, Draftail style type, toolbar label, description, CSS class)
    ("text-bold", "TEXT_BOLD", "B", "Bold", "text-bold"),
    ("text-extrabold", "TEXT_EXTRABOLD", "XB", "Extra bold", "text-extrabold"),
]


@hooks.register("register_rich_text_features")
def register_emphasis_features(features):
    for feature_name, style_type, label, description, css_class in EMPHASIS_STYLES:
        features.register_editor_plugin(
            "draftail",
            feature_name,
            draftail_features.InlineStyleFeature(
                {"type": style_type, "label": label, "description": description},
            ),
        )
        features.register_converter_rule(
            "contentstate",
            feature_name,
            {
                "from_database_format": {f'span[class="{css_class}"]': InlineStyleElementHandler(style_type)},
                "to_database_format": {
                    "style_map": {style_type: {"element": "span", "props": {"class": css_class}}},
                },
            },
        )
