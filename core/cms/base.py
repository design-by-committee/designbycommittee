"""Shared pieces of the `cms` management command: the "claude" user, dry runs, input data and admin forms.

Every change goes through the same Wagtail APIs and admin forms as the admin itself, so it's validated the same way
and appears in the page History / Reports → Site history under "Claude (command line)".
"""

import contextlib
import json
import sys
from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.forms.models import model_to_dict
from wagtail.log_actions import log

REVISION_USERNAME = "claude"


class CmsError(Exception):
    """An operation that can't be done; the message says why."""


class DryRun(Exception):
    """Raised inside `changes()` to roll back the transaction after a successful dry run."""


def actor():
    """The admin user Claude's changes are recorded under. It has no password and can't sign in."""
    user, created = get_user_model().objects.get_or_create(
        username=REVISION_USERNAME,
        defaults={"first_name": "Claude", "last_name": "(command line)", "is_active": False},
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user


@contextlib.contextmanager
def changes(apply):
    """Run database changes in a transaction that is rolled back unless `apply` is true.

    The operation runs for real either way, so a dry run catches every error a real run would (validation, tree
    rules, unique slugs, ...). Only use this for database-only operations: file deletions are not rolled back.
    """
    try:
        with transaction.atomic():
            yield
            if not apply:
                raise DryRun
    except DryRun:
        pass


def load_data(data=None, data_file=None, default=None):
    """JSON from --data (a string) or --data-file (a path, or - for stdin)."""
    if data is not None and data_file is not None:
        raise CmsError("Use --data or --data-file, not both.")
    try:
        if data is not None:
            return json.loads(data)
        if data_file is not None:
            if data_file == "-":
                return json.load(sys.stdin)
            with open(data_file, encoding="utf-8") as f:
                return json.load(f)
    except (OSError, json.JSONDecodeError) as error:
        raise CmsError(f"Couldn't read the JSON data: {error}") from None
    if default is not None:
        return default
    raise CmsError("Give the data with --data '{...}' or --data-file PATH (- for stdin).")


def to_json(value):
    """Make model values printable as JSON."""
    if isinstance(value, models.Model):
        return value.pk
    if hasattr(value, "stream_block") and hasattr(value, "get_prep_value"):
        # A StreamField: its stored blocks. str() would render it, and sections such as a quote form need a page.
        return value.get_prep_value()
    if isinstance(value, (list, tuple, set)):
        return [to_json(item) for item in value]
    if isinstance(value, dict):
        return {key: to_json(item) for key, item in value.items()}
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "name") and hasattr(value, "url"):  # files
        return value.name or None
    return value


def dump(data):
    return json.dumps(to_json(data), indent=2, ensure_ascii=False, default=str)


def record(instance, fields=None):
    """A model instance's field values as JSON-ready data."""
    data = {"id": instance.pk, **model_to_dict(instance, fields=fields)}
    return to_json(data)


def form_data(form):
    """POST-style data for a model form, taken from the instance's current values."""
    from django.forms import FileField

    data = {}
    for name, field in form.fields.items():
        if isinstance(field, FileField):
            continue  # files go in the `files` argument; leaving them out keeps the current file
        value = form.initial.get(name, field.initial)
        if callable(value):
            value = value()
        if name == "tags" or field.__class__.__name__ == "TagField":
            names = [getattr(tag, "name", tag) for tag in (value or [])]
            value = ", ".join(f'"{name}"' if " " in name else name for name in names)
        elif isinstance(value, models.Model):
            value = value.pk
        elif isinstance(value, (list, tuple)) and value and isinstance(value[0], models.Model):
            value = [item.pk for item in value]
        if value is None:
            continue  # an empty value; leave it out like a browser would
        data[name] = value
    return data


def _is_stream_field(field):
    return field.__class__.__name__ == "BlockField"


def save_with_form(form_class, instance, values, *, files=None, form_kwargs=None):
    """Validate `values` (a partial dict of field values) with the admin form for `instance` and save it.

    StreamField values (e.g. Site settings' footer columns) are raw block data, as `cms pages show` prints them. The
    admin's StreamField widget posts a different, prefixed format, so these skip the HTML form: they're validated by
    the field's own blocks (the same `clean()` the editor runs) and set on the instance before it's saved.

    Returns (saved instance, {field: (before, after)}) for the fields that changed. Raises CmsError with the
    form's errors if the values don't validate.
    """
    if not isinstance(values, dict):
        raise CmsError("The data must be a JSON object of field names and values.")
    form_kwargs = form_kwargs or {}
    unbound = form_class(instance=instance, **form_kwargs)
    unknown = set(values) - set(unbound.fields)
    if unknown:
        raise CmsError(f"Unknown field(s): {', '.join(sorted(unknown))}. Fields: {', '.join(unbound.fields)}.")
    streams = [name for name, field in unbound.fields.items() if _is_stream_field(field)]

    def drop_streams(form):
        for name in streams:
            del form.fields[name]
        return form

    def stream_snapshot(obj):
        return {name: json.dumps(getattr(obj, name).get_prep_value(), ensure_ascii=False) for name in streams}

    before = {**form_data(drop_streams(form_class(instance=instance, **form_kwargs))), **stream_snapshot(instance)}
    plain_values = {name: value for name, value in values.items() if name not in streams}
    data = {**form_data(drop_streams(form_class(instance=instance, **form_kwargs)))}
    data.update({name: _form_value(value, unbound.fields[name]) for name, value in plain_values.items()})
    data = {name: value for name, value in data.items() if value is not None and value is not False}
    form = drop_streams(form_class(data=data, files=files or {}, instance=instance, **form_kwargs))
    if not form.is_valid():
        raise CmsError(f"Not valid: {json.dumps(form.errors.get_json_data(), ensure_ascii=False)}")

    stream_values = [name for name in streams if name in values]
    if not stream_values:
        saved = form.save()
    else:
        saved = form.save(commit=False)
    for name in stream_values:
        stream_block = instance._meta.get_field(name).stream_block
        try:
            cleaned = stream_block.clean(stream_block.to_python(values[name] or []))
        except ValidationError as error:
            raise CmsError(f"Not valid: {name}: {'; '.join(error.messages)}") from None
        setattr(saved, name, cleaned)
    if stream_values:
        saved.save()
        form.save_m2m()

    after = {**form_data(drop_streams(form_class(instance=saved, **form_kwargs))), **stream_snapshot(saved)}
    changed = {
        name: (before.get(name), after.get(name)) for name in sorted(set(before) | set(after)) if before.get(name) != after.get(name)
    }
    return saved, changed


def _form_value(value, field=None):
    if field is not None and field.__class__.__name__ == "TagField" and isinstance(value, list):
        return ", ".join(f'"{tag}"' if " " in tag else tag for tag in value)  # the tag widget's format
    if value is True:
        return "on"
    if value is False:
        return False  # dropped below: an unticked checkbox is absent from POST data
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    return value


def log_action(instance, action):
    """Add an entry to Wagtail's audit log (Reports → Site history), as the admin does."""
    log(instance=instance, action=action, user=actor())


def format_changes(changed):
    if not changed:
        return "No changes."
    width = max(len(name) for name in changed)
    show = lambda value: json.dumps(to_json(value), ensure_ascii=False, default=str)  # noqa: E731
    return "\n".join(f"{name.ljust(width)}  {show(b)} → {show(a)}" for name, (b, a) in changed.items())
