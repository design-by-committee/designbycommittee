# Editing the site

How to change designbycommitt.ee in the Wagtail admin. Sign in at **/admin/** (on staging:
https://designbycommittee.onrender.com/admin/).

## Pages

| Page | Address | Page type |
|---|---|---|
| Home | `/` | Home page: the original agency design |
| Comedy | `/comedy/` | Landing page: full-width sections |

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
- Comedy: `fringe`, `packages`, `work`, `faq` and `quote` (header links and buttons point at them)

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
| Coloured cards | Audience cards, or case studies with a meta line; optional quote card underneath |
| Columns | Short points side by side, each with an optional link |
| Timeline with checklist | A dated timeline next to a checklist panel with a button |
| Numbered steps | A process, numbered automatically |
| Packages and prices | Pricing cards; mark one as featured and give it a badge |
| Questions (FAQ) | Expandable questions and answers |
| Quote request form | The enquiry form |
| Text | Free text with headings, lists and links |

Each landing page section can have a **Light**, **Paper** or **Dark** background.

## New landing page

1. **Pages → Home → ⋯ → Add child page → Landing page.**
2. Fill in the title and add sections. On the **Promote** tab, set the **Slug** (the address, e.g. `festivals` for
   `/festivals/`), the **Title tag** and **Search description**, and optionally the **Social sharing** fields.
3. Add **Header links** for the sections you want in the top menu, and a **Header button** (usually `#quote`).
4. Publish.

## Testimonials

**Snippets → Testimonials.** A testimonial is written once and used wherever it's chosen:

- The **quote** is used in the home page carousel.
- The **short quote** (optional) is used in quote cards on landing pages.
- **Card colour** is the name card's background in the carousel.
- The **logo** shows at 60×60 pixels. SVG works best.

## Leads (form submissions)

**Leads** in the left menu lists every form submission, newest first.

- Filter by form, or by whether it's handled. Search by name, email or any answer.
- Open a lead to read everything the person filled in. Tick **Handled** once you've replied, and save.
- **Download** (top right) exports the list as CSV or Excel.

Each new lead is also emailed to the address in **Settings → Site settings → Lead notification email**. Reply to
that email to answer the person directly. If the email ever fails, the lead is still saved here.

## Site settings

**Settings → Site settings:**

- **Company name** in the footer copyright line
- **Lead notification email** for form submissions
- **Default social image** for pages without their own

## Things to know

- The package codes (`solo`, `show`, `venue`) connect the pricing buttons to the **Package** dropdown in the quote
  form. The dropdown's options are part of the site's code; ask for a change if you add or rename packages.
- The form fields themselves (questions and options) are also in the code, so they stay in step with the
  validation and the notification emails.
- Images you upload are resized automatically; upload at least 1120 pixels wide for the hero screenshot.
