"""Do what an editor or administrator does in the Wagtail admin, from the command line.

    python manage.py cms <area> <action> [arguments] [--apply]

Areas: pages, snippets, settings, images, documents, leads, redirects, sites, users.
Run `python manage.py cms <area> --help` for the actions of an area.

Every change is a dry run unless --apply is given (pages: --draft or --publish): it runs for real inside a database
transaction, prints what would change, and rolls back. Changes are recorded under the "claude" user, which can't
sign in, and appear in page History and Reports → Site history like changes made in the admin.

Data for creates and updates is JSON: --data '{"field": "value"}' or --data-file PATH (- for stdin).
"""

import argparse

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management.base import BaseCommand, CommandError

from core.cms import media, pages, records
from core.cms.base import CmsError, changes, load_data


def _data_args(parser, required=True):
    group = parser.add_mutually_exclusive_group(required=required)
    group.add_argument("--data", help="JSON object (or, for pages edit, a JSON list of operations)")
    group.add_argument("--data-file", help="Path to a JSON file, or - for stdin")


def _apply_arg(parser):
    parser.add_argument("--apply", action="store_true", help="Make the change (otherwise: dry run)")


def _crud(subparsers, *, with_create=True, with_delete=True, type_arg=False):
    """list / show / create / update / delete subcommands for a record type."""
    def add(name, **kwargs):
        p = subparsers.add_parser(name, **kwargs)
        if type_arg:
            p.add_argument("type", help="Snippet type, e.g. testimonial (see `cms snippets types`)")
        return p

    add("list")
    add("show").add_argument("id", type=int)
    if with_create:
        p = add("create")
        _data_args(p)
        _apply_arg(p)
    p = add("update")
    p.add_argument("id", type=int)
    _data_args(p)
    _apply_arg(p)
    if with_delete:
        p = add("delete")
        p.add_argument("id", type=int)
        p.add_argument("--force", action="store_true", help="Delete even if it's used elsewhere")
        _apply_arg(p)


class Command(BaseCommand):
    help = __doc__.split("\n\n")[0]

    def create_parser(self, *args, **kwargs):
        parser = super().create_parser(*args, **kwargs)
        parser.formatter_class = argparse.RawDescriptionHelpFormatter
        parser.description = __doc__
        return parser

    def add_arguments(self, parser):
        areas = parser.add_subparsers(dest="area", required=True, parser_class=type(parser))

        # Pages
        page_actions = areas.add_parser("pages", help="Pages: content, publishing, tree").add_subparsers(dest="action", required=True)
        page_actions.add_parser("list", help="All pages")
        p = page_actions.add_parser("show", help="A page's fields and blocks as JSON")
        p.add_argument("page", help="Page id or path, e.g. /comedy/")
        p.add_argument("--live", action="store_true", help="The published version instead of the latest")
        p = page_actions.add_parser("edit", help="Change a page's content (see pages/content_ops.py for the operations)")
        p.add_argument("page")
        _data_args(p)
        mode = p.add_mutually_exclusive_group()
        mode.add_argument("--draft", action="store_true", help="Save as a draft")
        mode.add_argument("--publish", action="store_true", help="Save and publish")
        p.add_argument("--include-others-draft", action="store_true", help="Allow publishing over someone else's draft")
        p = page_actions.add_parser("create", help="Create a page")
        p.add_argument("parent", help="Parent page, e.g. /")
        p.add_argument("type", help="Page type, e.g. LandingPage")
        _data_args(p)
        mode = p.add_mutually_exclusive_group()
        mode.add_argument("--draft", action="store_true", help="Create it as a draft")
        mode.add_argument("--publish", action="store_true", help="Create and publish it")
        for name, help_text in [("publish", "Publish the latest revision"), ("unpublish", "Take a page offline")]:
            p = page_actions.add_parser(name, help=help_text)
            p.add_argument("page")
            if name == "unpublish":
                p.add_argument("--include-descendants", action="store_true")
            _apply_arg(p)
        p = page_actions.add_parser("delete", help="Delete a page and its subpages")
        p.add_argument("page")
        p.add_argument("--force", action="store_true", help="Delete even if other content links to it")
        _apply_arg(p)
        p = page_actions.add_parser("move", help="Move a page in the tree")
        p.add_argument("page")
        p.add_argument("target", help="New parent (or sibling, with --position left/right)")
        p.add_argument("--position", default="last-child", choices=["last-child", "first-child", "left", "right"])
        _apply_arg(p)
        p = page_actions.add_parser("copy", help="Copy a page")
        p.add_argument("page")
        p.add_argument("parent", help="Where the copy goes")
        p.add_argument("--title")
        p.add_argument("--slug")
        p.add_argument("--keep-live", action="store_true", help="Publish the copy (default: a draft)")
        _apply_arg(p)
        page_actions.add_parser("revisions", help="A page's revisions").add_argument("page")
        p = page_actions.add_parser("revert", help="Go back to an earlier revision")
        p.add_argument("page")
        p.add_argument("revision", type=int)
        p.add_argument("--publish", action="store_true", help="Publish the reverted version (default: a draft)")
        _apply_arg(p)
        for name in ("lock", "unlock"):
            p = page_actions.add_parser(name)
            p.add_argument("page")
            _apply_arg(p)
        page_actions.add_parser("references", help="Where a page is linked from").add_argument("page")

        # Snippets
        snippet_actions = areas.add_parser("snippets", help="Snippets such as testimonials").add_subparsers(dest="action", required=True)
        snippet_actions.add_parser("types")
        _crud(snippet_actions, type_arg=True)

        # Settings
        settings_actions = areas.add_parser("settings", help="Site settings").add_subparsers(dest="action", required=True)
        settings_actions.add_parser("list")
        p = settings_actions.add_parser("show")
        p.add_argument("name", help="e.g. sitesettings")
        p.add_argument("--site", help="Site host name (default: the default site)")
        p = settings_actions.add_parser("update")
        p.add_argument("name")
        p.add_argument("--site")
        _data_args(p)
        _apply_arg(p)

        # Images and documents
        for area in ("images", "documents"):
            actions = areas.add_parser(area, help=f"The {area} library").add_subparsers(dest="action", required=True)
            actions.add_parser("list").add_argument("--search")
            actions.add_parser("show").add_argument("id", type=int)
            p = actions.add_parser("upload")
            p.add_argument("--file", required=True, help="Path to the file, or - for stdin")
            p.add_argument("--filename", help="File name (needed with --file -)")
            _data_args(p, required=False)
            _apply_arg(p)
            p = actions.add_parser("update")
            p.add_argument("id", type=int)
            p.add_argument("--file", help="Replace the file (path, or - for stdin)")
            p.add_argument("--filename")
            _data_args(p, required=False)
            _apply_arg(p)
            p = actions.add_parser("delete")
            p.add_argument("id", type=int)
            p.add_argument("--force", action="store_true", help="Delete even if it's used on a page")
            _apply_arg(p)

        # Leads
        lead_actions = areas.add_parser("leads", help="Form submissions").add_subparsers(dest="action", required=True)
        p = lead_actions.add_parser("list")
        p.add_argument("--form", choices=["comedy-enquiry", "landing-page-assessment"])
        p.add_argument("--unhandled", action="store_true")
        p.add_argument("--since", help="YYYY-MM-DD")
        lead_actions.add_parser("show").add_argument("id", type=int)
        p = lead_actions.add_parser("update", help='e.g. --data \'{"handled": true}\'')
        p.add_argument("id", type=int)
        _data_args(p)
        _apply_arg(p)
        p = lead_actions.add_parser("delete")
        p.add_argument("id", type=int)
        _apply_arg(p)
        lead_actions.add_parser("export", help="CSV to stdout").add_argument("--form")

        # Redirects and sites
        _crud(areas.add_parser("redirects", help="Redirects").add_subparsers(dest="action", required=True))
        _crud(areas.add_parser("sites", help="Sites (host names)").add_subparsers(dest="action", required=True), with_delete=False)

        # Users
        user_actions = areas.add_parser("users", help="Admin users (no passwords)").add_subparsers(dest="action", required=True)
        _crud(user_actions)
        user_actions.add_parser("groups")

    def handle(self, *args, area, action, **options):
        apply = options.get("apply", False)
        try:
            output = self.run(area, action, options, apply)
        except CmsError as error:
            raise CommandError(str(error)) from None
        except (ValidationError, PermissionDenied) as error:
            messages = getattr(error, "messages", None) or [str(error)]
            raise CommandError("; ".join(messages)) from None
        if output:
            self.stdout.write(output)

    def run(self, area, action, o, apply):
        data = lambda: load_data(o.get("data"), o.get("data_file"))  # noqa: E731
        optional_data = lambda: load_data(o.get("data"), o.get("data_file"), default={})  # noqa: E731
        read_only = action in {"list", "show", "types", "revisions", "references", "export", "groups"}

        def mutate(fn):
            """Run a database change; roll it back unless --apply."""
            result = None
            with changes(apply):
                result = fn()
            if apply:
                return result
            return f"{result}\n\nDry run: nothing was saved. Add --apply to make this change."

        if area == "pages":
            if action == "list":
                return pages.list_pages()
            if action == "show":
                return pages.show(o["page"], live=o["live"])
            if action == "edit":
                return pages.edit(o["page"], data(), draft=o["draft"], publish=o["publish"],
                                  include_others_draft=o["include_others_draft"])
            if action == "create":
                apply = o["draft"] or o["publish"]
                return mutate(lambda: pages.create(o["parent"], o["type"], data(), draft=o["draft"], publish=o["publish"]))
            if action == "revisions":
                return pages.revisions(o["page"])
            if action == "references":
                return pages.references(o["page"])
            operations = {
                "publish": lambda: pages.publish(o["page"]),
                "unpublish": lambda: pages.unpublish(o["page"], o.get("include_descendants", False)),
                "delete": lambda: pages.delete(o["page"], o["force"]),
                "move": lambda: pages.move(o["page"], o["target"], o["position"]),
                "copy": lambda: pages.copy(o["page"], o["parent"], o["title"], o["slug"], o["keep_live"]),
                "revert": lambda: pages.revert(o["page"], o["revision"], publish=o["publish"]),
                "lock": lambda: pages.lock(o["page"], True),
                "unlock": lambda: pages.lock(o["page"], False),
            }
            return mutate(operations[action])

        if area == "snippets":
            if action == "types":
                return records.snippet_types()
            resource = records.snippet(o["type"])
            return self.crud(resource, action, o, data, mutate)

        if area == "settings":
            if action == "list":
                return records.settings_list()
            if action == "show":
                return records.settings_show(o["name"], o["site"])
            return mutate(lambda: records.settings_update(o["name"], data(), o["site"]))

        if area in ("images", "documents"):
            kind = area[:-1]
            if action == "list":
                return media.list_items(kind, o.get("search"))
            if action == "show":
                return media.show(kind, o["id"])
            if action == "upload":
                return media.upload(kind, optional_data(), o["file"], o["filename"], apply)
            if action == "update":
                return media.update(kind, o["id"], optional_data(), o["file"], o["filename"], apply)
            if action == "delete":
                return media.delete(kind, o["id"], apply, o["force"])

        if area == "leads":
            resource = records.leads_resource()
            if action == "list":
                return records.leads_list(o["form"], o["unhandled"], o["since"])
            if action == "export":
                return records.leads_export(o["form"])
            if action == "delete":
                return mutate(lambda: resource.delete(o["id"], force=True))
            return self.crud(resource, action, o, data, mutate)

        if area == "redirects":
            return self.crud(records.redirects, action, o, data, mutate)

        if area == "sites":
            return self.crud(records.sites, action, o, data, mutate)

        if area == "users":
            if action == "list":
                return records.users_list()
            if action == "groups":
                return records.groups_list()
            if action == "show":
                return records.users_show(o["id"])
            if action == "create":
                return mutate(lambda: records.users_create(data()))
            if action == "delete":
                return mutate(lambda: records.users_delete(o["id"], o["force"]))
            return self.crud(records.users_resource(), action, o, data, mutate)

        raise CmsError(f"Unknown action {area} {action}." if not read_only else "Unknown command.")

    @staticmethod
    def crud(resource, action, o, data, mutate):
        if action == "list":
            return resource.list()
        if action == "show":
            return resource.show(o["id"])
        if action == "create":
            return mutate(lambda: resource.create(data()))
        if action == "update":
            return mutate(lambda: resource.update(o["id"], data()))
        if action == "delete":
            return mutate(lambda: resource.delete(o["id"], o.get("force", False)))
        raise CmsError(f"Unknown action {action!r}.")
