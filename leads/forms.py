"""The site's two lead forms.

Field names match the original Netlify forms (including hyphenated names such as "first-name"), so the HTML,
the JavaScript and exported submissions keep the same keys. Labels and choices are defined here once and used by
the templates, the notification email and the admin.
"""

from django import forms

HONEYPOT = "bot-field"


class LeadForm(forms.Form):
    """Base for lead forms: a honeypot field, and helpers to describe a submission."""

    form_name = ""  # matches the form's form-name / HTML name attribute
    title = ""

    def is_spam(self):
        return bool(self.data.get(HONEYPOT))

    def submitter(self):
        """(name, email) for listing the submission."""
        raise NotImplementedError

    def answer_items(self):
        """(label, value) pairs of what the visitor filled in, in form order. Empty fields and unticked boxes are
        left out; ticked boxes read "Yes" and choices show their label."""
        items = []
        for name, field in self.fields.items():
            if name == HONEYPOT:
                continue
            value = self.cleaned_data.get(name)
            if isinstance(field, forms.BooleanField):
                if not value:
                    continue
                value = "Yes"
            elif isinstance(field, forms.ChoiceField):
                value = dict(field.choices).get(value, value)
            if value in (None, ""):
                continue
            items.append((field.label, str(value).strip()))
        return items

    def answers(self):
        """Compact "Label: value" lines, stored with the submission for the admin and exports."""
        return "\n".join(f"{label}: {value}" for label, value in self.answer_items())

    def email_answers(self):
        """The answers for the notification email, with a blank line between fields so they're easy to tell apart."""
        return "\n\n".join(f"{label}: {value}" for label, value in self.answer_items())


def build_form(class_name, base, fields):
    """Create a form class from a dict, so fields can keep hyphenated HTML names."""
    attrs = {HONEYPOT: forms.CharField(required=False, label="Leave this empty if you’re human")}
    attrs.update(fields)
    return type(base)(class_name, (base,), attrs)


# Landing page assessment (home page) -------------------------------------------------------------------------------

ASSESSMENT_INTERESTS = [
    # (field name, label, checked by default)
    ("factors", "Discover which factors have the most powerful influence on my visitors", True),
    ("offer", "Test a new offer or price point on my landing page", False),
    ("ux", "Update my landing page to fix UX issues and increase conversions", False),
    ("cpa", "Lower the average cost-per-acquisition (CPA) in my ad campaigns", False),
    ("mobile", "Optimize my landing page to convert on mobile devices", False),
    ("content", "Personalize my content to more closely match my visitor’s intent", False),
    ("speed", "Reduce load time on my landing page to improve PageSpeed scores", False),
    ("ai", "Utilize machine learning to identify new opportunities for growth", False),
]


class AssessmentFormBase(LeadForm):
    form_name = "landing-page-assessment"
    title = "Landing page assessment"

    def clean(self):
        cleaned = super().clean()
        if not any(cleaned.get(name) for name, _label, _checked in ASSESSMENT_INTERESTS):
            raise forms.ValidationError("Check at least one thing you want to do.", code="no_interest")
        return cleaned

    def submitter(self):
        name = f"{self.cleaned_data['first-name']} {self.cleaned_data['last-name']}".strip()
        return name, self.cleaned_data["email"]


AssessmentForm = build_form(
    "AssessmentForm",
    AssessmentFormBase,
    {
        "url": forms.URLField(label="Landing page URL", max_length=500, assume_scheme="https"),
        **{
            name: forms.BooleanField(label=label, required=False, initial=checked)
            for name, label, checked in ASSESSMENT_INTERESTS
        },
        "details": forms.CharField(label="Project details", required=False, max_length=5000),
        "first-name": forms.CharField(label="First name", max_length=150),
        "last-name": forms.CharField(label="Last name", max_length=150),
        "email": forms.EmailField(label="Email"),
        "date": forms.CharField(label="Preferred date", max_length=20),
        "time": forms.CharField(label="Preferred time", max_length=20),
        "timezone": forms.CharField(label="Time zone", required=False, max_length=100),
    },
)


# Comedy enquiry (/comedy/) -----------------------------------------------------------------------------------------

CLIENT_TYPES = [(label, label) for label in ["Performer", "Showrunner", "Venue owner", "Something else"]]


class ComedyEnquiryFormBase(LeadForm):
    form_name = "comedy-enquiry"
    title = "Comedy enquiry"

    def submitter(self):
        return self.cleaned_data["name"], self.cleaned_data["email"]


ComedyEnquiryForm = build_form(
    "ComedyEnquiryForm",
    ComedyEnquiryFormBase,
    {
        "name": forms.CharField(label="Your name", max_length=200),
        "email": forms.EmailField(label="Email"),
        "client-type": forms.ChoiceField(label="I’m a…", choices=CLIENT_TYPES),
        "link": forms.CharField(label="Current website, if any", required=False, max_length=500),
        "details": forms.CharField(label="Tell us about your show, venue or act", required=False, max_length=5000),
    },
)


FORMS = {form.form_name: form for form in (AssessmentForm, ComedyEnquiryForm)}
