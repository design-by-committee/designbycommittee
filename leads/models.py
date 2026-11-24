from django.db import models


class FormSubmission(models.Model):
    """One submission of a lead form, listed in the admin under Leads."""

    class FormName(models.TextChoices):
        ASSESSMENT = "landing-page-assessment", "Landing page assessment"
        COMEDY_ENQUIRY = "comedy-enquiry", "Comedy enquiry"

    form_name = models.CharField("Form", max_length=50, choices=FormName.choices)
    page = models.ForeignKey(
        "wagtailcore.Page",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    page_title = models.CharField(max_length=255, blank=True, help_text="The page’s title when the form was sent.")
    name = models.CharField(max_length=255)
    email = models.EmailField()
    answers = models.TextField(help_text="Everything the person filled in.")
    data = models.JSONField(default=dict, help_text="The raw form values, keyed by field name.")
    submitted_at = models.DateTimeField("Received", auto_now_add=True, db_index=True)
    handled = models.BooleanField(default=False, help_text="Tick once you’ve replied.")
    is_spam = models.BooleanField(
        "Spam",
        default=False,
        db_index=True,
        help_text="Set by the spam checks (leads/spam.py). Untick to move a real lead back to Leads.",
    )
    spam_reason = models.CharField(max_length=500, blank=True, help_text="Why the spam checks flagged it.")
    ip_hash = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        editable=False,
        help_text="A keyed hash of the sender’s IP address, for rate limiting. The address itself isn’t stored.",
    )

    class Meta:
        ordering = ["-submitted_at"]
        verbose_name = "lead"
        verbose_name_plural = "leads"

    def __str__(self):
        return f"{self.name} ({self.get_form_name_display()}, {self.submitted_at:%d %b %Y})"
