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
