from django.db import migrations


def update_catalog_title(apps, schema_editor):
    Section = apps.get_model("core", "SitePageSection")
    database = schema_editor.connection.alias
    Section.objects.using(database).filter(
        page="home",
        group="catalog",
        section_title="Популярные наборы",
    ).update(section_title="Наша продукция")
    Section.objects.using(database).filter(
        page="home",
        group="catalog",
        section_title_en="Popular gift sets",
    ).update(section_title_en="Our products")


def restore_catalog_title(apps, schema_editor):
    Section = apps.get_model("core", "SitePageSection")
    database = schema_editor.connection.alias
    Section.objects.using(database).filter(
        page="home",
        group="catalog",
        section_title="Наша продукция",
    ).update(section_title="Популярные наборы")
    Section.objects.using(database).filter(
        page="home",
        group="catalog",
        section_title_en="Our products",
    ).update(section_title_en="Popular gift sets")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_feedbacksubmission_source"),
    ]

    operations = [
        migrations.RunPython(update_catalog_title, restore_catalog_title),
    ]
