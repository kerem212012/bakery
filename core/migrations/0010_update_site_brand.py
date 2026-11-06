from django.db import migrations, models


def update_site_brand(apps, schema_editor):
    database = schema_editor.connection.alias
    replacements = (
        ("Лукоморья", "«Вкусно Да Сладко»"),
        ("Лукоморьем", "«Вкусно Да Сладко»"),
        ("Лукоморье", "«Вкусно Да Сладко»"),
        ("Lukomorye", "Vkusno Da Sladko"),
    )
    for model_name in ("SitePageContent", "SitePageSection"):
        model = apps.get_model("core", model_name)
        text_fields = [
            field.name
            for field in model._meta.get_fields()
            if isinstance(field, (models.CharField, models.TextField))
        ]
        for instance in model.objects.using(database).all().iterator():
            changed_fields = []
            for field_name in text_fields:
                value = getattr(instance, field_name)
                if not value:
                    continue
                updated_value = value
                for old_brand, new_brand in replacements:
                    updated_value = updated_value.replace(old_brand, new_brand)
                if updated_value != value:
                    setattr(instance, field_name, updated_value)
                    changed_fields.append(field_name)
            if changed_fields:
                instance.save(update_fields=changed_fields)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_feedbacksubmission_is_hidden"),
    ]

    operations = [
        migrations.RunPython(update_site_brand, migrations.RunPython.noop),
    ]
