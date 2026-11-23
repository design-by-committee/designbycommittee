"""Print a page's editable content as JSON, with block ids and types, for use with `edit_page`.

    python manage.py show_page                 # list all pages
    python manage.py show_page /comedy/        # latest version of a page (including any unpublished draft)
    python manage.py show_page /comedy/ --live # the published version
"""

import json

from django.core.management.base import BaseCommand, CommandError

from pages.content_ops import ContentError, describe, find_page, page_tree, snapshot


class Command(BaseCommand):
    help = "Print a page's editable content as JSON (or list all pages)."

    def add_arguments(self, parser):
        parser.add_argument("page", nargs="?", help="Page id or URL path, e.g. /comedy/. Omit to list pages.")
        parser.add_argument("--live", action="store_true", help="Show the published version instead of the latest.")

    def handle(self, *args, page=None, live=False, **options):
        if page is None:
            self.stdout.write(json.dumps(page_tree(), indent=2, ensure_ascii=False))
            return
        try:
            found = find_page(page)
        except ContentError as error:
            raise CommandError(str(error)) from None
        content = found if live else found.get_latest_revision_as_object()
        output = {"page": describe(found, live=live), **snapshot(content)}
        self.stdout.write(json.dumps(output, indent=2, ensure_ascii=False, default=str))
