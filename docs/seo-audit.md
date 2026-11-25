# SEO and GEO audit: comedians in the UK and western Europe

25 Nov 2026. Audited the live site (https://designbycommitt.ee/ and /comedy/) and this repository. "GEO" means
generative engine optimisation: being found and quoted by AI assistants (ChatGPT search, Perplexity, Google's AI
Overviews, Claude), not only by classic search.

**Target searches:** "website for comedians", "comedian website designer UK", "Edinburgh Fringe show website",
"comedy club website design", "how much does a comedian website cost", and the same questions asked to an AI
assistant ("who builds websites for comedians in the UK?").

## Summary

The technical basics are sound: HTTPS, one canonical host, canonical tags, a sitemap with `lastmod`, a robots.txt
that lets every crawler in (GPTBot, ClaudeBot, PerplexityBot and Googlebot all get the pages), fast pages with
nothing loaded from other hosts, and good alt text on the comedy page.

The biggest gaps were:

1. **The comedy page was an orphan.** Nothing on the site linked to `/comedy/`; the home page's only link goes to
   LinkedIn. Search engines found it through the sitemap alone, and it inherited none of the home page's authority.
2. **No structured data at all.** Search engines and AI assistants had to guess who the business is, where it works,
   what it sells and for how much.
3. **No `llms.txt`**, and no site-wide facts (where you're based, which countries you serve, who runs it) anywhere
   a machine can read them.
4. **The copy doesn't say the words people search for.** The comedy page's H1 is "Fill every seat in the venue",
   "UK" appears only in one FAQ, and nothing says where the business is.
5. **The home page is about something else**: conversion-optimised landing pages, in US English, with no mention of
   comedy.

## Fixed in this branch (all editable in the Wagtail admin)

| Change | Where to edit it |
|---|---|
| JSON-LD on every page: the organisation (`ProfessionalService`), website, web page, breadcrumbs | Settings → Site settings → **Search & AI** |
| Comedy FAQ marked up as `FAQPage`, generated from the page's Questions section | The FAQ section itself |
| Packages marked up as a `Service` with an `Offer` per package and its price (`from` → minimum price) | The Packages section, plus Promote → **Structured data** (service name, who it's for, areas served) |
| Extra JSON-LD per page (e.g. an `Event` for a Fringe showcase), validated as JSON on save | Promote → **Extra structured data** |
| `/llms.txt`: description, key facts, pages and prices, built live from the admin | Site settings → Search & AI and **Verification & llms.txt** |
| Google Search Console and Bing Webmaster Tools verification tags | Site settings → **Verification & llms.txt** |
| Per-page **Hide from search engines** (noindex, out of the sitemap and llms.txt) | Promote tab |
| Footer links to every page with **Show in menus** ticked, so the home page links to /comedy/ | Promote → Show in menus |
| `og:site_name`, `og:locale`, `og:image` width/height/alt, `twitter:card`, `max-image-preview:large` | Site settings, the page's social fields, the image's Description |
| Footer read "Design by Committee B.V.." (double full stop) | Fixed in the template |

The editor guide (`docs/editing.md`, "Search engines and AI assistants") explains each field.

## Status (25 Nov 2026)

Released as v1.0.0 to v1.2.1, and the content is live:

- **Done:** Comedy page title, description, H1 and lead; About section (Utrecht, experience producing live comedy
  in the US and Europe); five new FAQs; prices in pounds; “WordPress” spelling; case-study links (Fallout Theater, Mad
  Cow; Comedy on Tap's live site isn't running the new theme yet, so its card has no link); Show in menus, service
  name and audience; a home page section linking to /comedy/; Site settings (Utrecht, description, llms.txt text,
  square logo); image descriptions.
- **New pages:** /edfringe/ (Fringe 2027, with a €750 one-show Fringe package), /comedy-venue-websites/,
  /comedian-website-guide/ and /english-comedy-europe/.
- **Still yours to do:** Google Search Console and Bing Webmaster Tools verification and sitemap submission; Google
  Business Profile and Bing Places; a LinkedIn company page (then add it under Profiles elsewhere); asking clients for
  credit links; the Fringe services directory listing (advertising@edfringe.com); linking Comedy on Tap once
  comedyontap.nl runs the new theme.

## To do in the admin after this is deployed

1. **Comedy page → Promote:** tick **Show in menus** (otherwise the footer link doesn't appear), fill in **Service
   name** (e.g. "Website design for comedians, comedy shows and comedy venues") and **Who it's for**, then publish.
2. **Consider renaming the page title** from "Comedy" to "Websites for comedians". The title is the footer link's
   text and the breadcrumb name, and link text is a ranking signal. The address stays `/comedy/`.
3. **Site settings → Search & AI:** check the pre-filled description, areas served and specialities; add your
   **town or city**; upload a square **logo**; add your profiles (LinkedIn company page, Instagram, Google Business
   Profile) under **Profiles elsewhere**.
4. **Verify the site** in Google Search Console *and* Bing Webmaster Tools (paste the codes into Site settings),
   then submit `https://designbycommitt.ee/sitemap.xml` to both. Bing matters for GEO: ChatGPT search has relied on its index.
5. **Images:** give the social images a **Description**; it becomes `og:image:alt`.
6. Check the result with https://search.google.com/test/rich-results and https://validator.schema.org/.

## Content recommendations (comedy page)

**Title and description.** Put the searched words first and name the region:

- Title tag: *Websites for Comedians and Comedy Shows (UK & Europe) | Committee*
- Search description: *Web design for comedians, comedy shows and venues in the UK and Europe. Fixed prices from
  €500, live in 2–4 weeks, ready for the Edinburgh Fringe 2027.*

**H1.** "Fill every seat in the venue" is a good line but carries no search terms. Either make it "Websites for
comedians that fill every seat", or keep it and change the hero's lead to open with "Website design for comedians,
comedy shows and venues in the UK and Europe."

**Say where you are and who runs it.** AI assistants quote plain factual sentences. Add a short "About Committee"
paragraph: based in (city), Netherlands; run by Andres Lucero, who produces live comedy (name the shows or nights);
works with comedians across the UK, Ireland and Europe. This is also the experience signal Google looks for.

**Answer the questions people actually ask**, as extra FAQs (they're marked up automatically):

- "How much does a website for a comedian cost?" (answer with the three prices)
- "How long does it take to build a comedian website?"
- "Where are you based?" / "Can you invoice in pounds?"
- "What should a comedian's website include?"

**Prices for UK visitors.** Everything is in euros. UK searchers compare in pounds; consider "€500 (about £430)" or
a note that you can invoice in GBP.

**Spelling.** "Wordpress" appears three times in the live copy (Why work with Committee, How it works, Mad Cow case study); it's "WordPress".

**Case studies.** None of the three are in the UK (Austin, Utrecht, Utrecht) and none link to the live sites. Add the
links, ask each client for a "Website by Committee" credit in their footer, and add a UK or Fringe client as soon as
you have one. A Fringe case study would be the strongest proof for the main audience.

## New pages worth creating

Each is a new **Landing page** in the admin (Home → Add child page). Write each for one search intent, with its own
FAQ and a link back to /comedy/. Avoid near-duplicate city pages: search engines treat those as doorway pages.

1. **Edinburgh Fringe show websites** (`/edinburgh-fringe-websites/`). The most specific, highest-intent topic you
   have. Publish by January: performers plan sites before the programme launches in June.
2. **Comedy club and venue websites** (`/comedy-venue-websites/`). Different buyer, bigger budget, different words
   (ticketing integration, programme, private hire).
3. **What a comedian's website should include, and what it costs**. A guide-style page: the kind of page AI
   assistants cite when someone asks the question.
4. Later, **English-language comedy in Europe** (Amsterdam, Berlin, Paris, Barcelona...). A real scene you already
   work in (Mad Cow, Comedy on Tap); one page about it, not one per city.

## Home page

It sells landing page optimisation to businesses, in US English, and doesn't mention comedy. If comedy is the main
line of work now, either add a section near the top ("Websites for comedians, shows and venues →" linking to
/comedy/), or make the comedy page the home page and move the agency page to its own address. The footer link fixes
the crawl path but not the message.

## Off-site (where AI assistants and Google look for confirmation)

- **Google Business Profile** as a service-area business (address hidden) and **Bing Places**, with the same name,
  description and areas as Site settings.
- A **LinkedIn company page**, then add it under Profiles elsewhere.
- **Client credit links** from every site you build (the cheapest, most relevant links you can get).
- Lists and directories comedians actually read: festival participant resources and supplier lists (Edinburgh,
  Brighton, Leicester), comedy industry newsletters and podcasts, and genuine answers in comedian communities.
  AI assistants lean heavily on these when recommending suppliers.

## Possible follow-ups

- **IndexNow** pings to Bing (and through it ChatGPT search) whenever a page is published.
- An optional **link** on case-study cards, rendered as "Visit site" and added to the structured data.
- Review markup for testimonials: left out on purpose. Google ignores reviews a business publishes about itself, and
  the quotes are already readable on the page.
