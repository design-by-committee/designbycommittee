from django.utils.functional import cached_property
from wagtail import hooks
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


class LeadViewSet(ModelViewSet):
    model = FormSubmission
    icon = "mail"
    menu_label = "Leads"
    menu_order = 150
    add_to_admin_menu = True

    list_display = ["name", "email", "get_form_name_display", "page_title", "submitted_at", "handled"]
    list_filter = ["form_name", "handled"]
    search_fields = ["name", "email", "answers"]
    search_backend_name = None  # plain database search, no search index needed
    ordering = ["-submitted_at"]

    list_export = ["submitted_at", "form_name", "name", "email", "page_title", "answers", "handled"]
    export_filename = "leads"

    form_fields = ["handled"]  # everything else is what the visitor sent and stays read-only

    inspect_view_enabled = True
    inspect_view_fields = ["submitted_at", "form_name", "name", "email", "page_title", "answers", "handled"]

    @cached_property
    def permission_policy(self):
        return LeadPermissionPolicy(self.model)


@hooks.register("register_admin_viewset")
def register_lead_viewset():
    return LeadViewSet("leads")
