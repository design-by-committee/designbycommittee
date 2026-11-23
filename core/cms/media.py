"""Images and documents for the `cms` command, through the same forms as the admin's upload and edit screens.

Uploads come from a file on the server or from stdin (`--file -` with `--filename`). Unlike other operations, these
aren't dry-run by rolling back a transaction, because files on disk aren't part of the transaction: a dry run only
validates, and deletes are refused without --apply.
"""

import os
import sys

from django.core.files.uploadedfile import SimpleUploadedFile
from wagtail.documents import get_document_model
from wagtail.documents.forms import get_document_form
from wagtail.images import get_image_model
from wagtail.images.forms import get_image_form
from wagtail.models import ReferenceIndex

from .base import CmsError, dump, format_changes, log_action, record, save_with_form

LIST_FIELDS = {"image": ["title", "file", "width", "height", "collection", "created_at"], "document": ["title", "file", "collection", "created_at"]}


def _kind(kind):
    if kind == "image":
        model = get_image_model()
        return model, get_image_form(model)
    if kind == "document":
        model = get_document_model()
        return model, get_document_form(model)
    raise CmsError("Use images or documents.")


def _get(model, pk):
    obj = model.objects.filter(pk=pk).first()
    if obj is None:
        raise CmsError(f"No {model._meta.verbose_name} with id {pk}.")
    return obj


def _upload(file_arg, filename):
    """A file for the form, from a path on this machine or stdin ("-")."""
    if file_arg == "-":
        if not filename:
            raise CmsError("With --file - (stdin), give the file name with --filename, e.g. --filename photo.jpg")
        content = sys.stdin.buffer.read()
    else:
        try:
            with open(file_arg, "rb") as f:
                content = f.read()
        except OSError as error:
            raise CmsError(f"Couldn't read {file_arg}: {error}") from None
        filename = filename or os.path.basename(file_arg)
    if not content:
        raise CmsError("The file is empty.")
    return SimpleUploadedFile(filename, content)


def list_items(kind, search=None, limit=50):
    model, _form = _kind(kind)
    queryset = model.objects.order_by("-created_at")
    if search:
        queryset = queryset.filter(title__icontains=search)
    rows = []
    for obj in queryset[:limit]:
        row = record(obj, LIST_FIELDS[kind])
        row["tags"] = list(obj.tags.names())
        row["url"] = obj.file.url if obj.file else None
        rows.append(row)
    return dump(rows)


def show(kind, pk):
    model, _form = _kind(kind)
    obj = _get(model, pk)
    data = {**record(obj), "tags": list(obj.tags.names()), "url": obj.file.url if obj.file else None}
    data["used_in_places"] = ReferenceIndex.get_references_to(obj).count()
    return dump(data)


def upload(kind, values, file_arg, filename, apply):
    model, form_class = _kind(kind)
    upload_file = _upload(file_arg, filename)
    values = {"title": os.path.splitext(upload_file.name)[0], **(values or {})}
    if not apply:
        form = _bound(form_class, model(), values, upload_file)
        if not form.is_valid():
            raise CmsError(f"Not valid: {form.errors.get_json_data()}")
        return f"Dry run: {upload_file.name} ({len(upload_file)} bytes) is a valid {kind} upload. Add --apply to upload it."
    obj, changed = save_with_form(form_class, model(), values, files={"file": upload_file})
    log_action(obj, "wagtail.create")
    return f"Uploaded {kind} {obj.pk}: {obj.title} ({obj.file.url})\n{format_changes(changed)}"


def update(kind, pk, values, file_arg, filename, apply):
    model, form_class = _kind(kind)
    obj = _get(model, pk)
    files = {"file": _upload(file_arg, filename)} if file_arg else None
    if not apply:
        form = _bound(form_class, obj, values, files and files["file"])
        if not form.is_valid():
            raise CmsError(f"Not valid: {form.errors.get_json_data()}")
        return f"Dry run: the changes to {kind} {pk} are valid. Add --apply to save them."
    obj, changed = save_with_form(form_class, obj, values or {}, files=files)
    if changed or files:
        log_action(obj, "wagtail.edit")
    replaced = " (file replaced)" if files else ""
    return f"Updated {kind} {obj.pk}: {obj.title}{replaced}\n{format_changes(changed)}"


def delete(kind, pk, apply, force=False):
    model, _form = _kind(kind)
    obj = _get(model, pk)
    references = ReferenceIndex.get_references_to(obj).count()
    if references and not force:
        raise CmsError(f"{kind.title()} {pk} ({obj.title}) is used in {references} place(s). Add --force to delete it anyway.")
    if not apply:
        return f"Dry run: would delete {kind} {pk} ({obj.title}) and its file. Add --apply to delete it."
    title = obj.title
    log_action(obj, "wagtail.delete")
    obj.delete()
    return f"Deleted {kind} {pk}: {title}"


def _bound(form_class, instance, values, upload_file):
    from .base import _form_value, form_data

    unbound = form_class(instance=instance)
    data = {**form_data(unbound), **{name: _form_value(value, unbound.fields.get(name)) for name, value in (values or {}).items()}}
    data = {name: value for name, value in data.items() if value is not None and value is not False}
    return form_class(data=data, files={"file": upload_file} if upload_file else {}, instance=instance)
