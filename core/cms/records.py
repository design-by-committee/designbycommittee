"""Snippets, settings, redirects, sites, leads and users for the `cms` command.

Creates and edits go through the same forms the Wagtail admin uses for each of these, so validation matches.
"""

import csv
import io

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from wagtail.admin.panels import get_edit_handler
from wagtail.contrib.redirects.forms import RedirectForm
from wagtail.contrib.redirects.models import Redirect
from wagtail.contrib.settings.registry import registry as settings_registry
from wagtail.models import ReferenceIndex, Site
from wagtail.sites.forms import SiteForm
from wagtail.snippets.models import get_snippet_models

from .base import REVISION_USERNAME, CmsError, actor, dump, format_changes, log_action, record, save_with_form


class Resource:
    """A model that can be listed, shown, created, updated and deleted with an admin form."""

    log_prefix = "wagtail"
    list_fields = None

    def __init__(self, model, form_class, *, label=None, list_fields=None, deletable=True, form_kwargs=None):
        self.model = model
        self.form_class = form_class
        self.label = label or model._meta.verbose_name
        self.list_fields = list_fields
        self.deletable = deletable
        self.form_kwargs = form_kwargs or {}

    def get(self, pk):
        obj = self.model._default_manager.filter(pk=pk).first()
        if obj is None:
            raise CmsError(f"No {self.label} with id {pk}.")
        return obj

    def list(self, queryset=None):
        rows = queryset if queryset is not None else self.model._default_manager.all()
        return dump([{"id": obj.pk, "str": str(obj), **record(obj, self.list_fields)} for obj in rows])

    def show(self, pk):
        obj = self.get(pk)
        data = {"id": obj.pk, "str": str(obj), **record(obj)}
        references = ReferenceIndex.get_references_to(obj).count()
        if references:
            data["used_in_places"] = references
        return dump(data)

    def create(self, values):
        obj, changed = save_with_form(self.form_class, self.model(), values, form_kwargs=self.form_kwargs)
        log_action(obj, "wagtail.create")
        return f"Created {self.label} {obj.pk}: {obj}\n{format_changes(changed)}"

    def update(self, pk, values):
        obj, changed = save_with_form(self.form_class, self.get(pk), values, form_kwargs=self.form_kwargs)
        if changed:
            log_action(obj, "wagtail.edit")
        return f"Updated {self.label} {obj.pk}: {obj}\n{format_changes(changed)}"

    def delete(self, pk, force=False):
        if not self.deletable:
            raise CmsError(f"{self.label} records can't be deleted here.")
        obj = self.get(pk)
        references = ReferenceIndex.get_references_to(obj).count()
        if references and not force:
            raise CmsError(f"{self.label} {pk} ({obj}) is used in {references} place(s). Add --force to delete it anyway.")
        description = str(obj)
        log_action(obj, "wagtail.delete")
        obj.delete()
        return f"Deleted {self.label} {pk}: {description}"


def edit_handler_form(model):
    """The form class the Wagtail admin builds from a model's panels."""
    return get_edit_handler(model).get_form_class()


# Snippets -----------------------------------------------------------------------------------------------------------


def snippet_types():
    return dump([{"type": model._meta.model_name, "name": str(model._meta.verbose_name_plural)} for model in get_snippet_models()])


def snippet(type_name):
    for model in get_snippet_models():
        if type_name.lower() in (model._meta.model_name, model.__name__.lower()):
            return Resource(model, edit_handler_form(model), form_kwargs={"for_user": actor()})
    types = ", ".join(model._meta.model_name for model in get_snippet_models())
    raise CmsError(f"No snippet type {type_name!r}. Types: {types}.")


# Settings -----------------------------------------------------------------------------------------------------------


def _setting_model(name):
    for model in settings_registry:
        if name.lower() in (model._meta.model_name, model.__name__.lower()):
            return model
    raise CmsError(f"No setting {name!r}. Settings: {', '.join(m._meta.model_name for m in settings_registry)}.")


def _site(hostname=None):
    if hostname:
        site = Site.objects.filter(hostname=hostname).first()
        if site is None:
            raise CmsError(f"No site {hostname!r}. Sites: {', '.join(Site.objects.values_list('hostname', flat=True))}.")
        return site
    return Site.objects.get(is_default_site=True)


def settings_list():
    return dump([{"setting": model._meta.model_name, "name": str(model._meta.verbose_name)} for model in settings_registry])


def settings_show(name, hostname=None):
    model = _setting_model(name)
    instance = model.for_site(_site(hostname)) if hasattr(model, "for_site") else model.load()
    return dump(record(instance))


def settings_update(name, values, hostname=None):
    model = _setting_model(name)
    instance = model.for_site(_site(hostname)) if hasattr(model, "for_site") else model.load()
    obj, changed = save_with_form(edit_handler_form(model), instance, values, form_kwargs={"for_user": actor()})
    if changed:
        log_action(obj, "wagtail.edit")
    return f"Updated {model._meta.verbose_name}\n{format_changes(changed)}"


# Redirects and sites ------------------------------------------------------------------------------------------------

redirects = Resource(
    Redirect,
    RedirectForm,
    label="redirect",
    list_fields=["old_path", "site", "is_permanent", "redirect_page", "redirect_link"],
    form_kwargs={"for_user": None},
)

sites = Resource(Site, SiteForm, label="site", list_fields=["hostname", "port", "site_name", "root_page", "is_default_site"])


# Leads --------------------------------------------------------------------------------------------------------------


def _leads():
    from leads.models import FormSubmission

    class LeadForm(forms.ModelForm):
        class Meta:
            model = FormSubmission
            fields = ["handled"]  # what the admin lets you change; the rest is what the visitor sent

    return Resource(
        FormSubmission,
        LeadForm,
        label="lead",
        list_fields=["submitted_at", "form_name", "name", "email", "page_title", "handled"],
    )


def leads_resource():
    return _leads()


def leads_list(form_name=None, unhandled=False, since=None, limit=50):
    resource = _leads()
    queryset = resource.model.objects.all()
    if form_name:
        queryset = queryset.filter(form_name=form_name)
    if unhandled:
        queryset = queryset.filter(handled=False)
    if since:
        queryset = queryset.filter(submitted_at__date__gte=since)
    return resource.list(queryset[:limit])


def leads_export(form_name=None):
    resource = _leads()
    queryset = resource.model.objects.order_by("submitted_at")
    if form_name:
        queryset = queryset.filter(form_name=form_name)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["received", "form", "name", "email", "page", "answers", "handled"])
    for lead in queryset:
        writer.writerow(
            [lead.submitted_at.isoformat(), lead.form_name, lead.name, lead.email, lead.page_title, lead.answers, lead.handled]
        )
    return out.getvalue()


# Users --------------------------------------------------------------------------------------------------------------

USER_FIELDS = ["username", "email", "first_name", "last_name", "is_active", "is_superuser"]


class UserForm(forms.ModelForm):
    """Profile, status and groups. Passwords are never set here: people set their own with "Forgot password"."""

    groups = forms.ModelMultipleChoiceField(queryset=Group.objects.all(), required=False)

    class Meta:
        model = get_user_model()
        fields = [*USER_FIELDS, "groups"]

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk and self.instance.username == REVISION_USERNAME:
            raise forms.ValidationError("The claude user is managed by this tool and can't be edited.")
        if not cleaned.get("email"):
            self.add_error("email", "An email address is needed so the person can set a password.")
        was_admin = self.instance.pk and self.instance.is_superuser and self.instance.is_active
        if was_admin and not (cleaned.get("is_superuser") and cleaned.get("is_active")):
            others = (
                get_user_model()
                .objects.filter(is_superuser=True, is_active=True)
                .exclude(pk=self.instance.pk)
                .exclude(username=REVISION_USERNAME)
            )
            if not others.exists():
                raise forms.ValidationError("That's the last active superuser; this would lock everyone out of the admin.")
        return cleaned


def users_resource():
    return Resource(get_user_model(), UserForm, label="user", list_fields=[*USER_FIELDS, "last_login"], deletable=True)


def users_list():
    users = get_user_model().objects.exclude(username=REVISION_USERNAME).order_by("username")
    return dump(
        [
            {**record(user, [*USER_FIELDS, "last_login"]), "groups": list(user.groups.values_list("name", flat=True))}
            for user in users
        ]
    )


def users_create(values):
    obj, changed = save_with_form(UserForm, get_user_model()(), values)
    obj.set_unusable_password()
    obj.save(update_fields=["password"])
    log_action(obj, "wagtail.create")
    return (
        f"Created user {obj.username} (id {obj.pk}) without a password.\n{format_changes(changed)}\n"
        "They can set one with “Forgot password?” on /admin/login/ (the reset email goes to their address)."
    )


def users_delete(pk, force=False):
    User = get_user_model()
    user = users_resource().get(pk)
    if user.username == REVISION_USERNAME:
        raise CmsError("The claude user can't be deleted here.")
    if user.is_superuser and User.objects.filter(is_superuser=True, is_active=True).exclude(pk=user.pk).count() == 0:
        raise CmsError("That's the last active superuser; deleting it would lock everyone out of the admin.")
    if not force:
        raise CmsError(f"Deleting {user.username} also removes their authorship records. Deactivate instead "
                       f"(`cms users update {pk} --data '{{\"is_active\": false}}'`), or add --force.")
    return users_resource().delete(pk, force=True)


def groups_list():
    return dump([{"id": group.pk, "name": group.name, "users": group.user_set.count()} for group in Group.objects.all()])


def users_show(pk):
    """A user's profile, status and groups. Never the password hash."""
    user = users_resource().get(pk)
    return dump(
        {
            **record(user, [*USER_FIELDS, "last_login", "date_joined"]),
            "groups": list(user.groups.values_list("name", flat=True)),
            "has_password": user.has_usable_password(),
        }
    )
