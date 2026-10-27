from datetime import date, timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Product
from .calculator import calculate_quote
from .models import Preorder


class CalculatorTests(TestCase):
    def setUp(self):
        self.configuration = {
            "flavor": "classic",
            "quantity": 100,
            "size": "5",
            "shape": "heart",
            "coating": "icing",
            "packaging": "ribbon",
            "delivery": "moscow",
            "payment": "organization",
        }

    def test_reference_configuration_calculates_a_consistent_total(self):
        quote = calculate_quote(self.configuration)

        self.assertEqual(quote["unit_price"], Decimal("98"))
        self.assertEqual(quote["discount_percent"], 20)
        self.assertEqual(quote["delivery_cost"], Decimal("700"))
        self.assertEqual(quote["total_price"], Decimal("8540.00"))

    def test_size_and_quantity_change_the_quote(self):
        self.configuration["size"] = "10"
        self.configuration["quantity"] = 20

        quote = calculate_quote(self.configuration)

        self.assertEqual(quote["unit_price"], Decimal("186"))
        self.assertEqual(quote["discount_percent"], 10)
        self.assertEqual(quote["total_price"], Decimal("4048.00"))

    def test_homepage_renders_calculator_and_preorder_form(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="calculator"')
        self.assertContains(response, "Рассчитайте стоимость")
        self.assertContains(response, 'name="quantity"')
        self.assertContains(response, 'name="attachments"')
        self.assertContains(response, "Отправить предзаказ")

    def test_homepage_search_button_opens_name_search_form(self):
        response = self.client.get("/")

        self.assertContains(response, 'aria-controls="home-search-panel"')
        self.assertContains(
            response,
            f'action="{reverse("catalog:category_list")}"',
        )
        self.assertContains(response, 'name="query" maxlength="100"')
        self.assertContains(response, 'name="search_mode" value="name"')
        self.assertContains(response, ">Найти</button>")

    def test_valid_preorder_is_saved_with_server_calculated_quote(self):
        response = self.client.post(
            "/",
            {
                **self.configuration,
                "name": "Иван",
                "email": "ivan@example.com",
                "phone": "+74951234567",
                "delivery_date": (date.today() + timedelta(days=3)).isoformat(),
                "address": "Москва, ул. Пряничная, 12",
                "comment": "Макет приложен",
                "consent_given": "on",
            },
        )

        self.assertRedirects(response, "/#calculator")
        preorder = Preorder.objects.get()
        self.assertEqual(preorder.configuration["quantity"], 100)
        self.assertEqual(preorder.unit_price, Decimal("98"))
        self.assertEqual(preorder.discount_percent, 20)
        self.assertEqual(preorder.total_price, Decimal("8540.00"))

    def test_preorder_accepts_supported_attachment(self):
        upload = SimpleUploadedFile("design.png", b"image-data", content_type="image/png")

        response = self.client.post(
            "/",
            {
                **self.configuration,
                "name": "Иван",
                "email": "ivan@example.com",
                "phone": "+74951234567",
                "address": "Москва",
                "consent_given": "on",
                "attachments": upload,
            },
        )

        self.assertRedirects(response, "/#calculator")
        preorder = Preorder.objects.get()
        self.assertEqual(preorder.attachments.count(), 1)
        preorder.attachments.first().file.delete(save=False)

    def test_preorder_requires_consent(self):
        response = self.client.post(
            "/",
            {
                **self.configuration,
                "name": "Иван",
                "email": "ivan@example.com",
                "phone": "+74951234567",
                "address": "Москва",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Preorder.objects.exists())
        self.assertContains(response, "Необходимо дать согласие на обработку данных.")

    def test_pickup_does_not_require_delivery_address(self):
        response = self.client.post(
            "/",
            {
                **self.configuration,
                "delivery": "pickup",
                "name": "Иван",
                "email": "ivan@example.com",
                "phone": "+74951234567",
                "address": "",
                "consent_given": "on",
            },
        )

        self.assertRedirects(response, "/#calculator")
        self.assertEqual(Preorder.objects.get().address, "")

    def test_unsupported_upload_is_rejected(self):
        upload = SimpleUploadedFile("script.exe", b"not-an-image")

        response = self.client.post(
            "/",
            {
                **self.configuration,
                "name": "Иван",
                "email": "ivan@example.com",
                "phone": "+74951234567",
                "address": "Москва",
                "consent_given": "on",
                "attachments": upload,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Preorder.objects.exists())


class HomePageCatalogTests(TestCase):
    def test_about_page_renders_reference_sections_and_navigation_links(self):
        response = self.client.get(reverse("about"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<title>О нас — Лукоморье</title>")
        self.assertContains(response, 'aria-current="page">О нас</span>')
        self.assertContains(response, "Наша история")
        self.assertContains(response, "Наши ценности")
        self.assertContains(response, "5000+")
        self.assertContains(response, 'href="mailto:hello@lukomorye.example"')
        self.assertContains(response, f'href="{reverse("about")}">О нас</a>')

    def test_homepage_favorites_and_cart_buttons_open_their_pages(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{reverse("about")}">О нас</a>')
        self.assertContains(
            response,
            f'href="{reverse("accounts:favorites")}" aria-label="Избранное"',
        )
        self.assertContains(
            response,
            f'href="{reverse("catalog:cart")}" aria-label="Корзина, 0 товаров"',
        )

        session = self.client.session
        session["cart"] = {"3:8:painting:classic:gift_box": {"quantity": 2}}
        session.save()
        response = self.client.get("/")

        self.assertContains(
            response,
            f'href="{reverse("catalog:cart")}" aria-label="Корзина, 2 товаров"',
        )
        self.assertContains(response, '<span class="cart-header-count">2</span>')

    def test_homepage_renders_hero_carousel(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="hero-track"')
        self.assertContains(response, 'data-hero-direction="1"')
        self.assertContains(response, 'data-hero-direction="-1"')
        self.assertContains(response, 'data-hero-slide="2"')
        self.assertContains(response, "Подарки, созданные с душой")
        self.assertContains(response, "Внимание, которое объединяет")

    def test_homepage_renders_active_catalog_products(self):
        category = Category.objects.create(name="Подарки компании")
        inactive_category = Category.objects.create(
            name="Скрытая категория",
            is_active=False,
        )
        Product.objects.create(
            name="Праздничный набор",
            category=category,
            description="Подарок для команды",
            is_featured=True,
        )
        Product.objects.create(
            name="Скрытый товар",
            category=category,
            is_featured=False,
        )
        Product.objects.create(
            name="Товар скрытой категории",
            category=inactive_category,
            is_featured=True,
        )

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Подарки компании")
        self.assertContains(response, "Праздничный набор")
        self.assertContains(response, "Скрытый товар")
        self.assertNotContains(response, "Скрытая категория")
        self.assertNotContains(response, "Товар скрытой категории")
