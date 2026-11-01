from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from catalog.models import Category, Product
from .calculator import calculate_quote
from .models import FeedbackSubmission, Preorder, SiteContentBlock


class AdminDashboardTests(TestCase):
    def setUp(self):
        self.url = reverse("admin_dashboard")

    def test_dashboard_requires_staff_access(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

        customer = get_user_model().objects.create_user(
            username="dashboard_customer",
            password="Customer-password-482!",
        )
        self.client.force_login(customer)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_staff_dashboard_shows_management_links_and_catalog_counts(self):
        admin_user = get_user_model().objects.create_superuser(
            username="dashboard_admin",
            email="dashboard-admin@example.com",
            password="Secure-admin-password-482!",
        )
        existing_product_count = Product.objects.count()
        existing_active_product_count = Product.objects.filter(is_active=True).count()
        category = Category.objects.create(name="Gift sets")
        Product.objects.create(name="Active product", category=category)
        Product.objects.create(name="Hidden product", category=category, is_active=False)
        self.client.force_login(admin_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Панель управления")
        self.assertContains(response, reverse("admin_section_new", args=("products",)))
        self.assertContains(response, reverse("site_content_manager"))
        self.assertContains(response, "Фото и описания сайта")
        self.assertContains(response, reverse("admin_section", args=("categories",)))
        self.assertContains(response, reverse("admin_section", args=("orders",)))
        self.assertContains(response, reverse("admin_section", args=("filters",)))
        self.assertContains(response, reverse("admin_section", args=("customers",)))
        self.assertContains(response, reverse("admin_section", args=("messages",)))
        self.assertNotContains(response, "/admin/catalog/")
        self.assertNotContains(response, "/admin/core/")
        self.assertNotContains(response, "/admin/user/")
        self.assertEqual(
            response.context["product_count"],
            existing_product_count + 2,
        )
        self.assertEqual(
            response.context["active_product_count"],
            existing_active_product_count + 1,
        )

    def test_site_content_editor_is_superuser_only(self):
        manager = get_user_model().objects.create_user(
            username="content_manager",
            password="test-password",
            is_staff=True,
        )
        self.client.force_login(manager)

        response = self.client.get(reverse("site_content_manager"))
        self.assertEqual(response.status_code, 403)

        admin_user = get_user_model().objects.create_superuser(
            username="content_admin",
            email="content-admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)
        response = self.client.get(reverse("site_content_manager"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Добавить контент на сайт")
        self.assertContains(response, "не Django-админка")

    def test_site_content_manager_saves_new_page_block(self):
        admin_user = get_user_model().objects.create_superuser(
            username="content_creator",
            email="content-creator@example.com",
            password="content-password",
        )
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse("site_content_manager"),
            {
                "page": SiteContentBlock.Page.ABOUT,
                "title": "Custom page heading",
                "title_en": "Custom page heading in English",
                "description": "Custom page description",
                "description_en": "Custom page description in English",
                "display_order": "2",
                "is_active": "on",
            },
        )

        self.assertRedirects(response, reverse("site_content_manager"))
        block = SiteContentBlock.objects.get()
        self.assertEqual(block.page, SiteContentBlock.Page.ABOUT)
        self.assertEqual(block.title, "Custom page heading")
        self.assertEqual(block.display_order, 2)

    def test_custom_admin_section_requires_view_permission(self):
        manager = get_user_model().objects.create_user(
            username="section_manager",
            is_staff=True,
        )
        self.client.force_login(manager)

        response = self.client.get(reverse("admin_section", args=("products",)))

        self.assertEqual(response.status_code, 403)

        manager.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="catalog",
                codename="view_product",
            )
        )
        response = self.client.get(reverse("admin_section", args=("products",)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Товары")

    def test_all_admin_section_pages_render_for_superuser(self):
        admin_user = get_user_model().objects.create_user(
            username="all_sections_admin",
            email="all-sections@example.com",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(admin_user)

        for section in (
            "products",
            "categories",
            "filters",
            "orders",
            "customers",
            "messages",
        ):
            with self.subTest(section=section):
                response = self.client.get(reverse("admin_section", args=(section,)))
                self.assertEqual(response.status_code, 200)

        for section in ("categories", "filters"):
            with self.subTest(new_section=section):
                response = self.client.get(
                    reverse("admin_section_new", args=(section,))
                )
                self.assertEqual(response.status_code, 200)

    def test_custom_product_page_creates_product(self):
        admin_user = get_user_model().objects.create_superuser(
            username="section_product_admin",
            email="section-product-admin@example.com",
            password="section-password",
        )
        category = Category.objects.create(name="Custom section category")
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse("admin_section_new", args=("products",)),
            {
                "name": "Custom section product",
                "name_en": "Custom section product EN",
                "category": category.pk,
                "description": "Description",
                "description_en": "English description",
                "price": "120.00",
                "image_url": "",
                "display_order": "0",
                "is_active": "on",
                "is_featured": "on",
            },
        )

        product = Product.objects.get(name="Custom section product")
        self.assertRedirects(
            response,
            reverse("admin_section_edit", args=("products", product.pk)),
        )
        self.assertEqual(product.price, Decimal("120.00"))

    def test_custom_order_and_message_pages_update_statuses(self):
        admin_user = get_user_model().objects.create_user(
            username="section_status_admin",
            email="section-status-admin@example.com",
            is_staff=True,
            is_superuser=True,
        )
        order = Preorder.objects.create(
            name="Section order customer",
            email="section-order@example.com",
            phone="+7 900 000-00-00",
            configuration={"quantity": 3},
            unit_price="100.00",
            discount_percent=0,
            delivery_cost="0.00",
            total_price="300.00",
            consent_given=True,
        )
        feedback = FeedbackSubmission.objects.create(
            name="Section feedback customer",
            email="section-feedback@example.com",
            subject="Section feedback subject",
            message="A message for the custom admin page.",
            consent_given=True,
        )
        self.client.force_login(admin_user)

        order_url = reverse("admin_section_edit", args=("orders", order.pk))
        order_response = self.client.get(order_url)
        self.assertEqual(order_response.status_code, 200)
        self.assertContains(order_response, "Section order customer")
        self.assertRedirects(
            self.client.post(order_url, {"status": Preorder.Status.PRODUCTION}),
            order_url,
        )
        order.refresh_from_db()
        self.assertEqual(order.status, Preorder.Status.PRODUCTION)

        feedback_url = reverse("admin_section_edit", args=("messages", feedback.pk))
        feedback_response = self.client.get(feedback_url)
        self.assertEqual(feedback_response.status_code, 200)
        self.assertContains(feedback_response, "A message for the custom admin page.")
        self.assertRedirects(
            self.client.post(
                feedback_url,
                {"status": FeedbackSubmission.Status.RESOLVED},
            ),
            feedback_url,
        )
        feedback.refresh_from_db()
        self.assertEqual(feedback.status, FeedbackSubmission.Status.RESOLVED)

    def test_active_site_content_only_appears_on_its_selected_page(self):
        SiteContentBlock.objects.create(
            page=SiteContentBlock.Page.HOME,
            title="Homepage editorial heading",
            description="Homepage editorial description",
        )
        SiteContentBlock.objects.create(
            page=SiteContentBlock.Page.ABOUT,
            title="About editorial heading",
        )
        SiteContentBlock.objects.create(
            page=SiteContentBlock.Page.HOME,
            title="Hidden editorial heading",
            is_active=False,
        )

        home_response = self.client.get(reverse("home"))
        about_response = self.client.get(reverse("about"))

        self.assertContains(home_response, "Homepage editorial heading")
        self.assertNotContains(home_response, "About editorial heading")
        self.assertNotContains(home_response, "Hidden editorial heading")
        self.assertContains(about_response, "About editorial heading")
        self.assertNotContains(about_response, "Homepage editorial heading")

    def test_all_pages_content_appears_on_public_routes_but_not_editor_pages(self):
        SiteContentBlock.objects.create(
            page=SiteContentBlock.Page.ALL,
            title="Every public page heading",
        )
        SiteContentBlock.objects.create(
            page=SiteContentBlock.Page.HOME,
            title="Homepage only heading",
        )
        admin_user = get_user_model().objects.create_superuser(
            username="all_pages_content_admin",
            email="all-pages-content-admin@example.com",
            password="content-password",
        )
        self.client.force_login(admin_user)

        home_response = self.client.get(reverse("home"))
        cart_response = self.client.get(reverse("catalog:cart"))
        about_response = self.client.get(reverse("about"))
        editor_response = self.client.get(reverse("site_content_manager"))
        dashboard_response = self.client.get(reverse("admin_dashboard"))

        self.assertContains(home_response, "Every public page heading")
        self.assertContains(cart_response, "Every public page heading")
        self.assertContains(about_response, "Every public page heading")
        self.assertNotContains(cart_response, "Homepage only heading")
        self.assertEqual(editor_response.context["site_content_blocks"], ())
        self.assertEqual(dashboard_response.context["site_content_blocks"], ())

    def test_site_content_image_upload_is_rendered(self):
        image_buffer = BytesIO()
        Image.new("RGB", (1, 1), color="white").save(image_buffer, format="PNG")

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                block = SiteContentBlock.objects.create(
                    page=SiteContentBlock.Page.HOME,
                    title="Photo editorial heading",
                    image=SimpleUploadedFile(
                        "editorial.png",
                        image_buffer.getvalue(),
                        content_type="image/png",
                    ),
                )

                response = self.client.get(reverse("home"))

                self.assertContains(response, f'src="{block.image.url}"')

    def test_staff_header_links_to_admin_and_permitted_manager_pages(self):
        manager = get_user_model().objects.create_user(
            username="header_manager",
            password="Secure-manager-password-482!",
            is_staff=True,
        )
        manager.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="core",
                codename="view_preorder",
            )
        )
        self.client.force_login(manager)

        response = self.client.get(reverse("home"))

        self.assertContains(response, reverse("admin_dashboard"))
        self.assertContains(response, reverse("manager_dashboard"))
        self.assertContains(response, "mobile-staff-links")

    def test_non_staff_header_does_not_show_management_links(self):
        customer = get_user_model().objects.create_user(
            username="header_customer",
            password="Customer-password-482!",
        )
        self.client.force_login(customer)

        response = self.client.get(reverse("home"))

        self.assertNotContains(response, reverse("admin_dashboard"))
        self.assertNotContains(response, reverse("manager_dashboard"))


class ManagerDashboardTests(TestCase):
    def setUp(self):
        self.manager_url = reverse("manager_dashboard")
        self.status_url_name = "manager_update_order_status"
        self.manager = get_user_model().objects.create_user(
            username="manager",
            password="Secure-manager-password-482!",
            is_staff=True,
        )
        self.order = Preorder.objects.create(
            name="Alex Customer",
            email="alex@example.com",
            phone="+7 900 000-00-00",
            configuration={"quantity": 2},
            unit_price="100.00",
            discount_percent=0,
            delivery_cost="0.00",
            total_price="200.00",
            consent_given=True,
        )

    def grant_order_permissions(self, *codenames):
        permissions = Permission.objects.filter(
            content_type__app_label="core",
            codename__in=codenames,
        )
        self.manager.user_permissions.add(*permissions)

    def test_manager_page_requires_staff_and_order_or_feedback_permission(self):
        response = self.client.get(self.manager_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

        self.client.force_login(self.manager)
        response = self.client.get(self.manager_url)
        self.assertEqual(response.status_code, 403)

    def test_manager_can_view_orders_and_change_status_with_permissions(self):
        self.grant_order_permissions(
            "view_preorder",
            "change_preorder",
            "view_feedbacksubmission",
        )
        FeedbackSubmission.objects.create(
            name="Sam",
            email="sam@example.com",
            subject="Corporate order question",
            message="Can you prepare a gift set for our team?",
            consent_given=True,
        )
        self.client.force_login(self.manager)

        response = self.client.get(self.manager_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Кабинет менеджера")
        self.assertContains(response, "Alex Customer")
        self.assertContains(response, "Corporate order question")
        self.assertContains(
            response,
            reverse(self.status_url_name, args=[self.order.pk]),
        )
        self.assertEqual(response.context["order_counts"][Preorder.Status.NEW], 1)

        response = self.client.post(
            reverse(self.status_url_name, args=[self.order.pk]),
            {"status": Preorder.Status.PRODUCTION},
        )

        self.assertRedirects(response, self.manager_url)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Preorder.Status.PRODUCTION)

    def test_manager_without_change_permission_cannot_update_order_status(self):
        self.grant_order_permissions("view_preorder")
        self.client.force_login(self.manager)

        response = self.client.get(self.manager_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(
            response,
            reverse(self.status_url_name, args=[self.order.pk]),
        )

        response = self.client.post(
            reverse(self.status_url_name, args=[self.order.pk]),
            {"status": Preorder.Status.COMPLETED},
        )

        self.assertEqual(response.status_code, 403)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Preorder.Status.NEW)

    def test_change_permission_without_view_permission_cannot_update_order(self):
        self.grant_order_permissions("change_preorder")
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse(self.status_url_name, args=[self.order.pk]),
            {"status": Preorder.Status.COMPLETED},
        )

        self.assertEqual(response.status_code, 403)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Preorder.Status.NEW)

    def test_manager_status_update_rejects_invalid_values_and_get_requests(self):
        self.grant_order_permissions("view_preorder", "change_preorder")
        self.client.force_login(self.manager)
        update_url = reverse(self.status_url_name, args=[self.order.pk])

        self.assertEqual(self.client.get(update_url).status_code, 405)
        response = self.client.post(update_url, {"status": "not-a-status"})

        self.assertRedirects(response, self.manager_url)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Preorder.Status.NEW)


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
        self.assertContains(response, 'id="site-intro"')
        self.assertContains(response, 'document.documentElement.classList.add("site-intro-playing")')
        self.assertNotContains(response, "sessionStorage")
        self.assertContains(response, 'id="calculator"')
        self.assertContains(response, "Рассчитайте стоимость")
        self.assertContains(response, 'name="quantity"')
        self.assertContains(response, 'name="attachments"')
        self.assertContains(response, "Отправить предзаказ")

    def test_calculator_numeric_data_attributes_are_not_localized(self):
        response = self.client.get("/")

        self.assertContains(response, 'data-multiplier="0.55"')
        self.assertContains(response, 'data-multiplier="1.4"')

    def test_language_switch_keeps_the_current_page_and_renders_english(self):
        response = self.client.post(
            reverse("set_language"),
            {"language": "en", "next": reverse("home")},
        )

        self.assertRedirects(response, reverse("home"))
        page = self.client.get(reverse("home"))

        self.assertContains(page, 'lang="en"')
        self.assertContains(page, "Get a quote")
        self.assertContains(page, "Quick links")

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

    def test_shared_layout_renders_numbered_mobile_navigation(self):
        response = self.client.get("/")

        self.assertContains(response, 'id="navigation"')
        self.assertContains(response, 'class="mobile-menu-close"')
        self.assertContains(response, 'class="menu-backdrop"')
        self.assertContains(response, 'class="mobile-menu-number">01</span>')
        self.assertContains(response, 'class="mobile-menu-number">10</span>')
        self.assertContains(
            response,
            f'href="{reverse("feedback")}"><span class="mobile-menu-number">10</span><span>Обратная связь</span>',
        )

    def test_feedback_page_renders_contact_form(self):
        response = self.client.get(reverse("feedback"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<title>Обратная связь — Лукоморье</title>")
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="subject"')
        self.assertContains(response, 'name="message"')
        self.assertContains(response, 'name="consent_given"')

    def test_valid_feedback_submission_is_saved_and_redirected(self):
        response = self.client.post(
            reverse("feedback"),
            {
                "name": "Иван",
                "email": "ivan@example.com",
                "subject": "Вопрос о заказе",
                "message": "Подскажите, пожалуйста, сроки изготовления.",
                "consent_given": "on",
            },
        )

        self.assertRedirects(response, reverse("feedback"))
        submission = FeedbackSubmission.objects.get()
        self.assertEqual(submission.name, "Иван")
        self.assertEqual(submission.email, "ivan@example.com")
        self.assertEqual(submission.status, FeedbackSubmission.Status.NEW)

    def test_feedback_submission_requires_consent_and_valid_email(self):
        response = self.client.post(
            reverse("feedback"),
            {
                "name": "Иван",
                "email": "not-an-email",
                "subject": "Вопрос",
                "message": "Нужна помощь.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(FeedbackSubmission.objects.exists())
        self.assertContains(response, "Необходимо дать согласие на обработку данных.")

    def test_shared_layout_renders_floating_contact_button_group(self):
        response = self.client.get("/")

        self.assertContains(response, 'class="contact-float"')
        self.assertContains(response, 'class="contact-float-menu"')
        self.assertContains(response, 'class="contact-float-toggle"')
        self.assertContains(response, 'aria-controls="contact-float-menu"')
        self.assertContains(response, 'aria-label="Открыть способы связи"')
        self.assertContains(response, '>Связаться</span>')
        self.assertContains(response, 'WhatsApp')
        self.assertContains(response, 'href="https://max.ru/"')
        self.assertContains(response, 'aria-label="Написать в MAX"')
        self.assertContains(response, 'Позвонить')

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

    def test_authenticated_preorder_is_linked_to_the_account(self):
        user = get_user_model().objects.create_user(
            username="preorder_customer",
            email="preorder-customer@example.com",
            password="A-long-password-482!",
        )
        self.client.force_login(user)

        response = self.client.post(
            "/",
            {
                **self.configuration,
                "name": "Анна",
                "email": user.email,
                "phone": "+7 900 000-00-00",
                "address": "Москва",
                "consent_given": "on",
            },
        )

        self.assertRedirects(response, "/#calculator")
        self.assertEqual(Preorder.objects.get().user, user)

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

    def test_partnership_page_renders_directions_metrics_and_navigation(self):
        response = self.client.get(reverse("corporate"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<title>Партнёрство с Лукоморье — Лукоморье</title>")
        self.assertContains(response, "Направления сотрудничества")
        self.assertContains(response, "Франшиза")
        self.assertContains(response, "Производителям и поставщикам")
        self.assertContains(response, "Наши успехи — ваши возможности")
        self.assertContains(response, f'href="{reverse("business_clients")}">Корпоративным клиентам</a>')

    def test_business_clients_page_renders_its_own_content(self):
        response = self.client.get(reverse("business_clients"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<title>Корпоративным клиентам — Лукоморье</title>")
        self.assertContains(response, "Индивидуальные решения")
        self.assertContains(response, "Взаимодействие")
        self.assertContains(response, "Калькулятор заказа")

    def test_delivery_page_renders_methods_pickup_and_useful_information(self):
        response = self.client.get(reverse("delivery"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<title>Доставка и самовывоз — Лукоморье</title>")
        self.assertContains(response, "По Москве")
        self.assertContains(response, "По России")
        self.assertContains(response, "Упаковка")
        self.assertContains(response, "Стоимость доставки")
        self.assertContains(response, "Самовывоз")
        self.assertContains(response, "Полезная информация")
        self.assertContains(response, f'href="{reverse("delivery")}"><span class="mobile-menu-number">05</span>')

    def test_packaging_page_renders_packaging_cards_and_links(self):
        response = self.client.get(reverse("packaging"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<title>Варианты упаковки — Лукоморье</title>")
        self.assertContains(response, "Варианты упаковки")
        self.assertContains(response, "Основные варианты упаковки")
        self.assertContains(response, "Коробка с окном")
        self.assertContains(response, f'href="{reverse("packaging")}"><span class="mobile-menu-number">04</span>')

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
