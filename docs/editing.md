# Editing the site

How to change designbycommitt.ee in the Wagtail admin. Sign in at https://designbycommitt.ee/admin/.

## Pages

| Page | Address | Page type |
|---|---|---|
| Home | `/` | Home page: the original agency design |
| Websites for comedians | `/comedy/` | Landing page: full-width sections |
| Edinburgh Fringe 2027 websites | `/edfringe/` | Landing page, for visitors from the Fringe services directory |
| Comedy venue websites | `/comedy-venue-websites/` | Landing page |
| Comedian website guide | `/comedian-website-guide/` | Landing page (text sections) |
| English-language comedy in Europe | `/english-comedy-europe/` | Landing page |

Open **Pages** in the left menu, then click a page title to edit it.

### Change text or images

1. Open the page. Its content is a list of **sections** (blocks) under **Body**.
2. Click a section to expand it and edit its fields.
3. Click **Preview** (top right) to check it, then **Publish**. **Save draft** keeps your changes unpublished.

Every published version is kept: **History** (the clock icon) shows earlier versions, and you can compare or restore them.
Changes Claude makes from the command line appear there as **Claude (command line)**, usually as drafts for you to
review and publish. Its changes to testimonials, settings, images, users and other records are listed under
**Reports → Site history**.

### Add, move or remove a section

- **Add:** click the **+** between two sections and pick a section type.
- **Move:** drag a section by its handle, or use the up/down arrows in its header.
- **Remove:** use the bin icon in the section's header.

### Bold and extra bold text

Headings and intro paragraphs on the home page have two emphasis buttons in the toolbar: **B** (bold) and **XB**
(extra bold). They give the heavier weights used in the design, e.g. “Accelerate Growth” in the home page heading.

### Links to a section on the same page

Sections have an optional **Anchor** field. A section with anchor `packages` can be linked to as `#packages` from
buttons and header links. Keep the existing anchors in place:

- Home: `grow` and `contact` (the layout also uses these for spacing and centring)
- Comedy: `fringe`, `packages`, `work`, `about`, `faq` and `quote` (header links and buttons point at them)
- Edinburgh Fringe: `dates`, `packages`, `work`, `faq` and `quote`
- Venues and Europe: `packages`, `work`, `faq` and `quote`; the guide: `include`, `cost`, `faq` and `quote`

Keep page titles short and descriptive (e.g. “Websites for comedians”, not “Comedy”): they're used in breadcrumbs and
in search results.

**Prices in pounds** (“about £420”) are worked out from the euro price at the rate in **Settings → Site settings →
General → Pounds per euro**. Change the rate there and every page follows; leave it empty to hide pound prices.

## Section types

**Home page** (agency design):

| Section | Use it for |
|---|---|
| Hero with moped illustration | The opening heading, intro and button |
| Centred heading and text | A heading with an intro paragraph, optionally with an arrow link |
| Illustrated feature | Heading, piggy illustration (left or right), intro and bullet points |
| Centred button | A single call-to-action button |
| Testimonial carousel | Pick testimonials to show (a slider on phones) |
| Landing page assessment form | The two-step request form |

**Landing pages** (sections design, e.g. /comedy/):

| Section | Use it for |
|---|---|
| Hero with screenshot | Heading, intro, two buttons and a screenshot in a browser frame, with an optional editor mockup (“Edit show” or “Add review”) |
| Coloured cards | Audience cards (who you build for, what a site needs); optional quote card underneath |
| Case studies | Client projects chosen from **Snippets → Case studies**, with an optional testimonial underneath |
| Columns | Short points side by side, each with an optional link and an optional picture above it |
| Timeline with checklist | A dated timeline next to a checklist panel with a button |
| Numbered steps | A process, numbered automatically |
| Packages and prices | Pricing cards chosen from **Snippets → Packages**; on each page, mark one as featured and give it a badge. An optional introduction goes above the cards, or beside a single card |
| Questions (FAQ) | Expandable questions: **shared questions** from **Snippets → Questions**, or **one-off questions** written on the page |
| Shared section | Any section written once under **Snippets → Shared sections** and placed on several pages |
| Quote request form | The enquiry form |
| Text | Free text with headings, lists and links, and an optional photo beside it (e.g. the comedy page's About section) |
| Icon grid | Short items, each with an icon, a title and text (bold and links allowed), in two or three columns, with optional text under the grid |
| Points with screenshots | Short points, each with a screenshot in a browser frame, alternating sides (e.g. the guide's “The essentials”) |

Each landing page section can have a **Light**, **Paper** or **Dark** background.

## New landing page

1. **Pages → Home → ⋯ → Add child page → Landing page.**
2. Fill in the title and add sections. On the **Promote** tab, set the **Slug** (the address, e.g. `festivals` for
   `/festivals/`), the **Title tag** and **Search description**, and optionally the **Social sharing** fields.
3. Add **Header links** for the sections you want in the top menu, and a **Header button** (usually `#quote`).
4. On the **Promote** tab, tick **Show in menus** to link the page from the site footer (search engines find pages
   through links), and fill in **Structured data** (see Search engines and AI assistants below).
5. Publish.

## Shared pieces: write once, use on any page

Anything that appears on more than one page is written once under **Snippets** and chosen by the pages. Edit it
there and every page that uses it changes, along with the structured data and `/llms.txt`.

| Snippet | Chosen in | What's shared |
|---|---|---|
| **Packages** | Packages and prices sections | Name, price, timeframe, features (see below) |
| **Case studies** | Case studies sections | Client, description line, text, colour, screenshot and its description, link to the live site |
| **Questions** | Questions (FAQ) sections | The question and its answer |
| **Testimonials** | Testimonial carousels, cards and case studies | The quote and who said it |
| **Shared sections** | Shared section | A whole section of any type, e.g. *How it works (steps)* |

**Shared sections** are for sections that are the same everywhere, such as the numbered steps. Make one under
**Snippets → Shared sections → Add**: give it a name (only you see it) and build the section as you would on a page.
Then, on each page, add a **Shared section** and choose it. To change it on one page only, replace the Shared section
on that page with a normal section.

**Questions:** in an FAQ section, add a **Shared question** to use one from **Snippets → Questions**, or a
**One-off question** for something only this page needs. Each shared question shows the start of its answer in the
chooser, so two versions of the same question are easy to tell apart.

Snippets → **Usage** (on each snippet's page) lists the pages that use it.

## Packages

**Snippets → Packages.** Each package (Solo, Fringe, Show, Venue) is written once: name, who it's for, price, whether
it's a starting price (“from €3,500”), the text after the price, the timeframe and what's included (one per line).
Change a package there and it changes on every page that shows it, in the search engines' structured data and in
`/llms.txt`.

Pages choose packages in their **Packages and prices** sections. What can differ per page is only how the card is
shown: **featured** (the dark card), a **badge**, the **button text** (defaults to “Choose Solo” etc.) and link, and,
for the whole section, **Show approximate prices in pounds**.

**Prices in written copy.** Instead of typing a price, type a placeholder with the package's **code**:

| Type | Shows |
|---|---|
| `{solo.price}` | the Solo price, e.g. €500 |
| `{solo.pounds}` | its approximate pounds, e.g. £420 (empty if Site settings has no rate) |

The same works for `fringe`, `show` and `venue`. Placeholders work anywhere: titles, title tags, search and social
descriptions, every section's text, FAQ answers, and Site settings. The admin shows the placeholder; visitors,
previews, search engines and `/llms.txt` see the price. Write the words around it yourself, e.g.
`from {venue.price} (about {venue.pounds})`. A misspelt placeholder stays visible on the page, so check the preview.

## Testimonials

**Snippets → Testimonials.** A testimonial is written once and used wherever it's chosen:

- The **quote** is used in the home page carousel.
- The **short quote** (optional) is used in quote cards on landing pages.
- **Card colour** is the name card's background in the carousel.
- The **logo** shows at 60×60 pixels. SVG works best.

## Leads (form submissions)

**Leads → Inbox** in the left menu lists form submissions, newest first.

- Filter by form, or by whether it's handled. Search by name, email or any answer.
- Open a lead to read everything the person filled in. Tick **Handled** once you've replied, and save.
- **Download** (top right) exports the list as CSV or Excel.

Each new lead is also emailed to the address in **Settings → Site settings → Lead notification email**. Reply to
that email to answer the person directly. If the email ever fails, the lead is still saved here.

**Leads → Spam** holds submissions that look like spam, each with the reason. You get no email for these, and the
sender sees the usual thank-you message. If a real lead ends up there, open it, untick **Spam** and save: it moves
back to the inbox. Reasons include sending the form within a few seconds of opening the page, HTML or lots of links
in the answers, a call time the date and time pickers wouldn't allow, and more than five sends an hour from one
address. People with JavaScript turned off also land here, so glance at the list now and then.

## Footer

The footer on every page is edited in **Settings → Site settings → Footer**:

- **Footer introduction:** the sentence or two under the logo.
- **Button:** text and link (e.g. “Get a quote” → `/comedy/#quote`). Leave either empty to hide it.
- **Footer link columns:** titled groups of links, side by side (three fit best). Add, reorder or remove columns and
  links like page sections. Links take a path (`/edfringe/`), a section (`/comedy/#faq`) or a full address.

The bottom line shows the company name and the town and country from the **Search & AI** tab. If there are no
columns, the footer lists the pages ticked **Show in menus** instead.

## Site settings

**Settings → Site settings:**

- **Company name** in the footer copyright line, and the **KvK number** and **VAT number (BTW-nummer)** in the
  footer's bottom line (also given to search engines in the structured data)
- **Pounds per euro**, the rate for approximate pound prices (empty hides them)
- **Lead notification email** for form submissions
- **Default social image** for pages without their own

The **Search & AI**, **Footer** and **Verification & llms.txt** tabs are described in their own sections.

## Search engines and AI assistants

Everything search engines and AI assistants (ChatGPT, Perplexity, Google's AI answers...) read about the site is
edited in the admin. Nothing needs a developer.

**On each page (Promote tab):**

| Field | What it does |
|---|---|
| Title tag | The blue link in Google. Under about 60 characters, most important words first |
| Search description | The text under it. About 150 characters |
| Show in menus | Links the page from the footer of every page |
| Hide from search engines | `noindex`, and leaves the page out of `/sitemap.xml` and `/llms.txt`. For drafts-in-public or thank-you pages |
| Social sharing | Title, description and image for links shared on WhatsApp, LinkedIn, X... The image's **Description** (in **Images**) becomes its alt text |
| Structured data → Service name, Who it’s for, Areas served | Describe what the page sells. Together with the page's **Packages and prices** section they tell search engines your prices |
| Structured data → Extra structured data | Optional JSON-LD for anything not generated, e.g. an `Event`. Must be a JSON object |

The page's **Questions (FAQ)** sections are marked up as FAQs automatically, and the packages in its **Packages and prices**
section as offers with prices (`from` in the price prefix makes it a minimum price).

**For the whole site (Settings → Site settings):**

- **Search & AI:** the business's name, short name, description, logo, founder, where you're based, the countries
  and regions you work in, specialities and your profiles on other sites. These appear on every page as structured
  data, and the description opens `/llms.txt`.
- **Verification & llms.txt:** the codes from Google Search Console and Bing Webmaster Tools (paste only the code
  from their meta tag), and optional extra text for `/llms.txt`.

`/llms.txt` is a short summary of the site for AI assistants, built from these settings, the pages' titles and
descriptions, and their packages. It updates itself when you publish.

To check a page's structured data, paste its address into https://validator.schema.org/ or Google's Rich Results
Test (https://search.google.com/test/rich-results).

## Things to know

- The pricing buttons (and the timeline panel's button) scroll to the quote form and select its **I'm a…** option:
  package code `solo` or `fringe` selects Performer, `show` Showrunner and `venue` Venue owner. Visitors can still change it.
- The form fields themselves (questions and options) are also in the code, so they stay in step with the
  validation and the notification emails.
- Images you upload are resized automatically; upload at least 1120 pixels wide for the hero screenshot.
