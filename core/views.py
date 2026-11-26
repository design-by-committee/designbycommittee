from django.conf import settings
from django.http import HttpResponse
from django.utils.cache import patch_cache_control
from django.views.decorators.http import require_safe
from django.views.static import serve

from core.cache import cache_publicly
from core.storage import is_hashed_rendition

ONE_YEAR = 60 * 60 * 24 * 365
MEDIA_CSP = "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'"


def is_indexable_host(request):
    """Only the live domain is indexed; staging (*.onrender.com) and local hosts are not."""
    return request.get_host().split(":")[0] in settings.INDEXABLE_HOSTS


@require_safe
def robots_txt(request):
    if is_indexable_host(request):
        lines = ["User-agent: *", "Disallow:", "", f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}"]
    else:
        lines = ["User-agent: *", "Disallow: /"]
    return cache_publicly(HttpResponse("\n".join(lines) + "\n", content_type="text/plain"))


@require_safe
def llms_txt(request):
    """/llms.txt (https://llmstxt.org/): a short Markdown guide to the site for AI assistants.

    Built from Site settings (Search & AI tab) and the live pages that search engines may index, so it stays in step
    with the admin.
    """
    from wagtail.models import Site

    from core.models import SiteSettings
    from pages.structured_data import StructuredData

    site = Site.find_for_request(request)
    settings_ = SiteSettings.for_request(request)
    lines = [f"# {settings_.site_name}", ""]
    if settings_.organisation_description:
        lines += [f"> {' '.join(settings_.organisation_description.split())}", ""]
    if settings_.llms_txt_details.strip():
        lines += [settings_.llms_txt_details.strip(), ""]

    facts = []
    if settings_.company_name:
        facts.append(f"- Company: {settings_.company_name}")
    if settings_.kvk_number:
        facts.append(f"- KvK (Dutch Chamber of Commerce) number: {settings_.kvk_number}")
    if settings_.vat_number:
        facts.append(f"- VAT number: {settings_.vat_number}")
    if settings_.founder_name:
        founder = f"[{settings_.founder_name}]({settings_.founder_url})" if settings_.founder_url else settings_.founder_name
        facts.append(f"- Founder: {founder}")
    if place := ", ".join(filter(None, [settings_.address_locality, settings_.address_country])):
        facts.append(f"- Based in: {place}")
    if areas := SiteSettings.lines(settings_.areas_served):
        facts.append(f"- Works with clients in: {', '.join(areas)}")
    if settings_.public_email:
        facts.append(f"- Email: {settings_.public_email}")
    if facts:
        lines += ["## About", "", *facts, ""]

    pages = []
    if site:
        root = site.root_page.specific
        candidates = [root, *root.get_descendants().live().public().specific()]
        pages = [page for page in candidates if hasattr(page, "is_indexable") and page.is_indexable()]
    if pages:
        lines += ["## Pages", ""]
        for page in pages:
            entry = f"- [{page.seo_title or page.title}]({page.get_full_url(request)})"
            if page.search_description:
                entry += f": {' '.join(page.search_description.split())}"
            lines.append(entry)
        lines.append("")

    rate = settings_.pounds_per_euro
    for page in pages:
        packages = page.packages()
        if not packages:
            continue
        show_pounds = any(block["show_pounds"] for block in page.blocks_of_type("packages"))
        lines += [f"## Prices: {StructuredData(page, request).service_label()}", ""]
        for package in packages:
            price = " ".join(filter(None, ["from" if package.price_is_minimum else "", package.price_display, package.price_suffix]))
            pounds = package.approximate_pounds(rate) if show_pounds else None
            if pounds:
                price += f" (about {pounds})"
            details = "; ".join(filter(None, [package.audience, package.timeframe, *package.feature_list]))
            lines.append(f"- {package.name} ({price}): {details}")
        for block in page.blocks_of_type("packages"):
            if block["fine_print"]:
                lines += ["", " ".join(block["fine_print"].split())]
        lines += ["", f"Quotes: {page.get_full_url(request)}#quote", ""]

    response = HttpResponse("\n".join(lines).rstrip() + "\n", content_type="text/markdown; charset=utf-8")
    return cache_publicly(response)


@require_safe
def media(request, path):
    """Serve uploaded images and documents from the media folder (the persistent disk on Render).

    Image renditions have a content hash in their names (core/storage.py), so browsers and Render's edge cache can
    keep them for a year. Other files (originals, documents) can change under the same name: an hour at most.
    """
    response = serve(request, path, document_root=settings.MEDIA_ROOT)
    # Uploads can be SVGs, which may contain scripts. Opened directly (not through <img>), the file is its own page
    # on this site, so it gets a policy that runs nothing, like Wagtail's document downloads do.
    response["Content-Security-Policy"] = MEDIA_CSP
    if is_hashed_rendition(path):
        patch_cache_control(response, public=True, max_age=ONE_YEAR, immutable=True)
    else:
        patch_cache_control(response, public=True, max_age=60 * 60)
    return response


def sitemap(request, *args, **kwargs):
    from wagtail.contrib.sitemaps.views import sitemap as wagtail_sitemap

    response = wagtail_sitemap(request, *args, **kwargs)
    response.render()
    return cache_publicly(response)
