# Editing the site

How to change designbycommitt.ee in the Wagtail admin. Sign in at **/admin/** (on staging:
https://designbycommittee.onrender.com/admin/).

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

The page **title** is the link text in the footer menu, so keep titles short and descriptive (e.g. “Websites for
comedians”, not “Comedy”).

**Prices in pounds** are typed into each package's price suffix, e.g. “one-time fee (about £420)”, at about £0.83 to the
euro (November 2026). Update them if the exchange rate moves a lot.

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
| Hero with screenshot | Heading, intro, two buttons and a screenshot in a browser frame |
| Coloured cards | Audience cards, or case studies with a meta line and an optional link to the live site; optional quote card underneath |
| Columns | Short points side by side, each with an optional link |
| Timeline with checklist | A dated timeline next to a checklist panel with a button |
| Numbered steps | A process, numbered automatically |
| Packages and prices | Pricing cards; mark one as featured and give it a badge |
| Questions (FAQ) | Expandable questions and answers; leave a blank line in an answer to start a new paragraph |
| Quote request form | The enquiry form |
| Text | Free text with headings, lists and links |
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

## Site settings

**Settings → Site settings:**

- **Company name** in the footer copyright line
- **Lead notification email** for form submissions
- **Default social image** for pages without their own

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

The page's **Questions (FAQ)** sections are marked up as FAQs automatically, and its **Packages and prices**
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
