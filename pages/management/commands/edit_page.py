"""Change a page's content from a JSON list of operations (see pages/content_ops.py for the format).

    python manage.py edit_page /comedy/ changes.json            # dry run: validate and print a diff, save nothing
    python manage.py edit_page /comedy/ changes.json --draft    # save as a draft revision for review in the admin
    python manage.py edit_page /comedy/ changes.json --publish  # save and publish
    ... | python manage.py edit_page /comedy/ - --draft          # read the changes from stdin

Revisions are recorded under the "claude" user, so they show up as such in the page's History and can be reverted
there. Changes build on the page's latest version. If someone else has unpublished changes on the page, --publish
would publish their draft too, so it refuses unless --include-others-draft is given.
"""

import json
import sys

from django.core.management.base import BaseCommand, CommandError

from pages.content_ops import REVISION_USERNAME, ContentError, apply_changes, diff, find_page, save, snapshot


class Command(BaseCommand):
    help = "Change a page's content from a JSON list of operations. Dry run unless --draft or --publish."

    def add_arguments(self, parser):
        parser.add_argument("page", help="Page id or URL path, e.g. /comedy/")
        parser.add_argument("changes", help="Path to a JSON file with a list of operations, or - for stdin")
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument("--draft", action="store_true", help="Save the result as a draft revision")
        mode.add_argument("--publish", action="store_true", help="Save the result and publish it")
        parser.add_argument(
            "--include-others-draft",
            action="store_true",
            help="Allow --publish when someone else has unpublished changes on the page (they get published too)",
        )

    def handle(self, *args, page, changes, draft, publish, include_others_draft, **options):
        try:
            changes_data = json.load(sys.stdin if changes == "-" else open(changes, encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise CommandError(f"Couldn't read the changes: {error}") from None

        try:
            found = find_page(page)
        except ContentError as error:
            raise CommandError(str(error)) from None

        if found.locked:
            raise CommandError(f"{found.url} is locked in the admin. Unlock it first.")

        latest = found.get_latest_revision()
        others_draft = (
            found.has_unpublished_changes and latest is not None and getattr(latest.user, "username", None) != REVISION_USERNAME
        )
        if others_draft:
            self.stderr.write(
                f"Note: {found.url} has unpublished changes by {latest.user or 'someone'} "
                f"({latest.created_at:%d %b %Y %H:%M}); these changes build on that draft."
            )
            if publish and not include_others_draft:
                raise CommandError(
                    "Publishing would also publish that draft. Save with --draft instead, or add --include-others-draft."
                )

        editable = found.get_latest_revision_as_object()
        before = snapshot(editable)
        try:
            edited = apply_changes(editable, changes_data)
        except ContentError as error:
            raise CommandError(str(error)) from None
        after = snapshot(edited)

        changes_diff = diff(before, after)
        if not changes_diff:
            self.stdout.write("No differences; nothing to save.")
            return
        self.stdout.write(changes_diff)

        if not (draft or publish):
            self.stdout.write(self.style.WARNING("\nDry run: valid, nothing saved. Add --draft or --publish to save."))
            return

        revision = save(edited, publish=publish)
        action = "Published" if publish else "Saved as a draft"
        self.stdout.write(self.style.SUCCESS(f"\n{action}: {found.url} (revision {revision.pk}, by {REVISION_USERNAME})."))
        if not publish:
            self.stdout.write(f"Review it in the admin: /admin/pages/{found.pk}/edit/")
