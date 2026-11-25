"""Create the site's pages, testimonials, images and settings with the copy from the original static site.

Run once on each new environment (local, staging, production):

    python manage.py import_current_site --hostname designbycommitt.ee --port 443

It is safe to run again: images, testimonials and settings are matched and updated in place, and page content is
only replaced when a page has no content yet, or when --force is given (which overwrites edits made in the admin).
"""

import json
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.images import ImageFile
from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.images.models import Image
from wagtail.models import Site

from core.models import SiteSettings, Testimonial
from pages.models import HomePage, LandingPage

STATIC_IMG = Path(settings.BASE_DIR) / "static" / "img"
LINKEDIN = "https://www.linkedin.com/in/andreslucero/"


def block(block_type, value):
    return {"type": block_type, "value": value, "id": str(uuid.uuid4())}


def rich(html):
    return f"<p>{html}</p>"


# ---------------------------------------------------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------------------------------------------------

IMAGES = {
    # key: (file in static/img, title)
    "mad_cow": ("work-mad-cow-comedy.jpg", "Mad Cow Comedy homepage"),
    "logo_old_santa_fe": ("testimonial-old-santa-fe-trail.png", "Old Santa Fe Trail Beef Jerky logo"),
    "logo_fallout": ("testimonial-fallout-theater.svg", "Fallout Theater logo"),
    "logo_madhouse": ("testimonial-madhouse-development.svg", "Madhouse Development Services logo"),
}

TESTIMONIALS = {
    "old_santa_fe": {
        "name": "Andrew Chavez",
        "role": "Operations Manager",
        "company": "Old Santa Fe Trail Beef Jerky",
        "logo": "logo_old_santa_fe",
        "card_colour": "soft-pink",
        "quote": (
            "Committee moved our site to Shopify with a custom-designed theme, and the results were better than we "
            "could have imagined! Our conversion rate improved by over 105% and revenue continues to grow by 16% every "
            "month. Highly recommended, the service pays for itself."
        ),
        "short_quote": "",
    },
    "fallout": {
        "name": "Aaron Walther",
        "role": "Co-Founder",
        "company": "Fallout Theater",
        "logo": "logo_fallout",
        "card_colour": "turquoise",
        "quote": (
            "Andres created our website, and it was a pleasure to work with him throughout the process. The website "
            "itself is easy to use, maintain, and most importantly it looks very clean. I would certainly recommend "
            "Andres for managing the creation of a small business webpage!"
        ),
        "short_quote": (
            "Andres created our website, and it was a pleasure to work with him throughout the process. The website "
            "itself is easy to use, maintain, and most importantly it looks very clean."
        ),
    },
    "madhouse": {
        "name": "Henry Flores",
        "role": "Vice President",
        "company": "Madhouse Development Services",
        "logo": "logo_madhouse",
        "card_colour": "light-grey",
        "quote": (
            "Andres helped us optimize our mobile site, fixing some long-standing issues and making our theme more "
            "usable on mobile devices. His work was fast and professional, and we were all very happy with the end "
            "result. I’d recommend him to others looking to optimize their sites."
        ),
        "short_quote": "",
    },
}

AUDIT_POINTS = [
    "Analyze website data for conversion signals",
    "Identify key audience groups & usage patterns",
    "Receive qualitative user experience feedback",
    "Uncover obstacles in the customer journey",
]


def home_page_content(testimonials):
    return {
        "title": "Home",
        "seo_title": "Accelerate Growth with Conversion-Optimized Design by Committee",
        "search_description": (
            "Using proven techniques of persuasive design, we help you optimize every aspect of your landing "
            "page—from the technical to the psychological—to amplify your marketing message and increase conversions."
        ),
        "body": [
            block("hero", {
                "heading": rich('<span class="text-extrabold">Accelerate Growth</span> with Conversion-Optimized Design'),
                "lead": rich(
                    'Using <span class="text-bold">proven techniques of persuasive design</span>, we help you optimize '
                    "every aspect of your landing page—from the technical to the psychological—to amplify your "
                    'marketing message and <span class="text-bold">increase conversions.</span>'
                ),
                "button": {"text": "See our 3-Step Design Process", "url": "#grow"},
            }),
            block("intro", {
                "anchor": "grow",
                "heading": rich('Custom Landing Page Designs to <span class="text-extrabold">Grow Your Business</span>'),
                "lead": rich(
                    "Backed by data and optimized for conversion, our designs provide lasting value by "
                    '<span class="text-extrabold">improving the metrics that matter</span> most to your business.'
                ),
                "link": {"text": "", "url": "", "new_tab": False},
            }),
            block("feature", {
                "heading": "Gain Visitor Insights",
                "illustration": "detective",
                "illustration_side": "left",
                "lead": rich(
                    'Learn how people behave on your landing page, <span class="text-extrabold">understand your '
                    "visitors’ mindset</span>, and identify critical areas for improvement."
                ),
                "points": AUDIT_POINTS,
            }),
            block("feature", {
                "heading": "Devise Winning Strategies",
                "illustration": "champion",
                "illustration_side": "right",
                "lead": rich(
                    "Resolve major UX issues and improve your offer using powerful psychological triggers that "
                    '<span class="text-bold">influence more people to convert </span>on your landing page.'
                ),
                "points": [
                    "Establish a clear visual hierarchy & remove distractions",
                    "Update the look-and-feel to stay competitive in your market",
                    "Highlight benefits that differentiate your product or service",
                    "Prioritize the most valuable actions in your funnel",
                ],
            }),
            block("feature", {
                "heading": "Maximize Return on Ad Spend",
                "illustration": "laptop",
                "illustration_side": "left",
                "lead": rich(
                    "Personalize your landing page with relevant, contextual content to "
                    '<span class="text-bold">reduce ad costs and improve Quality Scores.</span>'
                ),
                # The original page repeats the first feature's points here; kept as-is.
                "points": AUDIT_POINTS,
            }),
            block("button", {"button": {"text": "Get a Free Landing Page Assessment", "url": "#contact"}}),
            block("intro", {
                "anchor": "",
                "heading": rich('A Design Partner <span class="text-extrabold">Committed to Your Success</span>'),
                "lead": rich(
                    '<span class="text-bold">Committee</span> is dedicated to providing long-term value for our '
                    "clients through technology &amp; design."
                ),
                "link": {"text": "Learn more about our founder Andres Lucero", "url": LINKEDIN, "new_tab": True},
            }),
            block("testimonials", {
                "testimonials": [testimonials[key].pk for key in ("old_santa_fe", "fallout", "madhouse")],
            }),
            block("assessment_form", {
                "anchor": "contact",
                "heading": rich('Get a <span class="text-extrabold">Free Landing Page Assessment</span>'),
                "lead": rich(
                    'Schedule a quick call to <span class="text-bold">uncover obstacles you never knew existed '
                    "</span>and learn how you can start optimizing your landing page today."
                ),
                "thanks_text": (
                    "We look forward to speaking to you about your project. We'll reach out shortly to confirm the "
                    "meeting time and provide you with our dial-in details."
                ),
            }),
        ],
    }


PACKAGES = {
    "solo": {
        "name": "Solo", "audience": "For comedians", "price": "495", "price_is_minimum": False,
        "price_suffix": "one-off", "timeframe": "Live in 2–4 weeks",
        "features": [
            "Home, about, gigs, video and press pages",
            "A gig list you can update from your phone",
            "Downloadable press photos and bio",
            "Mailing list sign-up",
            "Domain, SSL and launch setup",
        ],
    },
    "show": {
        "name": "Show", "audience": "For shows, nights and festival runs", "price": "795", "price_is_minimum": False,
        "price_suffix": "one-off", "timeframe": "Live in 4–6 weeks",
        "features": [
            "Everything in Solo",
            "Show pages with dates and ticket links",
            "Review quotes and star ratings",
            "A QR code landing page for flyers",
            "Lineup pages for recurring nights",
        ],
    },
    "venue": {
        "name": "Venue", "audience": "For clubs, theatres and venues", "price": "1950", "price_is_minimum": True,
        "price_suffix": "", "timeframe": "Live in 6–8 weeks",
        "features": [
            "As many pages as your programme needs",
            "A show calendar connected to your ticketing",
            "Pages for classes and workshops",
            "Private hire, memberships or donations",
            "Training for your staff",
        ],
    },
}


def comedy_page_content(images, testimonials, packages):
    return {
        "title": "Comedy",
        "slug": "comedy",
        "seo_title": "WordPress Websites for Comedians and Comedy Shows | Committee",
        "search_description": (
            "Committee builds WordPress websites for comedians, comedy shows and venues. Fixed prices in euros, sites "
            "live in weeks, and ready for the Edinburgh Fringe 2027."
        ),
        "og_title": "Fill more seats at every show",
        "og_description": "WordPress websites for comedians, comedy shows and venues, built by a comedy producer.",
        "og_image": images["mad_cow"],
        "show_in_menus": True,
        "service_name": "Website design for comedians, comedy shows and comedy venues",
        "service_audience": "Comedians, comedy shows and comedy venues",
        "header_links": [
            block("link", {"text": "Fringe 2027", "url": "#fringe"}),
            block("link", {"text": "Packages", "url": "#packages"}),
            block("link", {"text": "Work", "url": "#work"}),
            block("link", {"text": "FAQ", "url": "#faq"}),
        ],
        "header_button": [block("button", {"text": "Get a quote", "url": "#quote"})],
        "body": [
            block("screenshot_hero", {
                "heading": "Fill more seats at every show",
                "lead": (
                    "Committee builds WordPress websites for comedians and showrunners. Your gigs, lineups and ticket "
                    "links live in one place you can update from your phone, so anyone who wants to see you can find "
                    "the next show and book it."
                ),
                "primary_button": {"text": "See packages and prices", "url": "#packages"},
                "secondary_button": {"text": "Get a quote", "url": "#quote"},
                "proof": "Websites for Mad Cow Comedy, Comedy on Tap and Fallout Theater",
                "screenshot": {
                    "image": images["mad_cow"].pk,
                    "alt_text": (
                        "The Mad Cow Comedy homepage: a photo of a laughing audience, a link to the agenda, and cards "
                        "for the next three Sunday shows."
                    ),
                    "decorative": False,
                },
                "screenshot_address": "madcowcomedy.nl",
                "show_editor_mockup": True,
                "caption": "Mad Cow Comedy’s homepage, and the WordPress screen for adding a show.",
            }),
            block("cards", {
                "anchor": "",
                "background": "",
                "heading": "Who we build for",
                "layout": "cards",
                "cards": [
                    {"title": "Comedians", "meta": "", "colour": "pink", "text": (
                        "A site that works as your calling card for promoters, bookers and press, with your bio, "
                        "clips, photos and upcoming dates in one place. Adding a new gig takes a couple of minutes."
                    )},
                    {"title": "Shows and showrunners", "meta": "", "colour": "teal", "text": (
                        "A home for a monthly night, a solo hour or a festival run, with lineups, ticket links, "
                        "reviews and a mailing list that brings your audience back for the next show."
                    )},
                    {"title": "Clubs and venues", "meta": "", "colour": "blue", "text": (
                        "Your full programme connected to your ticketing, with pages for classes, workshops, private "
                        "hire and memberships that your staff can keep up to date."
                    )},
                ],
                "testimonial": None,
            }),
            block("columns", {
                "anchor": "",
                "background": "paper",
                "heading": "Why work with Committee",
                "columns": [
                    {"title": "Live in weeks", "link": {"text": "", "url": ""}, "text": (
                        "We build on a WordPress setup that’s already running comedy sites, so we start from what "
                        "works instead of from scratch. A solo site is usually live in two to four weeks."
                    )},
                    {"title": "Fixed prices", "link": {"text": "", "url": ""}, "text": (
                        "Each package has a fixed price, listed below in euros. You know the full cost before we "
                        "start, and there’s no hourly billing."
                    )},
                    {"title": "Run by a comedy producer", "link": {"text": "More about Andres", "url": LINKEDIN}, "text": (
                        "Committee is run by Andres Lucero, who produces and runs comedy shows. He knows a show’s "
                        "website has to sell tickets, keep lineups current and load quickly on a phone."
                    )},
                ],
            }),
            block("timeline", {
                "anchor": "fringe",
                "background": "dark",
                "heading": "Websites for Edinburgh Fringe shows",
                "lead": (
                    "If you’re taking a show to the Fringe in August 2027, your posters, flyers and listing all need "
                    "somewhere to send people. We’ll have your site ready well before the programme launches, so it’s "
                    "working for you through previews and the whole run."
                ),
                "timeline": [
                    {"when": "Winter", "what": "Get in touch and book a start date."},
                    {"when": "Spring", "what": "Your site goes live, in time for press releases and early ticket sales."},
                    {"when": "June", "what": (
                        "The Fringe programme launches. Your listing, flyers and posters all link to the same page."
                    )},
                    {"when": "August", "what": (
                        "During the run, you add new reviews and star ratings yourself as they come in."
                    )},
                ],
                "panel_heading": "What a Fringe show site includes",
                "panel_items": [
                    "Fast loading on mobile data",
                    "A QR code page for flyers and posters",
                    "Links to the Fringe box office or your venue’s ticketing",
                    "Review quotes and star ratings you can update",
                    "A press page with downloadable photos and show copy",
                    "Mailing list sign-up",
                ],
                "panel_button": {"text": "Plan my Fringe site", "url": "#quote"},
                "panel_button_package": "show",
                "footnote": (
                    "Not going to Edinburgh this year? We work with comedians, shows and venues across the UK and "
                    "Europe all year round."
                ),
            }),
            block("steps", {
                "anchor": "",
                "background": "",
                "heading": "How it works",
                "lead": "This is the same process we used for Fallout Theater, Mad Cow Comedy and Comedy on Tap.",
                "steps": [
                    {"title": "Intro call", "text": (
                        "A free 20-minute call about your show or venue, your audience and your deadline. Afterwards "
                        "you get a fixed quote."
                    )},
                    {"title": "Content", "text": (
                        "We send a checklist for your bio, photos, videos and ticket links, and help write or edit "
                        "anything you’re unsure about."
                    )},
                    {"title": "Design and review", "text": (
                        "We design and build the site, then send a private preview link. You check it on your phone "
                        "and laptop and send us one list of changes."
                    )},
                    {"title": "Launch and training", "text": (
                        "We launch on your domain and show you how to add shows, change lineups and update reviews, "
                        "so you don’t rely on us for day-to-day changes."
                    )},
                ],
            }),
            block("packages", {
                "anchor": "packages",
                "background": "paper",
                "heading": "Packages and prices",
                "packages": [
                    {"package": packages["solo"].pk, "featured": False, "badge": "", "button_text": "",
                     "button_link": "#quote"},
                    {"package": packages["show"].pk, "featured": True, "badge": "Best for Fringe runs",
                     "button_text": "", "button_link": "#quote"},
                    {"package": packages["venue"].pk, "featured": False, "badge": "", "button_text": "",
                     "button_link": "#quote"},
                ],
                "show_pounds": False,
                "fine_print": (
                    "Timelines start once we have your copy, photos and links. Prices exclude VAT where it applies. "
                    "Hosting and ongoing support are available as an optional monthly plan."
                ),
            }),
            block("cards", {
                "anchor": "work",
                "background": "",
                "heading": "Recent work",
                "layout": "work",
                "cards": [
                    {
                        "title": "Fallout Theater", "colour": "teal",
                        "meta": "Improv, sketch and stand-up theatre and school in Austin, Texas",
                        "text": (
                            "Fallout’s team runs a busy calendar of shows, classes and corporate workshops. They keep "
                            "all of it up to date themselves without waiting on a developer, and audiences and "
                            "students find everything in one place."
                        ),
                    },
                    {
                        "title": "Mad Cow Comedy", "colour": "pink",
                        "meta": "Weekly English-language stand-up in Utrecht and across the Netherlands",
                        "text": (
                            "Mad Cow’s producers add each show once, in their ticketing system, and it appears on the "
                            "site with the full lineup, venue details and ticket link. Nobody retypes listings every "
                            "week, so that time goes back into booking acts and running shows."
                        ),
                    },
                    {
                        "title": "Comedy on Tap", "colour": "blue",
                        "meta": "Monthly improv and stand-up night at Comedyhuis, Utrecht",
                        "text": (
                            "The organisers add each month’s show once. The homepage always leads with the next date "
                            "and past shows drop off the agenda by themselves, so the site stays current between shows "
                            "without anyone having to remember to update it."
                        ),
                    },
                ],
                "testimonial": testimonials["fallout"].pk,
            }),
            block("faq", {
                "anchor": "faq",
                "background": "paper",
                "heading": "Questions",
                "lead": rich('If your question isn’t answered here, <a href="#quote">ask us directly</a>.'),
                "questions": [
                    {"question": "Why WordPress?", "answer": (
                        "You own the site, it’s easy to update, and it works with almost every ticketing, mailing list "
                        "and video tool comedians already use. If you ever want to move on, any WordPress developer "
                        "can take it over."
                    )},
                    {"question": "Can I update the site myself?", "answer": (
                        "Yes. Adding a gig, changing a lineup or adding a new review takes a minute or two, and every "
                        "launch includes a walkthrough so you know where everything is."
                    )},
                    {"question": "Which ticketing platforms do you work with?", "answer": (
                        "Anything that gives you a link or an embed, including the Fringe box office, Eventbrite, "
                        "Crowdwork, Ticket Tailor, DICE, Confirmed.show and most venue box offices."
                    )},
                    {"question": "I’m only at the Fringe for August. Is a website worth it?", "answer": (
                        "The Show package is designed for a festival run. After August, the same site becomes the "
                        "home for your tour, a transfer or next year’s show with a few edits."
                    )},
                    {"question": "Do I need my own hosting and domain?", "answer": (
                        "No. We can register your domain and host the site for you on an optional monthly plan, or set "
                        "everything up on accounts you already have."
                    )},
                    {"question": "Do you work outside the UK?", "answer": (
                        "Yes. We work remotely with comedians, shows and venues across the UK and Europe, and we price "
                        "and invoice in euros."
                    )},
                    {"question": "Can you work to a tight deadline?", "answer": (
                        "Tell us your date when you get in touch. If the timeline is too tight for the full package, "
                        "we’ll say so and suggest a smaller first version that can launch sooner."
                    )},
                ],
            }),
            block("enquiry_form", {
                "anchor": "quote",
                "background": "dark",
                "heading": "Get a quote",
                "lead": (
                    "Tell us a little about your show or venue. We’ll reply within one working day with a fixed quote "
                    "and a time for a free 20-minute call."
                ),
                "submit_label": "Send my enquiry",
                "thanks_text": (
                    "Your enquiry is in. We’ll be in touch within one working day with a fixed quote and a time for a "
                    "quick call."
                ),
            }),
        ],
    }


# ---------------------------------------------------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------------------------------------------------


class Command(BaseCommand):
    help = "Create the pages, testimonials, images and settings from the original static site."

    def add_arguments(self, parser):
        parser.add_argument("--hostname", default="localhost", help="The site's host name, e.g. designbycommitt.ee")
        parser.add_argument("--port", type=int, default=80, help="443 for an HTTPS site")
        parser.add_argument(
            "--initial",
            action="store_true",
            help="Do nothing if the home page already has content. Safe to run on every deploy.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Replace page content even if the pages already have content (overwrites admin edits).",
        )

    @transaction.atomic
    def handle(self, *args, hostname, port, force, initial, **options):
        site = Site.objects.get(is_default_site=True)
        if initial and len(site.root_page.specific.body):
            self.stdout.write("The site already has content; nothing to import.")
            return

        site.hostname, site.port, site.site_name = hostname, port, "Design by Committee"
        site.save()
        self.stdout.write(f"Site: {hostname}:{port}")

        images = {key: self.get_or_create_image(filename, title) for key, (filename, title) in IMAGES.items()}
        testimonials = {key: self.update_testimonial(data, images) for key, data in TESTIMONIALS.items()}
        packages = {code: self.get_or_create_package(code, data) for code, data in PACKAGES.items()}

        site_settings = SiteSettings.for_site(site)
        site_settings.company_name = "Design by Committee BV"
        if not site_settings.default_social_image:
            site_settings.default_social_image = images["mad_cow"]
        site_settings.save()

        home = site.root_page.specific
        if not isinstance(home, HomePage):
            raise SystemExit("The site's root page isn't a HomePage. Run migrations on a fresh database first.")
        self.update_page(home, home_page_content(testimonials), force)

        comedy = LandingPage.objects.child_of(home).filter(slug="comedy").first()
        if comedy is None:
            comedy = LandingPage(title="Comedy", slug="comedy")
            home.add_child(instance=comedy)
            force = True  # a brand-new page always gets its content
        self.update_page(comedy, self.use_snippets(comedy_page_content(images, testimonials, packages)), force)

        self.stdout.write(self.style.SUCCESS("Done."))

    def get_or_create_image(self, filename, title):
        image = Image.objects.filter(title=title).first()
        if image:
            return image
        with open(STATIC_IMG / filename, "rb") as f:
            image = Image(title=title)
            image.file = ImageFile(f, name=filename)
            image.save()
        self.stdout.write(f"Image: {title}")
        return image

    def use_snippets(self, content):
        """Case studies and FAQ questions are snippets the page chooses: create any that are missing."""
        from pages.models import CaseStudy, Question

        for section in content["body"]:
            value = section["value"]
            if section["type"] == "cards" and value.get("layout") == "work":
                cases = []
                for card in value["cards"]:
                    case, _ = CaseStudy.objects.get_or_create(
                        title=card["title"],
                        defaults={"meta": card.get("meta", ""), "text": card["text"], "colour": card["colour"]},
                    )
                    cases.append(case.pk)
                section["type"] = "case_studies"
                section["value"] = {
                    "anchor": value.get("anchor", ""), "background": value.get("background", ""),
                    "heading": value["heading"], "case_studies": cases, "testimonial": value.get("testimonial"),
                }
            elif section["type"] == "faq":
                value["questions"] = [
                    {"type": "question", "value": Question.objects.get_or_create(**item)[0].pk}
                    for item in value["questions"]
                ]
        return content

    def get_or_create_package(self, code, data):
        """Packages are edited in the admin once they exist, so only missing ones are created."""
        from pages.models import Package

        package = Package.objects.filter(code=code).first()
        if package is None:
            package = Package.objects.create(code=code, **{**data, "features": "\n".join(data["features"])})
        return package

    def update_testimonial(self, data, images):
        values = {**data, "logo": images[data["logo"]]}
        testimonial, created = Testimonial.objects.update_or_create(
            name=data["name"], company=data["company"], defaults=values
        )
        self.stdout.write(f"Testimonial: {testimonial} ({'created' if created else 'updated'})")
        return testimonial

    def update_page(self, page, content, force):
        page = page.specific
        if len(page.body) and not force:
            self.stdout.write(f"Page {page.url_path}: has content, left as is (use --force to replace)")
            return
        for field, value in content.items():
            if field in ("body", "header_links", "header_button"):
                value = json.dumps(value)
            setattr(page, field, value)
        page.save_revision().publish()
        self.stdout.write(f"Page {page.url_path}: content imported and published")
