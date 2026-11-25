"""Price placeholders in page copy: {solo.price} → €500, {solo.pounds} → £420.

Editors type the placeholders anywhere in a page's text (titles, search descriptions, sections, FAQ answers) and in
Site settings. They're filled in from Snippets → Packages when a page is served (PackagePriceMiddleware), so the
copy, meta tags, structured data and llms.txt all show the current price, and the admin keeps the placeholders.

The part before the dot is the package's code (solo, fringe, show, venue). An unknown placeholder is left as it is,
so a typo shows on the page instead of disappearing.
"""

import re

PLACEHOLDER = re.compile(r"\{([a-z]+)\.(price|pounds)\}")


def fill_prices(text, pounds_per_euro=None):
    """`text` with every known placeholder replaced. Packages are only loaded when there's a placeholder."""
    if "{" not in text or not PLACEHOLDER.search(text):
        return text
    from pages.models import Package

    packages = {}
    for package in Package.objects.order_by("price", "pk"):
        packages.setdefault(package.code, package)  # with two packages on one code, the cheaper one wins

    def replace(match):
        package = packages.get(match[1])
        if package is None:
            return match[0]
        if match[2] == "price":
            return package.price_display
        return package.approximate_pounds(pounds_per_euro) or ""

    return PLACEHOLDER.sub(replace, text)
