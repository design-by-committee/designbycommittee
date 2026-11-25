import re

from django import template
from django.utils.safestring import mark_safe
from wagtail.rich_text import RichText, expand_db_html

register = template.Library()

PARAGRAPH = re.compile(r"<p(?:\s[^>]*)?>(.*?)</p>", re.DOTALL)


@register.filter
def inline_richtext(value):
    """Render a rich text value without its wrapping <p>, for use inside <h1>, <h2>, <p class="lead"> etc.

    Several paragraphs are joined with <br>.
    """
    if value is None:
        return ""
    html = expand_db_html(value.source if isinstance(value, RichText) else str(value)).strip()
    paragraphs = PARAGRAPH.findall(html)
    if paragraphs:
        html = "<br>".join(p.strip() for p in paragraphs)
    return mark_safe(html)  # noqa: S308  (rich text is sanitised by Wagtail's editor and converter)


@register.filter
def is_anchor(url):
    """True for in-page links such as "#quote"."""
    return str(url or "").startswith("#")


@register.filter
def client_type(package_code):
    """The quote form's "I’m a…" option for a pricing package code (solo, show, venue), or "" if there's none."""
    from leads.forms import PACKAGE_CLIENT_TYPES

    return PACKAGE_CLIENT_TYPES.get(package_code, "")


@register.simple_tag(takes_context=True)
def structured_data(context):
    """The page's schema.org JSON-LD (pages/structured_data.py), or nothing on pages without it."""
    page = context.get("page")
    request = context.get("request")
    if page is None or request is None or not hasattr(page, "blocks_of_type"):
        return ""
    from pages.structured_data import json_ld_script

    return mark_safe(json_ld_script(page, request))  # noqa: S308  (JSON with <, > and & escaped)


@register.filter
def og_locale(lang):
    """Open Graph locale from a language tag: "en-GB" → "en_GB". Empty when there's no region."""
    lang = str(lang or "")
    return lang.replace("-", "_") if "-" in lang else ""


@register.filter
def without_final_full_stop(text):
    """"Design by Committee B.V." → "Design by Committee B.V", so a sentence can end it with its own full stop."""
    return str(text or "").rstrip(".")


@register.simple_tag
def icon(name):
    """An Icon grid icon (pages/icons.py) as inline SVG."""
    from pages.icons import icon_svg

    return icon_svg(name)
