from django.db import migrations


def create_sample_catalog(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")
    database = schema_editor.connection.alias

    categories = (
        (
            "corporate-gifts",
            "Корпоративные подарки",
            "Для команды и партнёров",
            "https://images.unsplash.com/photo-1513883049090-d0b7439799bf?auto=format&fit=crop&w=800&q=80",
        ),
        (
            "holiday-sets",
            "Праздничные наборы",
            "Для особенных дат",
            "https://images.unsplash.com/photo-1490750967868-88aa4486c946?auto=format&fit=crop&w=800&q=80",
        ),
        (
            "personal-gifts",
            "Персональные подарки",
            "С вашим фирменным стилем",
            "https://images.unsplash.com/photo-1549465220-1a8b9238cd48?auto=format&fit=crop&w=800&q=80",
        ),
        ("sweet-compliments", "Сладкие комплименты", "Небольшие знаки внимания", ""),
        ("branded-gifts", "Подарки с логотипом", "С вашим фирменным стилем", ""),
        ("event-gifts", "Для важных событий", "Подарки для особых моментов", ""),
    )

    category_by_slug = {}
    for order, (slug, name, description, image_url) in enumerate(categories):
        category, _ = Category.objects.using(database).get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "description": description,
                "image_url": image_url,
                "display_order": order,
                "is_active": True,
            },
        )
        category_by_slug[slug] = category

    products = (
        (
            "heart-cookies",
            "Печенье-сердца",
            "Подарок с тёплым посланием",
            "https://images.unsplash.com/photo-1499636136210-6f4ee915583e?auto=format&fit=crop&w=600&q=80",
            "sweet-compliments",
            1490,
        ),
        (
            "gift-bears",
            "Подарочные мишки",
            "Милый подарок для особенного человека",
            "https://images.unsplash.com/photo-1513201099705-a9746e1e201f?auto=format&fit=crop&w=600&q=80",
            "personal-gifts",
            2490,
        ),
        (
            "berry-cupcakes",
            "Ягодные капкейки",
            "Набор с ягодами для праздничного стола",
            "https://images.unsplash.com/photo-1486427944299-d1955d23e34d?auto=format&fit=crop&w=600&q=80",
            "holiday-sets",
            1990,
        ),
        (
            "ribbon-gift-box",
            "Подарочная коробка",
            "Авторский набор в праздничной упаковке",
            "https://images.unsplash.com/photo-1549465220-1a8b9238cd48?auto=format&fit=crop&w=600&q=80",
            "corporate-gifts",
            3490,
        ),
        (
            "team-gift-set",
            "Набор для команды",
            "Подарочный набор для коллег и партнёров",
            "https://images.unsplash.com/photo-1513883049090-d0b7439799bf?auto=format&fit=crop&w=600&q=80",
            "corporate-gifts",
            4990,
        ),
        (
            "spring-gift-set",
            "Весенний набор",
            "Цветочный подарок для праздничного дня",
            "https://images.unsplash.com/photo-1490750967868-88aa4486c946?auto=format&fit=crop&w=600&q=80",
            "holiday-sets",
            2990,
        ),
    )

    for order, (slug, name, description, image_url, category_slug, price) in enumerate(products):
        Product.objects.using(database).get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "description": description,
                "category": category_by_slug[category_slug],
                "image_url": image_url,
                "price": price,
                "display_order": order,
                "is_active": True,
                "is_featured": True,
            },
        )


def remove_sample_catalog(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")
    database = schema_editor.connection.alias

    Product.objects.using(database).filter(
        slug__in=(
            "heart-cookies",
            "gift-bears",
            "berry-cupcakes",
            "ribbon-gift-box",
            "team-gift-set",
            "spring-gift-set",
        )
    ).delete()
    Category.objects.using(database).filter(
        slug__in=(
            "corporate-gifts",
            "holiday-sets",
            "personal-gifts",
            "sweet-compliments",
            "branded-gifts",
            "event-gifts",
        )
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_sample_catalog, remove_sample_catalog),
    ]
