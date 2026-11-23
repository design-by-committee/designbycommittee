"""Delete image renditions whose file names have no content hash, so Wagtail regenerates them with one.

Runs before the web server starts (render.yaml). After the first run it finds nothing to do, so it's cheap. It runs
before gunicorn rather than over SSH because Wagtail keeps renditions in each server process's cache, which a
separate process can't clear.
"""

from django.core.management.base import BaseCommand
from wagtail.images import get_image_model

from core.storage import is_hashed_rendition


class Command(BaseCommand):
    help = "Delete image renditions without a content hash in their file name (they're regenerated on demand)."

    def handle(self, *args, **options):
        Rendition = get_image_model().get_rendition_model()
        old = [rendition.pk for rendition in Rendition.objects.only("file") if not is_hashed_rendition(rendition.file.name)]
        if not old:
            self.stdout.write("All image renditions have hashed file names.")
            return
        # Wagtail's post_delete handler removes each rendition's file (and the image's cached rendition entries).
        for rendition in Rendition.objects.filter(pk__in=old):
            rendition.delete()
        self.stdout.write(f"Deleted {len(old)} rendition(s) without a hashed file name; they'll be regenerated on demand.")
