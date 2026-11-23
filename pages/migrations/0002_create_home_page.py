from django.db import migrations


def create_home_page(apps, schema_editor):
    """Replace Wagtail's default "Welcome" page (a plain Page) with an empty HomePage as the site root.

    Content is added by `manage.py import_current_site`.
    """
    ContentType = apps.get_model("contenttypes.ContentType")
    Page = apps.get_model("wagtailcore.Page")
    Site = apps.get_model("wagtailcore.Site")
    Locale = apps.get_model("wagtailcore.Locale")
    HomePage = apps.get_model("pages.HomePage")

    page_content_type = ContentType.objects.get(model="page", app_label="wagtailcore")
    welcome = Page.objects.filter(content_type=page_content_type, slug="home", depth=2).first()
    # wagtailcore created the initial locale from LANGUAGE_CODE; reuse it.
    locale_id = welcome.locale_id if welcome else Locale.objects.order_by("pk").first().pk
    if welcome:
        welcome.delete()  # also deletes the default Site that points at it

    home_page_content_type, __ = ContentType.objects.get_or_create(model="homepage", app_label="pages")

    home = HomePage.objects.create(
        title="Home",
        draft_title="Home",
        slug="home",
        content_type=home_page_content_type,
        path="00010001",
        depth=2,
        numchild=0,
        url_path="/home/",
        locale_id=locale_id,
    )

    Site.objects.create(hostname="localhost", root_page=home, is_default_site=True, site_name="Design by Committee")


def remove_home_page(apps, schema_editor):
    ContentType = apps.get_model("contenttypes.ContentType")
    HomePage = apps.get_model("pages.HomePage")

    HomePage.objects.filter(slug="home", depth=2).delete()  # the Site cascades
    ContentType.objects.filter(model="homepage", app_label="pages").delete()


class Migration(migrations.Migration):
    dependencies = [("pages", "0001_initial")]

    operations = [migrations.RunPython(create_home_page, remove_home_page)]
