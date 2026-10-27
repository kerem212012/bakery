from django.test import TestCase
from django.urls import reverse

from .models import Category, Product


class CatalogModelTests(TestCase):
    def test_category_and_product_generate_unique_slugs(self):
        first_category = Category.objects.create(name="Подарки")
        second_category = Category.objects.create(name="Подарки")
        product = Product.objects.create(
            name="Набор для команды",
            category=first_category,
            is_featured=True,
        )

        self.assertEqual(first_category.slug, "подарки")
        self.assertEqual(second_category.slug, "подарки-2")
        self.assertEqual(product.slug, "набор-для-команды")
        self.assertEqual(product.category, first_category)


class CatalogPageTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Корпоративные подарки",
            description="Для коллег и партнёров",
        )
        self.product = Product.objects.create(
            name="Подарочный набор",
            category=self.category,
            description="Авторский набор",
            price="1490.00",
            is_active=True,
        )

    def test_catalog_page_lists_categories_before_products(self):
        response = self.client.get(reverse("catalog:category_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.category.name)
        self.assertContains(
            response,
            reverse("catalog:category_detail", args=[self.category.slug]),
        )
        self.assertContains(response, self.product.name)

    def test_catalog_filters_by_category_and_price(self):
        affordable_product = Product.objects.create(
            name="Недорогая позиция",
            category=self.category,
            price="250.00",
        )
        other_category = Category.objects.create(name="Праздничные наборы")
        Product.objects.create(
            name="Дорогая позиция",
            category=other_category,
            price="5000.00",
        )

        response = self.client.get(
            reverse("catalog:category_list"),
            {
                "categories": [self.category.pk],
                "min_price": "200",
                "max_price": "2000",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)
        self.assertContains(response, affordable_product.name)
        self.assertNotContains(response, "Дорогая позиция")

    def test_catalog_search_and_price_sort(self):
        Product.objects.create(
            name="Самая доступная",
            category=self.category,
            price="100.00",
        )
        Product.objects.create(
            name="Кремовый набор",
            category=self.category,
            description="Набор со сладким кремом",
            price="3000.00",
        )

        response = self.client.get(
            reverse("catalog:category_list"),
            {"query": "крем", "sort": "price_desc"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Кремовый набор")
        self.assertNotContains(response, "Самая доступная")
        self.assertNotContains(response, self.product.name)

    def test_catalog_marks_size_selector_with_8_cm_base_price(self):
        response = self.client.get(reverse("catalog:category_list"))

        self.assertContains(response, 'data-size-price-control')
        self.assertContains(response, 'data-base-price="1490.00"')
        self.assertContains(response, '<option value="8" selected>8 см</option>')

    def test_product_detail_exposes_size_choices_and_base_price(self):
        response = self.client.get(
            reverse(
                "catalog:product_detail",
                args=[self.category.slug, self.product.slug],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-size-cm="8" aria-pressed="true"')
        self.assertContains(response, 'data-base-price="1490.00"')
        self.assertContains(response, 'data-option-choice aria-pressed="true"')
        self.assertContains(response, 'aria-label="Выберите покрытие"')
        self.assertContains(response, 'aria-label="Выберите упаковку"')

    def test_catalog_rejects_invalid_price_range_and_shows_error(self):
        response = self.client.get(
            reverse("catalog:category_list"),
            {"min_price": "1000", "max_price": "100"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Укажите верхнюю границу не меньше нижней.",
            response.context["filter_form"].errors["max_price"],
        )
        self.assertContains(response, self.product.name)

    def test_favorite_toggle_adds_and_removes_product_from_session(self):
        url = reverse("catalog:toggle_favorite", args=[self.product.pk])

        response = self.client.post(
            url,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"is_favorite": True, "favorites_count": 1})
        self.assertContains(
            self.client.get(reverse("accounts:favorites")),
            self.product.name,
        )

        response = self.client.post(
            url,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"is_favorite": False, "favorites_count": 0})
        self.assertNotContains(
            self.client.get(reverse("accounts:favorites")),
            self.product.name,
        )

    def test_favorite_toggle_requires_post_and_rejects_inactive_products(self):
        url = reverse("catalog:toggle_favorite", args=[self.product.pk])

        self.assertEqual(self.client.get(url).status_code, 405)

        self.product.is_active = False
        self.product.save()
        self.assertEqual(self.client.post(url).status_code, 404)

    def test_favorite_toggle_redirects_back_to_the_current_page(self):
        catalog_url = reverse("catalog:category_list")
        toggle_url = reverse("catalog:toggle_favorite", args=[self.product.pk])

        response = self.client.post(toggle_url, {"next": catalog_url})

        self.assertRedirects(response, catalog_url)
        self.assertContains(
            self.client.get(catalog_url),
            'aria-pressed="true"',
        )

        favorites_url = reverse("accounts:favorites")
        response = self.client.post(toggle_url, {"next": favorites_url})

        self.assertRedirects(response, favorites_url)
        self.assertNotContains(self.client.get(favorites_url), self.product.name)

    def test_category_page_lists_only_that_categories_active_products(self):
        other_category = Category.objects.create(name="Праздничные наборы")
        Product.objects.create(
            name="Товар другой категории",
            category=other_category,
            is_active=True,
        )
        Product.objects.create(
            name="Скрытый товар",
            category=self.category,
            is_active=False,
        )

        response = self.client.get(
            reverse("catalog:category_detail", args=[self.category.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)
        self.assertContains(response, "1490.00 ₽")
        self.assertNotContains(response, "Товар другой категории")
        self.assertNotContains(response, "Скрытый товар")

    def test_inactive_category_is_not_accessible(self):
        inactive_category = Category.objects.create(
            name="Архив",
            is_active=False,
        )

        response = self.client.get(
            reverse("catalog:category_detail", args=[inactive_category.slug])
        )

        self.assertEqual(response.status_code, 404)
