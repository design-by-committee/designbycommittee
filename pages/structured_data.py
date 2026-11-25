"""Structured data (schema.org JSON-LD) for a page, built from its content and Site settings.

Every page gets one @graph describing the organisation, the website and the page itself, so search engines and AI
assistants can tell who the business is, what it sells, where and for how much. Editors control it all in the admin:

- Settings → Site settings → Search & AI: the organisation (name, description, founder, location, areas served...)
- A page's Promote tab: service name, audience, areas served and extra JSON-LD
- The page's content: FAQ sections become FAQPage questions, packages become offers with prices
"""

import json
import re

from core.models import SiteSettings

CURRENCIES = {"€": "EUR", "£": "GBP", "$": "USD"}
PRICE = re.compile(r"(?P<symbol>[€£$])?\s*(?P<amount>\d[\d,.\s]*)\s*(?P<code>EUR|GBP|USD)?", re.IGNORECASE)
TITLE_SUFFIX = re.compile(r"\s+[|–—-]\s+[^|–—-]+$")

# Characters that could end the <script> element or start an HTML comment inside it
SCRIPT_ESCAPES = {ord("<"): "\\u003C", ord(">"): "\\u003E", ord("&"): "\\u0026"}


def parse_price(text):
    """("1200", "EUR") from "€1,200", "1.200 EUR" or "£950", or None when there's no amount."""
    match = PRICE.search(text or "")
    if not match:
        return None
    amount = re.sub(r"[\s,.](?=\d{3}\b)", "", match["amount"].strip()).replace(",", ".").rstrip(".")
    currency = CURRENCIES.get(match["symbol"]) or (match["code"] or "EUR").upper()
    return amount, currency


def paragraphs(text):
    return [part.strip() for part in re.split(r"\r?\n\s*\r?\n", text or "") if part.strip()]


class StructuredData:
    def __init__(self, page, request):
        self.page = page
        self.request = request
        self.settings = SiteSettings.for_request(request)
        site = page.get_site()
        self.root_url = (site.root_url if site else request.build_absolute_uri("/")).rstrip("/") + "/"
        self.page_url = page.get_full_url(request) or request.build_absolute_uri()

    # @ids, so nodes can refer to each other
    @property
    def organisation_id(self):
        return f"{self.root_url}#organisation"

    @property
    def website_id(self):
        return f"{self.root_url}#website"

    @property
    def webpage_id(self):
        return f"{self.page_url}#webpage"

    def absolute(self, url):
        return self.request.build_absolute_uri(url)

    def image(self, image, spec="width-1200"):
        rendition = image.get_rendition(spec)
        node = {
            "@type": "ImageObject",
            "url": self.absolute(rendition.url),
            "width": rendition.width,
            "height": rendition.height,
        }
        if getattr(image, "description", ""):
            node["caption"] = image.description
        return node

    def areas_served(self):
        return SiteSettings.lines(self.page.areas_served) or SiteSettings.lines(self.settings.areas_served)

    def graph(self):
        nodes = [self.organisation(), self.website(), self.webpage()]
        if self.page.depth > 2:
            nodes.append(self.breadcrumbs())
        service = self.service()
        if service:
            nodes.append(service)
        nodes.extend(self.extra())
        return {"@context": "https://schema.org", "@graph": nodes}

    def organisation(self):
        s = self.settings
        node = {
            "@type": s.organisation_type or "Organization",
            "@id": self.organisation_id,
            "name": s.site_name,
            "url": self.root_url,
        }
        if s.company_name and s.company_name != s.site_name:
            node["legalName"] = s.company_name
        if s.alternate_name:
            node["alternateName"] = s.alternate_name
        if s.organisation_description:
            node["description"] = s.organisation_description
        if s.logo:
            node["logo"] = self.image(s.logo, "max-512x512")
        if s.default_social_image:
            node["image"] = self.absolute(s.default_social_image.get_rendition("width-1200").url)
        if s.public_email:
            node["email"] = s.public_email
        if s.founder_name:
            founder = {"@type": "Person", "name": s.founder_name}
            if s.founder_url:
                founder["sameAs"] = [s.founder_url]
            node["founder"] = founder
        if s.address_locality or s.address_country:
            address = {"@type": "PostalAddress"}
            if s.address_locality:
                address["addressLocality"] = s.address_locality
            if s.address_country:
                address["addressCountry"] = s.address_country
            node["address"] = address
        if areas := SiteSettings.lines(s.areas_served):
            node["areaServed"] = areas
        if topics := SiteSettings.lines(s.knows_about):
            node["knowsAbout"] = topics
        if profiles := SiteSettings.lines(s.same_as):
            node["sameAs"] = profiles
        return node

    def website(self):
        node = {
            "@type": "WebSite",
            "@id": self.website_id,
            "url": self.root_url,
            "name": self.settings.site_name,
            "publisher": {"@id": self.organisation_id},
            "inLanguage": self.page.html_lang,
        }
        if self.settings.alternate_name:
            node["alternateName"] = self.settings.alternate_name
        return node

    def webpage(self):
        page = self.page
        faqs = self.faq_questions()
        node = {
            "@type": ["WebPage", "FAQPage"] if faqs else "WebPage",
            "@id": self.webpage_id,
            "url": self.page_url,
            "name": page.seo_title or page.title,
            "isPartOf": {"@id": self.website_id},
            "about": {"@id": self.organisation_id},
            "inLanguage": page.html_lang,
        }
        if page.search_description:
            node["description"] = page.search_description
        if page.last_published_at:
            node["dateModified"] = page.last_published_at.isoformat()
        if image := page.social_image():
            node["primaryImageOfPage"] = self.image(image)
        if page.depth > 2:
            node["breadcrumb"] = {"@id": f"{self.page_url}#breadcrumb"}
        if faqs:
            node["mainEntity"] = faqs
        return node

    def breadcrumbs(self):
        trail = self.page.get_ancestors(inclusive=True).filter(depth__gt=1).specific()
        return {
            "@type": "BreadcrumbList",
            "@id": f"{self.page_url}#breadcrumb",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": position,
                    "name": "Home" if crumb.depth == 2 else crumb.title,
                    "item": crumb.get_full_url(self.request),
                }
                for position, crumb in enumerate(trail, start=1)
            ],
        }

    def faq_questions(self):
        return [
            {
                "@type": "Question",
                "name": item["question"],
                "acceptedAnswer": {"@type": "Answer", "text": "\n\n".join(paragraphs(item["answer"]))},
            }
            for faq in self.page.blocks_of_type("faq")
            for item in faq["questions"]
        ]

    def service_label(self):
        page = self.page
        return page.service_name or TITLE_SUFFIX.sub("", page.seo_title or "") or page.title

    def service(self):
        """A Service with an offer per package, on pages that list packages or name a service."""
        page = self.page
        packages = [package for block in page.blocks_of_type("packages") for package in block["packages"]]
        if not packages and not page.service_name:
            return None
        node = {
            "@type": "Service",
            "@id": f"{self.page_url}#service",
            "name": self.service_label(),
            "url": self.page_url,
            "provider": {"@id": self.organisation_id},
        }
        if page.search_description:
            node["description"] = page.search_description
        if page.service_audience:
            node["audience"] = {"@type": "Audience", "audienceType": page.service_audience}
        if areas := self.areas_served():
            node["areaServed"] = areas
        if packages:
            node["hasOfferCatalog"] = {
                "@type": "OfferCatalog",
                "name": self.service_label(),
                "itemListElement": [self.offer(package) for package in packages],
            }
        return node

    def offer(self, package):
        description = [package["audience"], package["timeframe"], *package["features"]]
        item = {
            "@type": "Service",
            "name": f"{package['name']}: {package['audience']}" if package["audience"] else package["name"],
            "description": ". ".join(part.rstrip(".") for part in description if part) + ".",
        }
        offer = {"@type": "Offer", "name": package["name"], "itemOffered": item, "url": f"{self.page_url}#quote"}
        price = parse_price(package["price"])
        if price:
            amount, currency = price
            if "from" in (package["price_prefix"] or "").lower() or "from" in package["price"].lower():
                offer["priceSpecification"] = {
                    "@type": "PriceSpecification",
                    "minPrice": amount,
                    "priceCurrency": currency,
                }
                offer["priceCurrency"] = currency
            else:
                offer["price"] = amount
                offer["priceCurrency"] = currency
        return offer

    def extra(self):
        if not self.page.extra_json_ld.strip():
            return []
        data = json.loads(self.page.extra_json_ld)
        items = data if isinstance(data, list) else [data]
        return [{key: value for key, value in item.items() if key != "@context"} for item in items]


def json_ld_script(page, request):
    data = StructuredData(page, request).graph()
    text = json.dumps(data, ensure_ascii=False, indent=None, separators=(",", ":")).translate(SCRIPT_ESCAPES)
    return f'<script type="application/ld+json">{text}</script>'
