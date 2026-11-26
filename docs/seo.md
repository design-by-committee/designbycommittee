# Search engines and AI assistants (SEO and GEO)

Who the site is for: comedians, comedy shows and venues in the UK and western Europe. Target searches include
"website for comedians", "Edinburgh Fringe show website", "comedy club website design" and "how much does a comedian
website cost", and the same questions asked to AI assistants (ChatGPT search, Perplexity, Google's AI answers,
Claude). Based on an audit on 25 Nov 2026; how to edit each field is in [editing.md](editing.md#search-engines-and-ai-assistants).

## In place

- HTTPS on one canonical host, canonical tags, `/sitemap.xml` with `lastmod`, and a `/robots.txt` that lets every
  crawler in (including GPTBot, ClaudeBot and PerplexityBot). Hosts other than designbycommitt.ee get `noindex`.
- JSON-LD on every page (`pages/structured_data.py`): the organisation (`ProfessionalService`, with KvK and VAT),
  website, web page and breadcrumbs; FAQ sections as `FAQPage`; packages as a `Service` with an `Offer` per package;
  optional extra JSON-LD per page.
- `/llms.txt`, built live from Site settings, the pages and their packages.
- Per page: title tag, description, social tags, **Hide from search engines**, and **Show in menus**, which links the
  page from every footer so no landing page is an orphan.
- Landing pages, each written for one search intent: `/comedy/`, `/edfringe/`, `/comedy-venue-websites/`,
  `/comedian-website-guide/` and `/english-comedy-europe/`. The home page links to `/comedy/`.
- Prices in euros with approximate pounds for UK visitors.
- [IndexNow](https://www.indexnow.org/) (`core/indexnow.py`): when a page is published, unpublished, deleted, moved or
  renamed (in the admin, with `cms`, or on a schedule), its URL goes to api.indexnow.org, which shares it with Bing
  (and through it ChatGPT search), Yandex, Seznam, Naver, Yep and Amazon. Google doesn't take part and uses the
  sitemap. Only indexable pages on designbycommitt.ee are sent, at most once per URL every 5 minutes, a few seconds
  after the change (after the edge cache purge). The key file is `/<key>.txt`; results show in the Render logs as
  `IndexNow: submitted …` (HTTP 202 the first time while the key is checked, then 200).

## Decisions

- **No city pages.** One page about English-language comedy in Europe instead of one per city: search engines treat
  near-duplicate city pages as doorway pages.
- **No review markup on testimonials.** Google ignores reviews a business publishes about itself, and the quotes are
  already readable on the page.

## Open (site owner)

- Verify the site in Google Search Console and Bing Webmaster Tools (paste the codes into **Site settings →
  Verification & llms.txt**) and submit `https://designbycommitt.ee/sitemap.xml` to both. Bing matters for AI
  answers: ChatGPT search has relied on its index. Bing Webmaster Tools → **IndexNow** then lists the URLs the site
  has submitted.
- Google Business Profile (service-area business, address hidden) and Bing Places, with the same name, description
  and areas as Site settings.
- A LinkedIn company page, then add it under **Site settings → Search & AI → Profiles elsewhere**.
- Ask clients for a "Website by Committee" credit link; link Comedy on Tap's case study once comedyontap.nl runs the
  new theme; add a UK or Fringe case study as soon as there is one.
- Listings comedians read: the Fringe services directory (advertising@edfringe.com), festival supplier lists
  (Brighton, Leicester), comedy newsletters and podcasts.
