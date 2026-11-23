"""Media storage that puts a content hash in image rendition file names, like static files get.

Wagtail serves images as renditions (resized copies) under media/images/, e.g. images/photo.width-800.jpg. Those names
don't change when the picture does: replace an image's file and a later rendition can reuse an old URL. With the
hash, every distinct file gets its own URL (images/photo.width-800.3f2a1b9c0d12.jpg), so renditions can be cached
for a year by browsers and Render's edge cache. A changed image gets new URLs, and pages link to them as soon as
they're published.
"""

import hashlib
import posixpath
import re

from django.core.files.storage import FileSystemStorage

RENDITIONS_DIR = "images/"
HASH_LENGTH = 12
HASHED_NAME = re.compile(rf"\.[0-9a-f]{{{HASH_LENGTH}}}\.[A-Za-z0-9]+$")


def content_hash(content):
    digest = hashlib.sha256()
    if hasattr(content, "seek"):
        content.seek(0)
    for chunk in content.chunks() if hasattr(content, "chunks") else [content.read()]:
        digest.update(chunk)
    if hasattr(content, "seek"):
        content.seek(0)
    return digest.hexdigest()[:HASH_LENGTH]


def is_hashed_rendition(name):
    """True for a rendition file name that carries a content hash."""
    return name.startswith(RENDITIONS_DIR) and bool(HASHED_NAME.search(name))


class HashedRenditionStorage(FileSystemStorage):
    def save(self, name, content, max_length=None):
        if name and name.replace("\\", "/").startswith(RENDITIONS_DIR) and not HASHED_NAME.search(name):
            root, ext = posixpath.splitext(name)
            name = f"{root}.{content_hash(content)}{ext}"
        return super().save(name, content, max_length=max_length)
