from django.db import migrations


def create_home_page(apps, schema_editor):
    """Replace Wagtail's default "Welcome" page (a plain Page) with a LandingPage as the site root."""
    ContentType = apps.get_model("contenttypes.ContentType")
    Page = apps.get_model("wagtailcore.Page")
    Site = apps.get_model("wagtailcore.Site")
    LandingPage = apps.get_model("pages.LandingPage")
    Locale = apps.get_model("wagtailcore.Locale")

    page_content_type = ContentType.objects.get(model="page", app_label="wagtailcore")
    welcome = Page.objects.filter(content_type=page_content_type, slug="home", depth=2).first()
    # wagtailcore created the initial locale from LANGUAGE_CODE; reuse it.
    locale_id = welcome.locale_id if welcome else Locale.objects.order_by("pk").first().pk
    if welcome:
        welcome.delete()  # also deletes the default Site that points at it

    landing_page_content_type, __ = ContentType.objects.get_or_create(model="landingpage", app_label="pages")

    home = LandingPage.objects.create(
        title="Home",
        draft_title="Home",
        slug="home",
        content_type=landing_page_content_type,
        path="00010001",
        depth=2,
        numchild=0,
        url_path="/home/",
        locale_id=locale_id,
    )

    Site.objects.create(hostname="localhost", root_page=home, is_default_site=True, site_name="Design by Committee")


def remove_home_page(apps, schema_editor):
    ContentType = apps.get_model("contenttypes.ContentType")
    LandingPage = apps.get_model("pages.LandingPage")

    LandingPage.objects.filter(slug="home", depth=2).delete()  # the Site cascades
    ContentType.objects.filter(model="landingpage", app_label="pages").delete()


class Migration(migrations.Migration):
    dependencies = [("pages", "0001_initial")]

    operations = [migrations.RunPython(create_home_page, remove_home_page)]
