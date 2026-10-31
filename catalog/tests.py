from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import Preorder
from user.models import CustomerProfile

from .models import Category, Product, ProductFilterOption


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


class CatalogAdminTests(TestCase):
    def setUp(self):
        admin_user = get_user_model().objects.create_superuser(
            username="catalog_admin",
            email="catalog-admin@example.com",
            password="Secure-admin-password-482!",
        )
        self.client.force_login(admin_user)
        self.category = Category.objects.create(
            name="Подарочные наборы",
            name_en="Gift sets",
        )

    def test_admin_can_create_product_with_english_catalog_content(self):
        response = self.client.post(
            reverse("admin:catalog_product_add"),
            {
                "name": "Пряничный набор",
                "name_en": "Gingerbread gift set",
                "slug": "",
                "category": str(self.category.pk),
                "description": "Набор ручной работы",
                "description_en": "A handmade gift set",
                "price": "2500.00",
                "image_url": "",
                "filter_options": [],
                "is_active": "on",
                "is_featured": "on",
                "display_order": "0",
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 302)
        product = Product.objects.get(name="Пряничный набор")
        self.assertEqual(product.name_en, "Gingerbread gift set")
        self.assertEqual(product.description_en, "A handmade gift set")
        self.assertEqual(product.category, self.category)
        self.assertTrue(product.is_featured)

    def test_admin_dashboard_links_to_catalog_and_orders(self):
        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Лукоморье — управление сайтом")
        self.assertContains(response, reverse("admin:catalog_product_changelist"))
        self.assertContains(response, reverse("admin:catalog_category_changelist"))
        self.assertContains(response, reverse("admin:core_preorder_changelist"))


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

    def test_catalog_sidebar_shows_quick_categories_and_price_range(self):
        response = self.client.get(reverse("catalog:category_list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["total_product_count"],
            Product.objects.filter(is_active=True, category__is_active=True).count(),
        )
        self.assertContains(response, "Все товары")
        self.assertContains(response, 'data-price-range-min')
        self.assertContains(response, 'data-price-range-max')
        self.assertContains(response, 'aria-controls="catalog-category-filters"')

    def test_price_sliders_keep_default_bounds_when_other_filters_are_submitted(self):
        response = self.client.get(
            reverse("catalog:category_list"),
            {"categories": [self.category.pk], "min_price": "", "max_price": ""},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'value="0" aria-label="Минимальная цена" data-price-range-min',
        )
        self.assertContains(
            response,
            'value="25000" aria-label="Максимальная цена" data-price-range-max',
        )

    def test_price_sliders_keep_submitted_price_bounds(self):
        response = self.client.get(
            reverse("catalog:category_list"),
            {"min_price": "500", "max_price": "2300"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'value="500" aria-label="Минимальная цена" data-price-range-min',
        )
        self.assertContains(
            response,
            'value="2300" aria-label="Максимальная цена" data-price-range-max',
        )

    def test_category_overview_lists_active_categories(self):
        inactive_category = Category.objects.create(
            name="Скрытая категория",
            is_active=False,
        )

        response = self.client.get(reverse("catalog:categories"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Все категории")
        self.assertContains(response, self.category.name)
        self.assertContains(
            response,
            reverse("catalog:category_detail", args=[self.category.slug]),
        )
        self.assertNotContains(response, inactive_category.name)

    def test_english_catalog_uses_translated_category_and_product_fields(self):
        self.category.name_en = "Corporate gifts"
        self.category.description_en = "Gifts for colleagues and partners"
        self.category.save(update_fields=("name_en", "description_en"))
        self.product.name_en = "Gift set"
        self.product.description_en = "A curated gift"
        self.product.save(update_fields=("name_en", "description_en"))
        self.client.post(
            reverse("set_language"),
            {"language": "en", "next": reverse("catalog:category_list")},
        )

        response = self.client.get(reverse("catalog:category_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Corporate gifts")
        self.assertContains(response, "Gift set")
        self.assertContains(response, "Apply filters")

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

    def test_catalog_filters_by_multiple_product_attributes(self):
        other_product = Product.objects.create(
            name="Другой подарок",
            category=self.category,
            price="1790.00",
        )
        size = ProductFilterOption.objects.get(filter_type="size", value="8")
        occasion = ProductFilterOption.objects.get_or_create(
            filter_type="occasion",
            value="birthday",
            defaults={"label": "День рождения"},
        )[0]
        size.products.add(self.product, other_product)
        occasion.products.add(self.product)

        response = self.client.get(
            reverse("catalog:category_list"),
            {"sizes": ["8"], "occasions": ["birthday"]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)
        self.assertNotContains(response, other_product.name)
        self.assertQuerySetEqual(
            response.context["filter_form"].fields["sizes"].choices,
            ProductFilterOption.objects.filter(
                filter_type="size",
                is_active=True,
            ).values_list("value", "label"),
            transform=tuple,
            ordered=False,
        )

    def test_catalog_renders_all_product_attribute_filter_sections(self):
        response = self.client.get(reverse("catalog:category_list"))

        self.assertEqual(response.status_code, 200)
        for label in ("Размер", "Покрытие", "Вид теста", "Цвет", "Повод", "Упаковка"):
            self.assertContains(response, label)
        self.assertContains(response, 'name="sizes"')
        self.assertContains(response, 'name="colors"')
        self.assertContains(response, 'name="packaging"')

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

    def test_catalog_name_search_does_not_match_description(self):
        description_match = Product.objects.create(
            name="Сердце",
            category=self.category,
            description="Подарочный набор",
        )

        response = self.client.get(
            reverse("catalog:category_list"),
            {"query": "подарочный", "search_mode": "name"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)
        self.assertNotContains(response, description_match.name)

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
        self.assertContains(
            response,
            'data-option-choice data-cart-value="painting" aria-pressed="true"',
        )
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
        self.assertContains(
            response,
            f'href="{reverse("catalog:categories")}">← Все категории</a>',
        )
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


class CartTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Пряники")
        self.product = Product.objects.create(
            name="Пряник с росписью",
            category=self.category,
            price="1490.00",
        )
        self.add_url = reverse("catalog:add_to_cart", args=[self.product.pk])
        self.cart_url = reverse("catalog:cart")
        self.user = get_user_model().objects.create_user(
            username="customer",
            password="secure-test-password",
        )
        self.client.force_login(self.user)

    def add_product(self, **overrides):
        data = {
            "quantity": "1",
            "size": "8",
            "coating": "painting",
            "dough": "classic",
            "packaging": "gift_box",
        }
        data.update(overrides)
        return self.client.post(self.add_url, data)

    def test_guest_cannot_add_to_cart_and_is_sent_to_login(self):
        self.client.logout()

        response = self.add_product()

        self.assertRedirects(
            response,
            f'{reverse("accounts:login")}?next={reverse("catalog:category_list")}',
        )
        self.assertNotIn("cart", self.client.session)

    def test_guest_catalog_buttons_link_to_login(self):
        self.client.logout()

        response = self.client.get(reverse("catalog:category_list"))

        self.assertContains(
            response,
            f'href="{reverse("accounts:login")}?next={reverse("catalog:category_list")}"',
        )
        self.assertContains(response, "Войти, чтобы добавить")
        self.assertContains(response, 'class="catalog-cart-form"')

    def test_guest_product_detail_links_to_login(self):
        self.client.logout()

        product_url = reverse(
            "catalog:product_detail",
            args=[self.category.slug, self.product.slug],
        )
        response = self.client.get(product_url)

        self.assertContains(
            response,
            f'href="{reverse("accounts:login")}?next={product_url}"',
        )
        self.assertNotContains(response, '<button class="primary-action" type="submit">В корзину</button>')

    def test_add_to_cart_saves_validated_options_and_updates_header_count(self):
        response = self.add_product(quantity="2", size="10", dough="chocolate")

        self.assertRedirects(response, self.cart_url)
        response = self.client.get(self.cart_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)
        self.assertContains(response, "cart-shell")
        self.assertContains(response, "2 товара")
        self.assertContains(response, "2328")
        self.assertContains(response, 'aria-label="Корзина, 2 товаров"')
        self.assertContains(response, 'class="cart-payment-select"')
        self.assertContains(response, "Онлайн-списание на сайте пока не подключено.")
        self.assertContains(response, "Способ оплаты")
        self.assertContains(response, "Свяжитесь с нами")
        self.assertContains(response, 'class="cart-field-control"')
        self.assertContains(response, 'class="cart-upload"')
        self.assertContains(response, 'class="cart-submit-button"')

    def test_saved_account_address_is_prefilled_in_checkout(self):
        self.add_product()
        CustomerProfile.objects.create(
            user=self.user,
            delivery_address="Москва, ул. Тестовая, 1",
        )

        response = self.client.get(self.cart_url)

        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.context["form"].initial.get("address"), "Москва, ул. Тестовая, 1")
        self.assertContains(response, 'value="Москва, ул. Тестовая, 1"')

    def test_add_to_cart_merges_identical_variants_and_rejects_bad_options(self):
        self.add_product(quantity="3")
        self.add_product(quantity="2")

        response = self.client.get(self.cart_url)
        self.assertContains(response, "5 товара")

        self.client.post(self.add_url, {"size": "999", "quantity": "1"})
        response = self.client.get(self.cart_url)
        self.assertContains(response, "5 товара")

    def test_cart_update_remove_and_clear(self):
        self.add_product()
        item_id = next(iter(self.client.session["cart"]))

        response = self.client.post(
            reverse("catalog:update_cart_item", args=[item_id]),
            {
                "quantity": "3",
                "size": "10",
                "coating": "printing",
                "dough": "spiced",
                "packaging": "kraft_box",
            },
        )
        self.assertRedirects(response, self.cart_url)
        self.assertEqual(len(self.client.session["cart"]), 1)
        updated_id = next(iter(self.client.session["cart"]))
        self.assertNotEqual(updated_id, item_id)
        self.assertEqual(self.client.session["cart"][updated_id]["quantity"], 3)

        self.client.post(reverse("catalog:remove_cart_item", args=[updated_id]))
        self.assertFalse(self.client.session.get("cart"))
        self.add_product()
        self.client.post(reverse("catalog:clear_cart"))
        self.assertFalse(self.client.session.get("cart"))

    def test_checkout_creates_preorder_and_clears_cart(self):
        self.add_product(quantity="2")
        response = self.client.post(
            self.cart_url,
            {
                "delivery": "pickup",
                "payment": "card",
                "name": "Анна",
                "phone": "+7 900 000-00-00",
                "email": "anna@example.com",
                "consent_given": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        preorder = Preorder.objects.get()
        self.assertEqual(
            response.url,
            reverse("accounts:order_detail", args=[preorder.pk]),
        )
        self.assertEqual(preorder.user, self.user)
        self.assertEqual(preorder.total_price, 2980)
        self.assertEqual(preorder.configuration["items"][0]["product_id"], self.product.pk)
        self.assertNotIn("cart", self.client.session)
        order_page = self.client.get(response.url)
        self.assertContains(order_page, f"Заказ #{preorder.pk} оформлен")
        self.assertContains(order_page, self.product.name)

    def test_successful_checkout_updates_saved_delivery_address(self):
        self.add_product()

        response = self.client.post(
            self.cart_url,
            {
                "delivery": "moscow",
                "payment": "card",
                "name": "Анна",
                "phone": "+7 900 000-00-00",
                "email": "anna@example.com",
                "address": "Москва, ул. Садовая, 7",
                "consent_given": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self.user.customer_profile.delivery_address,
            "Москва, ул. Садовая, 7",
        )

    def test_guest_checkout_creates_order_without_account_owner(self):
        self.add_product(quantity="2")
        cart_data = self.client.session["cart"]
        self.client.logout()
        session = self.client.session
        session["cart"] = cart_data
        session.save()

        response = self.client.post(
            self.cart_url,
            {
                "delivery": "pickup",
                "payment": "card",
                "name": "Анна",
                "phone": "+7 900 000-00-00",
                "email": "anna@example.com",
                "consent_given": "on",
            },
        )

        self.assertRedirects(response, self.cart_url)
        preorder = Preorder.objects.get()
        self.assertIsNone(preorder.user)
        self.assertEqual(preorder.total_price, 2980)
        self.assertNotIn("cart", self.client.session)

    def test_checkout_requires_delivery_address(self):
        self.add_product()
        response = self.client.post(
            self.cart_url,
            {
                "delivery": "moscow",
                "payment": "card",
                "name": "Анна",
                "phone": "+7 900 000-00-00",
                "email": "anna@example.com",
                "consent_given": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Укажите адрес доставки.")
        self.assertContains(response, "Не удалось оформить заказ. Проверьте данные:")
        self.assertEqual(Preorder.objects.count(), 0)
        self.assertTrue(self.client.session.get("cart"))
