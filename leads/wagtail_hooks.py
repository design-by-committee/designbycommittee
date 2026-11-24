from django.utils.functional import cached_property
from wagtail import hooks
from wagtail.admin.views.generic import IndexView
from wagtail.admin.viewsets.base import ViewSetGroup
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.permission_policies import ModelPermissionPolicy

from .models import FormSubmission


class LeadPermissionPolicy(ModelPermissionPolicy):
    """Leads come from the website forms only, so nobody can add one in the admin."""

    def user_has_permission(self, user, action):
        if action == "add":
            return False
        return super().user_has_permission(user, action)

    def user_has_any_permission(self, user, actions):
        return any(self.user_has_permission(user, action) for action in actions)


class InboxIndexView(IndexView):
    is_spam = False

    def get_base_queryset(self):
        return super().get_base_queryset().filter(is_spam=self.is_spam)


class SpamIndexView(InboxIndexView):
    is_spam = True


class LeadViewSet(ModelViewSet):
    """Real leads. Submissions flagged by the spam checks (leads/spam.py) are listed under Spam instead."""

    model = FormSubmission
    icon = "mail"
    menu_label = "Inbox"
    index_view_class = InboxIndexView

    list_display = ["name", "email", "get_form_name_display", "page_title", "submitted_at", "handled"]
    list_filter = ["form_name", "handled"]
    search_fields = ["name", "email", "answers"]
    search_backend_name = None  # plain database search, no search index needed
    ordering = ["-submitted_at"]

    list_export = ["submitted_at", "form_name", "name", "email", "page_title", "answers", "handled"]
    export_filename = "leads"

    # Everything else is what the visitor sent and stays read-only. Unticking Spam moves a lead back to the inbox.
    form_fields = ["handled", "is_spam"]

    inspect_view_enabled = True
    inspect_view_fields = [
        "submitted_at", "form_name", "name", "email", "page_title", "answers", "handled", "is_spam", "spam_reason"
    ]

    @cached_property
    def permission_policy(self):
        return LeadPermissionPolicy(self.model)


class SpamViewSet(LeadViewSet):
    icon = "warning"
    menu_label = "Spam"
    index_view_class = SpamIndexView
    list_display = ["name", "email", "get_form_name_display", "spam_reason", "submitted_at"]
    list_filter = ["form_name"]
    export_filename = "spam"


class LeadsGroup(ViewSetGroup):
    menu_label = "Leads"
    menu_icon = "mail"
    menu_order = 150
    items = [LeadViewSet("leads"), SpamViewSet("spam")]


@hooks.register("register_admin_viewset")
def register_lead_viewsets():
    return LeadsGroup()
