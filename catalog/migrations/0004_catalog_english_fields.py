from django.db import migrations, models


CATEGORY_TRANSLATIONS = {
    "corporate-gifts": ("Corporate gifts", "For teams and partners"),
    "holiday-sets": ("Holiday sets", "For special occasions"),
    "personal-gifts": ("Personalized gifts", "Customized in your brand style"),
    "sweet-compliments": ("Sweet treats", "Small gestures of appreciation"),
    "branded-gifts": ("Branded gifts", "Customized in your brand style"),
    "event-gifts": ("Gifts for special events", "Gifts for special moments"),
}

PRODUCT_TRANSLATIONS = {
    "heart-cookies": ("Heart-shaped cookies", "A gift with a heartfelt message"),
    "gift-bears": ("Gift bears", "A sweet gift for someone special"),
    "berry-cupcakes": ("Berry cupcakes", "A berry-filled set for your celebration"),
    "ribbon-gift-box": ("Gift box", "A curated set in festive packaging"),
    "team-gift-set": ("Team gift set", "A gift set for colleagues and partners"),
    "spring-gift-set": ("Spring gift set", "A floral gift for a special day"),
}

FILTER_TRANSLATIONS = {
    ("size", "6"): "6 cm",
    ("size", "8"): "8 cm",
    ("size", "10"): "10 cm",
    ("size", "12"): "12 cm",
    ("size", "15"): "15 cm",
    ("coating", "painting"): "Hand-painted icing",
    ("coating", "printing"): "Printed icing",
    ("coating", "classic"): "Classic",
    ("coating", "chocolate"): "Chocolate",
    ("coating", "none"): "No coating",
    ("dough", "classic"): "Classic",
    ("dough", "chocolate"): "Chocolate",
    ("dough", "vanilla"): "Vanilla",
    ("dough", "spiced"): "Spiced",
    ("color", "white"): "White",
    ("color", "pink"): "Pink",
    ("color", "red"): "Red",
    ("color", "blue"): "Blue",
    ("color", "green"): "Green",
    ("color", "gold"): "Gold",
    ("color", "multicolor"): "Multicolored",
    ("occasion", "birthday"): "Birthday",
    ("occasion", "wedding"): "Wedding",
    ("occasion", "corporate"): "Corporate gift",
    ("occasion", "new-year"): "New Year",
    ("occasion", "march-8"): "March 8",
    ("occasion", "february-23"): "February 23",
    ("occasion", "easter"): "Easter",
    ("occasion", "children"): "Children's celebration",
    ("packaging", "gift_box"): "Gift box",
    ("packaging", "kraft_box"): "Kraft box",
    ("packaging", "individual"): "Custom packaging",
    ("packaging", "none"): "No packaging",
}


def populate_english_catalog(apps, schema_editor):
    database = schema_editor.connection.alias
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")
    ProductFilterOption = apps.get_model("catalog", "ProductFilterOption")

    for slug, (name, description) in CATEGORY_TRANSLATIONS.items():
        Category.objects.using(database).filter(slug=slug).update(
            name_en=name,
            description_en=description,
        )

    for slug, (name, description) in PRODUCT_TRANSLATIONS.items():
        Product.objects.using(database).filter(slug=slug).update(
            name_en=name,
            description_en=description,
        )

    for (filter_type, value), label in FILTER_TRANSLATIONS.items():
        ProductFilterOption.objects.using(database).filter(
            filter_type=filter_type,
            value=value,
        ).update(label_en=label)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0003_productfilteroption"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="name_en",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="category",
            name="description_en",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="product",
            name="name_en",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="product",
            name="description_en",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="productfilteroption",
            name="label_en",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.RunPython(populate_english_catalog, migrations.RunPython.noop),
    ]
