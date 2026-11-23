"""Read and change page content from the command line, through Wagtail's own APIs.

Used by `cms pages show` and `cms pages edit` (core/management/commands/cms.py), so content can be edited without the admin
(e.g. by Claude over SSH). Every change is validated like the page editor validates it, and saved as a normal
page revision (a draft unless publishing is asked for), so it shows in the page's History and can be reverted.

Changes are a list of operations on a page:

    {"op": "set_field", "field": "seo_title", "value": "New title"}
    {"op": "set", "block": "feature:3", "path": "points.0", "value": "New first point"}
    {"op": "set", "block": "hero", "path": "lead", "value": "<p>New <span class=\\"text-bold\\">lead</span></p>"}
    {"op": "insert", "type": "intro", "value": {...}, "after": "button"}    (or "before"; neither = append)
    {"op": "remove", "block": "faq"}
    {"op": "move", "block": "packages", "before": "steps"}

"stream" picks the StreamField and defaults to "body" (LandingPage also has "header_links" and "header_button").

A block reference ("block", "after", "before") is one of:
    - the block's id, or a unique prefix of it (at least 4 characters), as shown by `show_page`
    - a block type, when the page has exactly one block of that type: "hero"
    - a block type and its position among blocks of that type, counting from 1: "feature:3"
    - a position among all blocks, counting from 1: "#2"

A path walks into a block's value with dots: "points.0" is the first bullet point, "cards.1.title" the second
card's title. An empty path means the whole block value.
"""

import copy
import difflib
import json

from django.core.exceptions import ValidationError
from wagtail.models import Page, Site

EDITABLE_FIELDS = {"title", "slug", "seo_title", "search_description", "og_title", "og_description"}


class ContentError(Exception):
    """A change that can't be applied; the message says why."""


# Pages --------------------------------------------------------------------------------------------------------------


def find_page(ref):
    """A page by id ("12") or by its URL path on the default site ("/", "/comedy/")."""
    ref = str(ref).strip()
    if ref.isdigit():
        page = Page.objects.filter(pk=int(ref)).first()
    else:
        site = Site.objects.get(is_default_site=True)
        parts = [part for part in ref.strip("/").split("/") if part]
        url_path = site.root_page.url_path + "".join(f"{part}/" for part in parts)
        page = Page.objects.filter(url_path=url_path).first()
    if page is None:
        raise ContentError(f"No page found for {ref!r}. Use a page id or a path such as /comedy/.")
    return page.specific


def stream_field_names(page):
    from wagtail.fields import StreamField

    return [field.name for field in page._meta.get_fields() if isinstance(field, StreamField)]


def stream_data(stream_value):
    """A StreamField's value as raw JSON data, with every field the blocks currently define.

    Blocks saved before a field was added to their definition don't store that field. Iterating the StreamValue
    converts each block through its definition first, which fills in missing fields with their defaults, so they
    show up in `show` and can be set by a path.
    """
    list(stream_value)
    return stream_value.get_prep_value()


def snapshot(page):
    """The page's editable content as plain JSON-ready data."""
    data = {"fields": {name: getattr(page, name) for name in sorted(EDITABLE_FIELDS)}}
    for name in stream_field_names(page):
        data[name] = stream_data(getattr(page, name))
    return data


def describe(page, *, live):
    latest = page.get_latest_revision()
    return {
        "id": page.pk,
        "type": page.specific_class.__name__,
        "url": page.url,
        "showing": "live version" if live else "latest version (including any unpublished draft)",
        "live": page.live,
        "has_unpublished_changes": page.has_unpublished_changes,
        "latest_revision": {
            "id": latest.pk,
            "by": str(latest.user) if latest and latest.user else None,
            "at": latest.created_at.isoformat(),
        }
        if latest
        else None,
        "locked": page.locked,
    }


def page_tree():
    """All pages under the default site's root, for `show_page` without a page."""
    root = Site.objects.get(is_default_site=True).root_page
    pages = [root, *root.get_descendants().specific()]
    return [
        {
            "id": page.pk,
            "url": page.url,
            "title": page.title,
            "type": page.specific_class.__name__,
            "live": page.live,
            "has_unpublished_changes": page.has_unpublished_changes,
        }
        for page in [p.specific for p in pages]
    ]


# Block references and paths -----------------------------------------------------------------------------------------


def resolve_block(blocks, ref):
    """Index of the block in a raw stream list that `ref` points to (see module docstring)."""
    ref = str(ref).strip()
    if not ref:
        raise ContentError("Empty block reference.")
    if ref.startswith("#") and ref[1:].isdigit():
        position = int(ref[1:])
        if not 1 <= position <= len(blocks):
            raise ContentError(f"There's no block {ref}; the stream has {len(blocks)} blocks.")
        return position - 1

    by_id = [i for i, block in enumerate(blocks) if block.get("id") == ref]
    if by_id:
        return by_id[0]
    if len(ref) >= 4:
        by_prefix = [i for i, block in enumerate(blocks) if str(block.get("id", "")).startswith(ref)]
        if len(by_prefix) == 1:
            return by_prefix[0]

    block_type, _, nth = ref.partition(":")
    of_type = [i for i, block in enumerate(blocks) if block["type"] == block_type]
    if nth:
        if not nth.isdigit() or not 1 <= int(nth) <= len(of_type):
            raise ContentError(f"There's no block {ref!r}; the stream has {len(of_type)} {block_type!r} blocks.")
        return of_type[int(nth) - 1]
    if len(of_type) == 1:
        return of_type[0]
    if len(of_type) > 1:
        raise ContentError(f"{len(of_type)} blocks are of type {block_type!r}; use {block_type}:1, {block_type}:2, …")
    types = ", ".join(sorted({block["type"] for block in blocks})) or "none"
    raise ContentError(f"No block matches {ref!r}. Block types on this stream: {types}.")


def _is_list_item(value):
    # ListBlock items are stored as {"type": "item", "value": ..., "id": ...}
    return isinstance(value, dict) and value.get("type") == "item" and "value" in value


def _step(container, key, path):
    if isinstance(container, list):
        if not (key.isdigit() or (key.startswith("-") and key[1:].isdigit())):
            raise ContentError(f"{path!r}: {key!r} should be a list position (0 is the first item).")
        index = int(key)
        if not -len(container) <= index < len(container):
            raise ContentError(f"{path!r}: there's no item {index}; the list has {len(container)} items.")
        return index
    if isinstance(container, dict):
        if key not in container:
            raise ContentError(f"{path!r}: no field {key!r}. Fields here: {', '.join(container)}.")
        return key
    raise ContentError(f"{path!r}: can't go into {key!r}, the value there is a {type(container).__name__}.")


def set_path(value, path, new_value):
    """Set `new_value` at a dotted path inside a raw block value and return the (possibly replaced) value."""
    if not path:
        return new_value
    keys = path.split(".")
    container = value
    for key in keys[:-1]:
        container = container[_step(container, key, path)]
        if _is_list_item(container):
            container = container["value"]
    last = _step(container, keys[-1], path)
    if _is_list_item(container[last]):
        container[last]["value"] = new_value
    else:
        container[last] = new_value
    return value


# Applying changes ---------------------------------------------------------------------------------------------------


def apply_changes(page, changes, validate_page=True):
    """Apply a list of operations to `page` (an unsaved copy) and validate the result like the page editor does."""
    if not isinstance(changes, list) or not changes:
        raise ContentError("Changes must be a non-empty JSON list of operations.")
    streams = {name: copy.deepcopy(stream_data(getattr(page, name))) for name in stream_field_names(page)}
    touched = set()

    for number, change in enumerate(changes, start=1):
        try:
            _apply_one(page, streams, change, touched)
        except ContentError as error:
            raise ContentError(f"Change {number} ({change.get('op', '?')}): {error}") from None

    for name in touched:
        stream_block = page._meta.get_field(name).stream_block
        try:
            value = stream_block.clean(stream_block.to_python(streams[name]))
        except ValidationError as error:
            raise ContentError(f"The new {name} isn't valid: {_flatten_errors(error)}") from None
        setattr(page, name, value)

    if validate_page:
        try:
            page.full_clean()
        except ValidationError as error:
            raise ContentError(f"The page isn't valid: {_flatten_errors(error)}") from None
    return page


def _apply_one(page, streams, change, touched):
    if not isinstance(change, dict):
        raise ContentError("Each change must be a JSON object.")
    op = change.get("op")

    if op == "set_field":
        field = change.get("field")
        if field not in EDITABLE_FIELDS:
            raise ContentError(f"Field {field!r} can't be edited here. Editable: {', '.join(sorted(EDITABLE_FIELDS))}.")
        setattr(page, field, change.get("value", ""))
        return

    stream_name = change.get("stream", "body")
    if stream_name not in streams:
        raise ContentError(f"This page has no {stream_name!r}. Streams: {', '.join(streams)}.")
    blocks = streams[stream_name]
    stream_block = page._meta.get_field(stream_name).stream_block
    touched.add(stream_name)

    if op == "set":
        index = resolve_block(blocks, change.get("block", ""))
        blocks[index]["value"] = set_path(blocks[index]["value"], change.get("path", ""), change.get("value"))
    elif op == "insert":
        block_type = change.get("type")
        if block_type not in stream_block.child_blocks:
            allowed = ", ".join(stream_block.child_blocks)
            raise ContentError(f"Block type {block_type!r} isn't allowed in {stream_name}. Allowed: {allowed}.")
        new_block = {"type": block_type, "value": change.get("value")}
        blocks.insert(_target_position(blocks, change), new_block)
    elif op == "remove":
        del blocks[resolve_block(blocks, change.get("block", ""))]
    elif op == "move":
        block = blocks.pop(resolve_block(blocks, change.get("block", "")))
        if "after" not in change and "before" not in change:
            raise ContentError("A move needs 'after' or 'before'.")
        blocks.insert(_target_position(blocks, change), block)
    else:
        raise ContentError(f"Unknown op {op!r}. Use set_field, set, insert, remove or move.")


def _target_position(blocks, change):
    if "after" in change:
        return resolve_block(blocks, change["after"]) + 1
    if "before" in change:
        return resolve_block(blocks, change["before"])
    return len(blocks)


def _flatten_errors(error):
    if hasattr(error, "block_errors") or hasattr(error, "params"):
        detail = getattr(error, "as_json_data", None)
        if callable(detail):
            return json.dumps(detail(), ensure_ascii=False)
    if hasattr(error, "message_dict"):
        return json.dumps(error.message_dict, ensure_ascii=False)
    return "; ".join(error.messages)


def diff(before, after):
    """A unified diff of two snapshots."""
    dump = lambda data: json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True).splitlines()  # noqa: E731
    return "\n".join(difflib.unified_diff(dump(before), dump(after), "current", "proposed", lineterm=""))
