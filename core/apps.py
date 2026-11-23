from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Site"

    def ready(self):
        connect_edge_cache_purging()


# Saving only these fields doesn't change anything visitors see (Wagtail fills them in when an image is first used).
BOOKKEEPING_FIELDS = {"file_hash", "file_size", "width", "height"}


def connect_edge_cache_purging():
    """Purge the edge cache whenever something that appears on public pages changes."""
    from django.db.models.signals import post_delete, post_save
    from wagtail.contrib.redirects.models import Redirect
    from wagtail.images import get_image_model
    from wagtail.models import Page, Site
    from wagtail.signals import page_published, page_unpublished, post_page_move

    from core.cache import purge_edge_cache_on_commit
    from core.models import SiteSettings, Testimonial

    def purge(sender, **kwargs):
        update_fields = kwargs.get("update_fields")
        if update_fields and set(update_fields) <= BOOKKEEPING_FIELDS:
            return
        purge_edge_cache_on_commit()

    for signal in (page_published, page_unpublished, post_page_move):
        signal.connect(purge, dispatch_uid=f"edge-purge-{signal}")

    def purge_on_page_delete(sender, instance, **kwargs):
        if isinstance(instance, Page) and instance.live:
            purge_edge_cache_on_commit()

    post_delete.connect(purge_on_page_delete, dispatch_uid="edge-purge-page-delete")

    for model in (Testimonial, SiteSettings, get_image_model(), Redirect, Site):
        post_save.connect(purge, sender=model, dispatch_uid=f"edge-purge-save-{model.__name__}")
        post_delete.connect(purge, sender=model, dispatch_uid=f"edge-purge-delete-{model.__name__}")
