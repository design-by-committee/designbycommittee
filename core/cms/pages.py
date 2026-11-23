"""Page operations for the `cms` command, using Wagtail's own page actions (as the admin does)."""

import json

from django.apps import apps
from django.utils import timezone
from wagtail.actions.delete_page import DeletePageAction
from wagtail.actions.move_page import MovePageAction
from wagtail.actions.revert_to_page_revision import RevertToPageRevisionAction
from wagtail.actions.unpublish_page import UnpublishPageAction
from wagtail.models import Page, ReferenceIndex

from pages.content_ops import ContentError, apply_changes, describe, diff, find_page, page_tree, snapshot

from .base import REVISION_USERNAME, CmsError, actor, dump, log_action


def _page(ref):
    try:
        return find_page(ref)
    except ContentError as error:
        raise CmsError(str(error)) from None


def _others_draft(page):
    latest = page.get_latest_revision()
    if page.has_unpublished_changes and latest is not None and getattr(latest.user, "username", None) != REVISION_USERNAME:
        return latest
    return None


def list_pages():
    return dump(page_tree())


def show(ref, live=False):
    page = _page(ref)
    content = page if live else page.get_latest_revision_as_object()
    return dump({"page": describe(page, live=live), **snapshot(content)})


def edit(ref, changes_data, *, draft, publish, include_others_draft):
    """Apply a list of content operations (see pages/content_ops.py). Dry run unless draft or publish."""
    page = _page(ref)
    if page.locked:
        raise CmsError(f"{page.url} is locked in the admin. Unlock it first.")
    notes = []
    others = _others_draft(page)
    if others:
        notes.append(f"Note: {page.url} has unpublished changes by {others.user or 'someone'}; these changes build on that draft.")
        if publish and not include_others_draft:
            raise CmsError("Publishing would also publish that draft. Use --draft instead, or add --include-others-draft.")

    editable = page.get_latest_revision_as_object()
    before = snapshot(editable)
    try:
        edited = apply_changes(editable, changes_data)
    except ContentError as error:
        raise CmsError(str(error)) from None
    changes_diff = diff(before, snapshot(edited))
    if not changes_diff:
        return "\n".join([*notes, "No differences; nothing to save."])
    if not (draft or publish):
        return "\n".join([*notes, changes_diff, "", "Dry run: valid, nothing saved. Add --draft or --publish to save."])

    revision = edited.save_revision(user=actor(), log_action=True)
    if publish:
        revision.publish(user=actor(), skip_permission_checks=True)
    action = "Published" if publish else f"Saved as a draft (review: /admin/pages/{page.pk}/edit/)"
    return "\n".join([*notes, changes_diff, "", f"{action}: {page.url}, revision {revision.pk}."])


def create(parent_ref, page_type, values, *, draft, publish):
    """Create a page under `parent_ref` from {"title", "slug", other fields, and stream fields as block lists}."""
    parent = _page(parent_ref)
    model = _page_model(page_type)
    if model not in parent.specific_class.allowed_subpage_models():
        allowed = ", ".join(m.__name__ for m in parent.specific_class.allowed_subpage_models()) or "none"
        raise CmsError(f"A {model.__name__} can't go under {parent.url}. Allowed there: {allowed}.")
    if not model.can_create_at(parent):
        raise CmsError(f"Can't create another {model.__name__} there (it may be limited to one).")
    if not isinstance(values, dict) or not values.get("title"):
        raise CmsError('The data needs at least a "title".')

    page = model(owner=actor(), live=False, has_unpublished_changes=True)
    stream_ops = []
    from pages.content_ops import EDITABLE_FIELDS, stream_field_names

    streams = stream_field_names(page)
    for name, value in values.items():
        if name in streams:
            for block in value or []:
                if not isinstance(block, dict) or "type" not in block:
                    raise CmsError(f'Each block in "{name}" needs a "type" and a "value".')
                stream_ops.append({"op": "insert", "stream": name, "type": block["type"], "value": block.get("value")})
        elif name in EDITABLE_FIELDS:
            setattr(page, name, value)
        else:
            raise CmsError(f"Unknown field {name!r}. Fields: {', '.join(sorted(EDITABLE_FIELDS | set(streams)))}.")
    if not page.slug:
        from django.utils.text import slugify

        page.slug = slugify(page.title)

    if stream_ops:
        try:
            apply_changes(page, stream_ops, validate_page=False)  # the page is validated when it's added below
        except ContentError as error:
            raise CmsError(str(error)) from None
    parent.add_child(instance=page)
    revision = page.save_revision(user=actor(), log_action=False)
    log_action(page, "wagtail.create")
    if publish:
        revision.publish(user=actor(), skip_permission_checks=True)
    state = "published" if publish else "saved as a draft" if draft else "would be created (dry run)"
    return f"{model.__name__} “{page.title}” at {_where(page)} {state}."


def _page_model(name):
    for model in apps.get_models():
        if issubclass(model, Page) and model is not Page and model.__name__.lower() == str(name).lower():
            return model
    types = ", ".join(m.__name__ for m in apps.get_models() if issubclass(m, Page) and m is not Page)
    raise CmsError(f"No page type {name!r}. Types: {types}.")


def publish(ref):
    page = _page(ref)
    revision = page.get_latest_revision()
    if revision is None:
        raise CmsError(f"{page.url} has no revisions to publish.")
    if page.live and not page.has_unpublished_changes:
        return f"{page.url} is already live and has no unpublished changes."
    revision.publish(user=actor(), skip_permission_checks=True)
    return f"Published {page.url}: revision {revision.pk} by {revision.user or 'unknown'} ({revision.created_at:%d %b %Y %H:%M})."


def unpublish(ref, include_descendants=False):
    page = _page(ref)
    _protect_root(page, "unpublish")
    if not page.live:
        return f"{page.url} is already unpublished."
    UnpublishPageAction(page, user=actor(), include_descendants=include_descendants).execute(skip_permission_checks=True)
    return f"Unpublished {page.title} ({_where(page)})."


def delete(ref, force=False):
    page = _page(ref)
    _protect_root(page, "delete")
    descendants = page.get_descendant_count()
    references = _reference_count(page)
    if references and not force:
        raise CmsError(f"{page.url} is linked from {references} place(s). Add --force to delete it anyway.")
    title, url = page.title, page.url
    DeletePageAction(page, user=actor()).execute(skip_permission_checks=True)
    extra = f" and its {descendants} subpage(s)" if descendants else ""
    return f"Deleted “{title}” ({url}){extra}."


def move(ref, target_ref, position="last-child"):
    page = _page(ref)
    _protect_root(page, "move")
    target = _page(target_ref)
    if position not in ("last-child", "first-child", "left", "right"):
        raise CmsError("Position must be last-child, first-child, left (before the target) or right (after it).")
    MovePageAction(page, target, pos=position, user=actor()).execute(skip_permission_checks=True)
    page.refresh_from_db()
    return f"Moved “{page.title}” to {_where(page)}."


def copy(ref, parent_ref, title=None, slug=None, keep_live=False):
    page = _page(ref)
    parent = _page(parent_ref)
    update = {}
    if title:
        update["title"] = title
        update["draft_title"] = title
    if slug:
        update["slug"] = slug
    new_page = page.copy(to=parent, update_attrs=update or None, keep_live=keep_live, user=actor())
    state = "live" if new_page.live else "a draft"
    return f"Copied to “{new_page.title}” at {_where(new_page)} ({state}, id {new_page.pk})."


def revisions(ref, limit=20):
    page = _page(ref)
    live_id = page.live_revision_id
    rows = [
        {
            "id": revision.pk,
            "created_at": revision.created_at,
            "by": str(revision.user) if revision.user else None,
            "live": revision.pk == live_id,
        }
        for revision in page.revisions.order_by("-created_at")[:limit]
    ]
    return dump(rows)


def revert(ref, revision_id, *, publish):
    page = _page(ref)
    revision = page.revisions.filter(pk=revision_id).first()
    if revision is None:
        raise CmsError(f"{page.url} has no revision {revision_id}. See `cms pages revisions {page.url}`.")
    new_revision = RevertToPageRevisionAction(page, revision, user=actor()).execute(skip_permission_checks=True)
    if publish:
        new_revision.publish(user=actor(), skip_permission_checks=True)
    state = "and published" if publish else "as a draft"
    return f"Reverted {page.url} to revision {revision.pk} {state} (new revision {new_revision.pk})."


def lock(ref, locked):
    page = _page(ref)
    if page.locked == locked:
        return f"{page.url} is already {'locked' if locked else 'unlocked'}."
    page.locked = locked
    page.locked_by = actor() if locked else None
    page.locked_at = timezone.now() if locked else None
    page.save(update_fields=["locked", "locked_by", "locked_at"])
    log_action(page, "wagtail.lock" if locked else "wagtail.unlock")
    return f"{'Locked' if locked else 'Unlocked'} {page.url}."


def references(ref):
    page = _page(ref)
    return dump([_describe_reference(r) for r in ReferenceIndex.get_references_to(page)])


def _reference_count(obj):
    return ReferenceIndex.get_references_to(obj).count()


def _describe_reference(reference):
    return {
        "from": f"{reference.content_type.model} {reference.object_id}",
        "field": reference.model_path,
    }


def _where(page):
    return page.url or page.url_path


def _protect_root(page, action):
    if page.depth <= 2:
        raise CmsError(f"Won't {action} the site's home page; it would take the whole site down.")


def parse_changes(data):
    if isinstance(data, str):
        data = json.loads(data)
    return data
