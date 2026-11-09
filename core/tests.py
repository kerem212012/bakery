from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import Permission
from django import forms
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from catalog.models import Category, Product, ProductFilterOption
from .calculator import calculate_quote
from .models import (
    CalculatorSettings,
    FeedbackSubmission,
    HomeHeroSlide,
    Preorder,
    SiteContentBlock,
    SitePageContent,
    SitePageSection,
)


class SiteContentDjangoAdminTests(TestCase):
    def test_site_content_models_are_editable_in_django_admin(self):
        admin_user = get_user_model().objects.create_superuser(
            username="site_content_admin",
            email="site-content-admin@example.com",
            password="test-password",
        )
        page_content = SitePageContent.objects.create(
            page=SitePageContent.Page.ABOUT,
            title="Original title",
        )
        hero_slide = HomeHeroSlide.objects.create(title="Home banner")
        content_block = SiteContentBlock.objects.create(
            page=SiteContentBlock.Page.ABOUT,
            title="About block",
        )
        self.client.force_login(admin_user)

        model_objects = (
            ("core_sitepagecontent", page_content),
            ("core_homeheroslide", hero_slide),
            ("core_sitecontentblock", content_block),
        )
        for model_name, instance in model_objects:
            with self.subTest(model=model_name):
                changelist_url = reverse(f"admin:{model_name}_changelist")
                change_url = reverse(
                    f"admin:{model_name}_change",
                    args=(instance.pk,),
                )
                self.assertEqual(self.client.get(changelist_url).status_code, 200)
                self.assertEqual(self.client.get(change_url).status_code, 200)

        response = self.client.post(
            reverse(
                "admin:core_sitepagecontent_change",
                args=(page_content.pk,),
            ),
            {
                "page": SitePageContent.Page.ABOUT,
                "eyebrow": "",
                "eyebrow_en": "",
                "title": "Updated title",
                "title_en": "",
                "subtitle": "",
                "subtitle_en": "",
                "description": "",
                "description_en": "",
                "button_text": "",
                "button_text_en": "",
                "button_url": "",
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 302)
        page_content.refresh_from_db()
        self.assertEqual(page_content.title, "Updated title")


class AdminDashboardTests(TestCase):
    def setUp(self):
        self.url = reverse("admin_dashboard")

    def test_dashboard_requires_staff_access(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])
        self.assertNotIn("/admin/login/", response["Location"])

        customer = get_user_model().objects.create_user(
            username="dashboard_customer",
            password="Customer-password-482!",
        )
        self.client.force_login(customer)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])
        self.assertNotIn("/admin/login/", response["Location"])

    def test_staff_without_permissions_is_redirected_to_manager_workspace(self):
        staff_user = get_user_model().objects.create_user(
            username="basic_staff",
            is_staff=True,
        )
        self.client.force_login(staff_user)

        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            reverse("manager_dashboard"),
            fetch_redirect_response=False,
        )
        manager_response = self.client.get(reverse("manager_dashboard"))
        self.assertEqual(manager_response.status_code, 200)
        self.assertContains(manager_response, "У вашей учётной записи пока нет доступа")

    def test_site_content_editor_redirects_to_site_login(self):
        response = self.client.get(reverse("site_content_manager"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])
        self.assertIn(
            reverse("site_content_manager"),
            response["Location"],
        )
        self.assertNotIn("/admin/login/", response["Location"])

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
        self.assertContains(response, reverse("calculator_settings"))
        self.assertContains(response, "Настроить калькулятор")
        self.assertContains(response, "Редактировать контент страниц")
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

    def test_calculator_floating_button_is_hidden_on_admin_and_manager_pages(self):
        admin_user = get_user_model().objects.create_superuser(
            username="floating_calculator_admin",
            email="floating-calculator-admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)

        for url in (
            reverse("admin_dashboard"),
            reverse("admin_section", args=("products",)),
            reverse("site_content_manager"),
            reverse("manager_dashboard"),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, "calculator-float-toggle")
                self.assertNotContains(response, 'class="contact-float"')

        public_response = self.client.get(reverse("home"))
        self.assertContains(public_response, "calculator-float-toggle")
        self.assertContains(public_response, 'class="contact-float"')

    def test_site_content_editor_requires_site_content_permissions(self):
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
        self.assertContains(response, "Редактировать страницы сайта")
        self.assertContains(response, "Выберите страницу")
        self.assertContains(response, 'option value="catalog" selected')
        self.assertNotContains(response, 'option value="home" selected')

    def test_staff_with_site_content_permissions_can_edit_page_content(self):
        manager = get_user_model().objects.create_user(
            username="permitted_content_manager",
            password="test-password",
            is_staff=True,
        )
        page_content = SitePageContent.objects.create(
            page=SitePageContent.Page.ABOUT,
            title="Before edit",
        )
        permissions = Permission.objects.filter(
            content_type__app_label="core",
            codename__in=(
                "add_sitepagecontent",
                "change_sitepagecontent",
                "add_homeheroslide",
                "change_homeheroslide",
                "add_sitecontentblock",
                "change_sitecontentblock",
                "add_sitepagesection",
                "change_sitepagesection",
            ),
        )
        manager.user_permissions.add(*permissions)
        self.client.force_login(manager)

        dashboard_response = self.client.get(reverse("admin_dashboard"))
        editor_response = self.client.get(
            reverse("site_content_manager"),
            {"page": SitePageContent.Page.ABOUT},
        )

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, "Редактировать контент страниц")
        self.assertEqual(editor_response.status_code, 200)
        self.assertContains(editor_response, "Редактировать страницы сайта")

        save_response = self.client.post(
            reverse("site_content_manager"),
            {
                "action": "save_page_content",
                "page": SitePageContent.Page.ABOUT,
                "eyebrow": "",
                "eyebrow_en": "",
                "title": "After edit",
                "title_en": "",
                "subtitle": "",
                "subtitle_en": "",
                "description": "",
                "description_en": "",
                "button_text": "",
                "button_text_en": "",
                "button_url": "",
            },
        )

        self.assertRedirects(
            save_response,
            f"{reverse('site_content_manager')}?page=about",
        )
        page_content.refresh_from_db()
        self.assertEqual(page_content.title, "After edit")

    def test_selecting_page_loads_its_existing_content_for_editing(self):
        admin_user = get_user_model().objects.create_superuser(
            username="existing_content_admin",
            email="existing-content-admin@example.com",
            password="test-password",
        )
        page_content = SitePageContent.objects.create(
            page=SitePageContent.Page.CATALOG,
            title="Catalog content to edit",
            description="Saved catalog description",
        )
        self.client.force_login(admin_user)

        response = self.client.get(
            reverse("site_content_manager"),
            {"page": SiteContentBlock.Page.CATALOG},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_form"].instance, page_content)
        self.assertContains(response, "Catalog content to edit")
        self.assertContains(response, "Saved catalog description")

    def test_selecting_page_with_multiple_blocks_shows_page_specific_choices(self):
        admin_user = get_user_model().objects.create_superuser(
            username="multiple_content_admin",
            email="multiple-content-admin@example.com",
            password="test-password",
        )
        SiteContentBlock.objects.create(
            page=SiteContentBlock.Page.ABOUT,
            title="First about block",
        )
        SiteContentBlock.objects.create(
            page=SiteContentBlock.Page.ABOUT,
            title="Second about block",
        )
        SiteContentBlock.objects.create(
            page=SiteContentBlock.Page.CATALOG,
            title="Catalog block",
        )
        self.client.force_login(admin_user)

        response = self.client.get(
            reverse("site_content_manager"),
            {"page": SiteContentBlock.Page.ABOUT},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["form"])
        self.assertNotIn("site_blocks", response.context)
        self.assertNotContains(response, "Additional page content")
        self.assertNotContains(response, "Дополнительный контент страницы")
        self.assertContains(response, 'option value="about" selected')

    def test_page_picker_switches_from_editing_one_page_to_another(self):
        admin_user = get_user_model().objects.create_superuser(
            username="switch_content_admin",
            email="switch-content-admin@example.com",
            password="test-password",
        )
        about_content = SitePageContent.objects.create(
            page=SitePageContent.Page.ABOUT,
            title="About page content",
        )
        catalog_content = SitePageContent.objects.create(
            page=SitePageContent.Page.CATALOG,
            title="Catalog page content",
        )
        self.client.force_login(admin_user)

        about_response = self.client.get(
            reverse("site_content_manager"),
            {"page": SitePageContent.Page.ABOUT},
        )
        catalog_response = self.client.get(
            reverse("site_content_manager"),
            {"page": SitePageContent.Page.CATALOG},
        )

        self.assertEqual(about_response.context["page_form"].instance, about_content)
        self.assertEqual(catalog_response.context["page_form"].instance, catalog_content)
        self.assertContains(about_response, "About page content")
        self.assertContains(catalog_response, "Catalog page content")
        self.assertNotContains(catalog_response, "About page content")

    def test_page_picker_loads_page_specific_editor_fields(self):
        admin_user = get_user_model().objects.create_superuser(
            username="page_content_fields_admin",
            email="page-content-fields-admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)

        about_response = self.client.get(
            reverse("site_content_manager"),
            {"page": SitePageContent.Page.ABOUT},
        )
        faq_response = self.client.get(
            reverse("site_content_manager"),
            {"page": SitePageContent.Page.FAQ},
        )
        home_response = self.client.get(
            reverse("site_content_manager"),
            {"page": SiteContentBlock.Page.HOME},
        )

        self.assertNotIn("button_text", about_response.context["page_form"].fields)
        self.assertNotIn("button_url", about_response.context["page_form"].fields)
        self.assertIn("image", about_response.context["page_form"].fields)
        self.assertNotIn("button_text", faq_response.context["page_form"].fields)
        self.assertNotIn("button_url", faq_response.context["page_form"].fields)
        self.assertEqual(home_response.context["slide_formset"].total_form_count(), 4)
        home_slide_form = home_response.context["slide_formset"].forms[1]
        self.assertEqual(
            set(home_slide_form.fields),
            {"image", "display_order", "is_active", "id"},
        )
        self.assertEqual(home_slide_form["display_order"].value(), 1)
        self.assertTrue(home_slide_form["is_active"].value())
        self.assertFalse(
            home_response.context["slide_formset"].forms[3]["is_active"].value()
        )
        self.assertContains(home_response, 'id="add-home-slide"')

    def test_page_content_button_fields_are_hidden_on_every_page(self):
        admin_user = get_user_model().objects.create_superuser(
            username="all_page_button_fields_admin",
            email="all-page-button-fields@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)

        pages = (
            SitePageContent.Page.ABOUT,
            SitePageContent.Page.BUSINESS_CLIENTS,
            SitePageContent.Page.PARTNERSHIP,
            SitePageContent.Page.CONTACTS,
            SitePageContent.Page.DELIVERY,
            SitePageContent.Page.FAQ,
            SitePageContent.Page.FEEDBACK,
            SitePageContent.Page.PACKAGING,
            SitePageContent.Page.CATALOG,
            SitePageContent.Page.CATEGORIES,
        )
        for page in pages:
            with self.subTest(page=page):
                response = self.client.get(
                    reverse("site_content_manager"),
                    {"page": page},
                )
                self.assertEqual(response.status_code, 200)
                self.assertFalse(
                    {"button_text", "button_text_en", "button_url"}
                    & set(response.context["page_form"].fields)
                )

    def test_page_content_button_edits_are_rendered_on_every_static_page(self):
        pages = (
            (SitePageContent.Page.ABOUT, "about"),
            (SitePageContent.Page.BUSINESS_CLIENTS, "business_clients"),
            (SitePageContent.Page.PARTNERSHIP, "corporate"),
            (SitePageContent.Page.CONTACTS, "contacts"),
            (SitePageContent.Page.DELIVERY, "delivery"),
            (SitePageContent.Page.FAQ, "faq"),
            (SitePageContent.Page.FEEDBACK, "feedback"),
            (SitePageContent.Page.PACKAGING, "packaging"),
            (SitePageContent.Page.CATALOG, "catalog:category_list"),
            (SitePageContent.Page.CATEGORIES, "catalog:categories"),
        )
        for page, route_name in pages:
            with self.subTest(page=page):
                SitePageContent.objects.create(
                    page=page,
                    title="Page title",
                    title_en="Page title",
                    button_text="Связаться",
                    button_text_en="Contact us",
                    button_url="/custom-action/",
                )

                response = self.client.get(reverse(route_name))

                self.assertContains(response, 'href="/custom-action/"')
                self.assertContains(response, "Связаться")

    def test_page_picker_does_not_render_section_editor(self):
        admin_user = get_user_model().objects.create_superuser(
            username="all_page_sections_admin",
            email="all-page-sections-admin@example.com",
            password="test-pass-123",
        )
        self.client.force_login(admin_user)
        pages = SiteContentBlock.Page.values

        for page in pages:
            with self.subTest(page=page):
                response = self.client.get(
                    reverse("site_content_manager"),
                    {"page": page},
                )
                self.assertEqual(response.status_code, 200)
                self.assertNotIn("section_formset", response.context)
                self.assertNotContains(response, 'name="action" value="save_page_sections"')

    def test_site_content_page_picker_hides_category_and_product_pages(self):
        admin_user = get_user_model().objects.create_superuser(
            username="page_picker_options_admin",
            email="page-picker-options-admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)

        response = self.client.get(
            reverse("site_content_manager"),
            {"page": SiteContentBlock.Page.CATALOG},
        )

        choices = response.context["page_selector"].fields["page"].choices
        choice_values = {choice[0] for choice in choices}
        self.assertNotIn(SiteContentBlock.Page.CATEGORIES, choice_values)
        self.assertNotIn(SiteContentBlock.Page.CATEGORY, choice_values)
        self.assertNotIn(SiteContentBlock.Page.PRODUCT, choice_values)
        self.assertNotContains(response, '<option value="categories"')
        self.assertNotContains(response, '<option value="category"')
        self.assertNotContains(response, '<option value="product"')

    def test_home_about_form_is_only_available_for_home_page(self):
        admin_user = get_user_model().objects.create_superuser(
            username="home_about_form_admin",
            email="home-about-form-admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)

        home_response = self.client.get(
            reverse("site_content_manager"),
            {"page": SiteContentBlock.Page.HOME},
        )
        about_response = self.client.get(
            reverse("site_content_manager"),
            {"page": SiteContentBlock.Page.ABOUT},
        )

        self.assertIsNotNone(home_response.context["home_about_form"])
        self.assertFalse(
            {"value", "value_en", "url"}
            & set(home_response.context["home_about_form"].fields)
        )
        self.assertContains(home_response, "Главная страница — раздел")
        self.assertIsNone(about_response.context["home_about_form"])
        self.assertNotContains(about_response, "Главная страница — раздел")

    def test_about_story_form_is_only_available_for_about_page(self):
        admin_user = get_user_model().objects.create_superuser(
            username="about_story_form_admin",
            email="about-story-form-admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)

        about_response = self.client.get(
            reverse("site_content_manager"),
            {"page": SiteContentBlock.Page.ABOUT},
        )
        home_response = self.client.get(
            reverse("site_content_manager"),
            {"page": SiteContentBlock.Page.HOME},
        )

        self.assertIsNotNone(about_response.context["about_story_form"])
        self.assertContains(about_response, "Страница «О нас» — «Наша история»")
        self.assertIsNone(home_response.context["about_story_form"])
        self.assertNotContains(home_response, "Страница «О нас» — «Наша история»")

    def test_about_story_form_saves_and_updates_public_page(self):
        admin_user = get_user_model().objects.create_superuser(
            username="about_story_saver",
            email="about-story-saver@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse("site_content_manager"),
            {
                "action": "save_about_story",
                "page": SitePageSection.Page.ABOUT,
                "section_eyebrow": "Семейная история",
                "section_eyebrow_en": "A family story",
                "section_title": "Новая история",
                "section_title_en": "A new story",
                "description": "Обновлённый рассказ о компании.",
                "description_en": "An updated story about the company.",
                "image_alt": "Мастерская",
                "image_alt_en": "Workshop",
                "is_active": "on",
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('site_content_manager')}?page=about",
        )
        story = SitePageSection.objects.get(
            page=SitePageSection.Page.ABOUT,
            group="story",
        )
        self.assertEqual(story.section_title, "Новая история")
        self.assertEqual(story.description_en, "An updated story about the company.")

        about_response = self.client.get(reverse("about"))
        self.assertContains(about_response, "Новая история")
        self.assertContains(about_response, "Обновлённый рассказ о компании.")

    def test_about_promises_form_updates_principle_cards(self):
        admin_user = get_user_model().objects.create_superuser(
            username="about_promises_saver",
            email="about-promises-saver@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)
        editor_response = self.client.get(
            reverse("site_content_manager"),
            {"page": SitePageSection.Page.ABOUT},
        )
        formset = editor_response.context["about_promises_formset"]
        self.assertEqual(
            len(formset.forms),
            SitePageSection.objects.filter(
                page=SitePageSection.Page.ABOUT,
                group="promises",
            ).count(),
        )
        self.assertEqual(
            [form.initial["display_order"] for form in formset.forms],
            list(range(1, len(formset.forms) + 1)),
        )
        post_data = {
            "page": SitePageSection.Page.ABOUT,
            "action": "save_about_promises",
            "promises-TOTAL_FORMS": str(len(formset.forms)),
            "promises-INITIAL_FORMS": str(formset.initial_form_count()),
            "promises-MIN_NUM_FORMS": "0",
            "promises-MAX_NUM_FORMS": "1000",
        }
        for index, form in enumerate(formset.forms):
            if form.instance.pk:
                post_data[f"promises-{index}-id"] = str(form.instance.pk)
                post_data[f"promises-{index}-title"] = form.instance.title
                post_data[f"promises-{index}-title_en"] = form.instance.title_en
                post_data[f"promises-{index}-description"] = form.instance.description
                post_data[f"promises-{index}-description_en"] = form.instance.description_en
                post_data[f"promises-{index}-display_order"] = str(
                    form.instance.display_order + 1
                )
                if form.instance.is_active:
                    post_data[f"promises-{index}-is_active"] = "on"
        post_data["promises-0-title"] = "Новый принцип"

        response = self.client.post(reverse("site_content_manager"), post_data)

        self.assertRedirects(
            response,
            f"{reverse('site_content_manager')}?page=about",
        )
        promise = SitePageSection.objects.get(
            page=SitePageSection.Page.ABOUT,
            group="promises",
            display_order=0,
        )
        self.assertEqual(promise.title, "Новый принцип")
        about_response = self.client.get(reverse("about"))
        self.assertContains(about_response, "Новый принцип")

    def test_about_values_form_updates_section_heading_and_value_cards(self):
        admin_user = get_user_model().objects.create_superuser(
            username="about_values_saver",
            email="about-values-saver@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)
        editor_response = self.client.get(
            reverse("site_content_manager"),
            {"page": SitePageSection.Page.ABOUT},
        )
        formset = editor_response.context["about_values_formset"]
        self.assertEqual(
            len(formset.forms),
            SitePageSection.objects.filter(
                page=SitePageSection.Page.ABOUT,
                group="values",
            ).count(),
        )
        self.assertEqual(
            [form.initial["display_order"] for form in formset.forms],
            list(range(1, len(formset.forms) + 1)),
        )
        post_data = {
            "page": SitePageSection.Page.ABOUT,
            "action": "save_about_values",
            "values-TOTAL_FORMS": str(len(formset.forms)),
            "values-INITIAL_FORMS": str(formset.initial_form_count()),
            "values-MIN_NUM_FORMS": "0",
            "values-MAX_NUM_FORMS": "1000",
        }
        heading_form = editor_response.context["about_values_heading_form"]
        for field_name in heading_form.fields:
            post_data[f"values-heading-{field_name}"] = heading_form.initial.get(
                field_name, ""
            )
        for index, form in enumerate(formset.forms):
            if form.instance.pk:
                post_data[f"values-{index}-id"] = str(form.instance.pk)
                for field_name in (
                    "title",
                    "title_en",
                    "description",
                    "description_en",
                    "image_alt",
                    "image_alt_en",
                    "display_order",
                ):
                    post_data[f"values-{index}-{field_name}"] = str(
                        (
                            form.instance.display_order + 1
                            if field_name == "display_order"
                            else getattr(form.instance, field_name)
                        )
                    )
                if form.instance.is_active:
                    post_data[f"values-{index}-is_active"] = "on"
        post_data["values-heading-section_title"] = "Новая заголовочная часть"
        post_data["values-heading-section_title_en"] = "New values heading"
        post_data["values-0-title"] = "Новая ценность"

        response = self.client.post(reverse("site_content_manager"), post_data)

        self.assertRedirects(
            response,
            f"{reverse('site_content_manager')}?page=about",
        )
        value_card = SitePageSection.objects.get(
            page=SitePageSection.Page.ABOUT,
            group="values",
            display_order=0,
        )
        self.assertEqual(value_card.section_title, "Новая заголовочная часть")
        self.assertEqual(value_card.section_title_en, "New values heading")
        self.assertEqual(value_card.title, "Новая ценность")
        about_response = self.client.get(reverse("about"))
        self.assertContains(about_response, "Новая заголовочная часть")
        self.assertContains(about_response, "Новая ценность")

    def test_contact_details_form_is_only_available_under_all_pages(self):
        admin_user = get_user_model().objects.create_superuser(
            username="contact_details_form_admin",
            email="contact-details-form-admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)

        contacts_response = self.client.get(
            reverse("site_content_manager"),
            {"page": SiteContentBlock.Page.CONTACTS},
        )
        all_pages_response = self.client.get(
            reverse("site_content_manager"),
            {"page": SiteContentBlock.Page.ALL},
        )

        self.assertIsNone(contacts_response.context["contact_details_form"])
        self.assertIsNotNone(contacts_response.context["contact_requisites_form"])
        self.assertContains(contacts_response, "Контакты — реквизиты")
        self.assertIsNotNone(all_pages_response.context["contact_details_form"])
        self.assertIsNone(all_pages_response.context["contact_requisites_form"])
        self.assertContains(all_pages_response, "Все страницы — контактные данные")
        self.assertEqual(
            len(all_pages_response.context["contact_details_form"].fields),
            15,
        )
        self.assertIsNotNone(
            all_pages_response.context["business_clients_contact_form"]
        )
        self.assertEqual(
            len(all_pages_response.context["business_clients_contact_form"].fields),
            15,
        )
        self.assertContains(
            all_pages_response,
            'name="action" value="save_contact_details"',
            count=1,
        )
        self.assertContains(
            all_pages_response,
            'name="action" value="save_business_clients_contacts"',
            count=1,
        )

    def test_contact_details_form_updates_public_phone_email_and_address(self):
        admin_user = get_user_model().objects.create_superuser(
            username="contact_details_saver",
            email="contact-details-saver@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)

        editor_response = self.client.get(
            reverse("site_content_manager"),
            {"page": SiteContentBlock.Page.ALL},
        )
        form = editor_response.context["contact_details_form"]
        post_data = {
            "page": SiteContentBlock.Page.ALL,
            "action": "save_contact_details",
        }
        post_data.update(
            {
                field_name: form.initial[field_name]
                for field_name in form.fields
            }
        )
        post_data["phone_value"] = "+7 999 111-22-33"
        post_data["phone_url"] = "tel:+79991112233"
        post_data["email_value"] = "new@example.com"
        post_data["email_url"] = "mailto:new@example.com"
        post_data["address_value"] = "New office address"

        response = self.client.post(reverse("site_content_manager"), post_data)

        self.assertRedirects(
            response,
            f"{reverse('site_content_manager')}?page=all",
        )
        contacts = list(
            SitePageSection.objects.filter(
                page=SitePageSection.Page.CONTACTS,
                group="details",
            ).order_by("display_order", "pk")
        )
        self.assertEqual(contacts[0].value, "+7 999 111-22-33")
        self.assertEqual(contacts[0].url, "tel:+79991112233")
        self.assertEqual(contacts[1].value, "new@example.com")
        self.assertEqual(contacts[1].url, "mailto:new@example.com")
        self.assertEqual(contacts[2].value, "New office address")

        public_response = self.client.get(reverse("contacts"))
        self.assertContains(public_response, "+7 999 111-22-33")
        self.assertContains(public_response, 'href="mailto:new@example.com"')
        self.assertContains(public_response, "New office address")

    def test_contact_requisites_form_updates_contacts_page(self):
        admin_user = get_user_model().objects.create_superuser(
            username="contact_requisites_saver",
            email="contact-requisites-saver@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)
        editor_url = reverse("site_content_manager")
        editor_response = self.client.get(
            editor_url,
            {"page": SitePageSection.Page.CONTACTS},
        )
        form = editor_response.context["contact_requisites_form"]
        post_data = {
            "page": SitePageSection.Page.CONTACTS,
            "action": "save_contact_requisites",
            **{
                f"{form.prefix}-{field_name}": form[field_name].value() or ""
                for field_name in form.fields
            },
        }
        post_data.update(
            {
                f"{form.prefix}-title": "Новые реквизиты",
                f"{form.prefix}-title_en": "New company details",
                f"{form.prefix}-description": "Обновлённое описание реквизитов.",
                f"{form.prefix}-description_en": "Updated company details.",
                f"{form.prefix}-value": "Запросить новые реквизиты",
                f"{form.prefix}-value_en": "Request new company details",
                f"{form.prefix}-url": "mailto:accounts@example.com",
                f"{form.prefix}-is_active": "on",
            }
        )

        response = self.client.post(editor_url, post_data)

        self.assertRedirects(
            response,
            f"{editor_url}?page={SitePageSection.Page.CONTACTS}",
        )
        requisites = SitePageSection.objects.get(
            page=SitePageSection.Page.CONTACTS,
            group="requisites",
            display_order=0,
        )
        self.assertEqual(requisites.title, "Новые реквизиты")
        self.assertEqual(requisites.description, "Обновлённое описание реквизитов.")
        self.assertEqual(requisites.value, "Запросить новые реквизиты")
        self.assertEqual(requisites.url, "mailto:accounts@example.com")

        public_response = self.client.get(reverse("contacts"))
        self.assertContains(public_response, "Новые реквизиты")
        self.assertContains(public_response, "Обновлённое описание реквизитов.")
        self.assertContains(public_response, "Запросить новые реквизиты")
        self.assertContains(public_response, 'href="mailto:accounts@example.com"')

    def test_delivery_sections_are_editable_and_rendered(self):
        admin_user = get_user_model().objects.create_superuser(
            username="delivery_sections_admin",
            email="delivery-sections-admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)
        editor_url = reverse("site_content_manager")
        page = SitePageSection.Page.DELIVERY
        editor_response = self.client.get(editor_url, {"page": page})
        self.assertEqual(editor_response.status_code, 200)

        methods_heading_form = editor_response.context[
            "delivery_methods_heading_form"
        ]
        methods_formset = editor_response.context["delivery_methods_formset"]
        pickup_heading_form = editor_response.context[
            "delivery_pickup_heading_form"
        ]
        pickup_formset = editor_response.context["delivery_pickup_formset"]
        help_heading_form = editor_response.context["delivery_help_heading_form"]
        help_formset = editor_response.context["delivery_help_formset"]
        self.assertIsNotNone(methods_formset)
        self.assertIsNotNone(pickup_formset)
        self.assertIsNotNone(help_formset)
        self.assertContains(editor_response, "Доставка — способы доставки")
        self.assertContains(editor_response, "Доставка — самовывоз")
        self.assertContains(editor_response, "Доставка — полезная информация")

        def formset_data(formset):
            data = {
                f"{formset.prefix}-TOTAL_FORMS": str(len(formset.forms)),
                f"{formset.prefix}-INITIAL_FORMS": str(formset.initial_form_count()),
                f"{formset.prefix}-MIN_NUM_FORMS": "0",
                f"{formset.prefix}-MAX_NUM_FORMS": "1000",
            }
            for form in formset.forms:
                for field_name in form.fields:
                    if field_name == "image":
                        continue
                    name = f"{form.prefix}-{field_name}"
                    if field_name == "id":
                        data[name] = str(form.instance.pk)
                    else:
                        data[name] = form[field_name].value() or ""
            return data

        def form_data(form):
            return {
                f"{form.prefix}-{field_name}": form[field_name].value() or ""
                for field_name in form.fields
            }

        methods_data = {
            "page": page,
            "action": "save_delivery_methods",
            **formset_data(methods_formset),
            **form_data(methods_heading_form),
            "delivery-methods-0-title": "Новая доставка",
            "delivery-methods-0-title_en": "New delivery",
            "delivery-methods-0-description": "Описание новой доставки.",
            "delivery-methods-0-description_en": "Description of new delivery.",
            "delivery-methods-0-value": "Новый срок доставки",
            "delivery-methods-0-value_en": "New delivery timeframe",
            "delivery-methods-heading-section_title": "Новые способы доставки",
            "delivery-methods-heading-section_title_en": "New delivery methods",
            "delivery-methods-heading-section_description": "Обновлённое описание доставки.",
            "delivery-methods-heading-section_description_en": "Updated delivery introduction.",
        }
        response = self.client.post(editor_url, methods_data)
        self.assertRedirects(response, f"{editor_url}?page={page}")

        pickup_data = {
            "page": page,
            "action": "save_delivery_pickup",
            **formset_data(pickup_formset),
            **form_data(pickup_heading_form),
            "delivery-pickup-0-title": "Новый адрес",
            "delivery-pickup-0-title_en": "New address",
            "delivery-pickup-0-description": "Новый адрес студии.",
            "delivery-pickup-0-description_en": "New studio address.",
            "delivery-pickup-heading-section_title": "Новый самовывоз",
            "delivery-pickup-heading-section_title_en": "New pickup",
            "delivery-pickup-heading-section_description": "Обновлённые условия самовывоза.",
            "delivery-pickup-heading-section_description_en": "Updated pickup details.",
            "delivery-pickup-heading-value": "Открыть новый маршрут",
            "delivery-pickup-heading-value_en": "Open new route",
            "delivery-pickup-heading-url": "https://maps.example/pickup",
        }
        response = self.client.post(editor_url, pickup_data)
        self.assertRedirects(response, f"{editor_url}?page={page}")

        help_data = {
            "page": page,
            "action": "save_delivery_help",
            **formset_data(help_formset),
            **form_data(help_heading_form),
            "delivery-help-0-title": "Новая стоимость доставки",
            "delivery-help-0-title_en": "New delivery cost",
            "delivery-help-0-description": "Описание новой стоимости доставки.",
            "delivery-help-0-description_en": "Description of new delivery cost.",
            "delivery-help-heading-section_title": "Новая полезная информация",
            "delivery-help-heading-section_title_en": "New useful information",
        }
        response = self.client.post(editor_url, help_data)
        self.assertRedirects(response, f"{editor_url}?page={page}")

        methods = SitePageSection.objects.get(
            page=page,
            group="methods",
            display_order=0,
        )
        pickup_heading = SitePageSection.objects.get(
            page=page,
            group="pickup",
            display_order=0,
        )
        pickup_address = SitePageSection.objects.get(
            page=page,
            group="pickup",
            display_order=1,
        )
        delivery_cost = SitePageSection.objects.get(
            page=page,
            group="notes",
            display_order=0,
        )
        self.assertEqual(methods.title, "Новая доставка")
        self.assertEqual(methods.section_title, "Новые способы доставки")
        self.assertEqual(pickup_heading.section_title, "Новый самовывоз")
        self.assertEqual(pickup_heading.url, "https://maps.example/pickup")
        self.assertEqual(pickup_address.description, "Новый адрес студии.")
        self.assertEqual(delivery_cost.title, "Новая стоимость доставки")
        self.assertEqual(delivery_cost.section_title, "Новая полезная информация")

        public_response = self.client.get(reverse("delivery"))
        for rendered_text in (
            "Новые способы доставки",
            "Обновлённое описание доставки.",
            "Новая доставка",
            "Новый срок доставки",
            "Новый самовывоз",
            "Обновлённые условия самовывоза.",
            "Новый адрес",
            "Новый адрес студии.",
            "Новая полезная информация",
            "Новая стоимость доставки",
            "Описание новой стоимости доставки.",
        ):
            with self.subTest(text=rendered_text):
                self.assertContains(public_response, rendered_text)
        self.assertContains(public_response, 'href="https://maps.example/pickup"')

    def test_faq_questions_can_be_added_edited_ordered_and_deleted(self):
        admin_user = get_user_model().objects.create_superuser(
            username="faq_questions_admin",
            email="faq-questions-admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)
        editor_url = reverse("site_content_manager")
        page = SitePageSection.Page.FAQ
        editor_response = self.client.get(editor_url, {"page": page})
        formset = editor_response.context["faq_questions_formset"]
        self.assertIsNotNone(formset)
        self.assertEqual(formset.extra_forms[0]["display_order"].value(), formset.initial_form_count() + 1)
        self.assertContains(editor_response, "Частые вопросы — вопросы и ответы")
        self.assertContains(editor_response, "Добавить вопрос")

        post_data = {
            "page": page,
            "action": "save_faq_questions",
            f"{formset.prefix}-TOTAL_FORMS": str(formset.total_form_count()),
            f"{formset.prefix}-INITIAL_FORMS": str(formset.initial_form_count()),
            f"{formset.prefix}-MIN_NUM_FORMS": "0",
            f"{formset.prefix}-MAX_NUM_FORMS": "1000",
        }
        for index, question_form in enumerate(formset.forms):
            for field_name in question_form.fields:
                field_key = f"{question_form.prefix}-{field_name}"
                if field_name == "id":
                    post_data[field_key] = str(question_form.instance.pk or "")
                elif field_name == "DELETE":
                    if index == 1:
                        post_data[field_key] = "on"
                elif field_name == "is_active":
                    if question_form[field_name].value():
                        post_data[field_key] = "on"
                else:
                    post_data[field_key] = question_form[field_name].value() or ""

        post_data.update(
            {
                f"{formset.prefix}-0-title": "Обновлённый вопрос",
                f"{formset.prefix}-0-title_en": "Updated question",
                f"{formset.prefix}-0-description": "Обновлённый ответ.",
                f"{formset.prefix}-0-description_en": "Updated answer.",
                f"{formset.prefix}-0-display_order": "8",
                f"{formset.prefix}-{formset.initial_form_count()}-title": "Новый вопрос",
                f"{formset.prefix}-{formset.initial_form_count()}-title_en": "New question",
                f"{formset.prefix}-{formset.initial_form_count()}-description": "Новый ответ.",
                f"{formset.prefix}-{formset.initial_form_count()}-description_en": "New answer.",
                f"{formset.prefix}-{formset.initial_form_count()}-display_order": "9",
                f"{formset.prefix}-{formset.initial_form_count()}-is_active": "on",
            }
        )

        response = self.client.post(editor_url, post_data)

        self.assertRedirects(response, f"{editor_url}?page={page}")
        questions = SitePageSection.objects.filter(
            page=page,
            group="questions",
        )
        self.assertEqual(
            questions.filter(title="Обновлённый вопрос").get().display_order,
            7,
        )
        self.assertTrue(questions.filter(title="Новый вопрос").exists())
        self.assertFalse(questions.filter(title="Можно ли нанести логотип или индивидуальный дизайн?").exists())

        public_response = self.client.get(reverse("faq"))
        self.assertContains(public_response, "Обновлённый вопрос")
        self.assertContains(public_response, "Обновлённый ответ.")
        self.assertContains(public_response, "Новый вопрос")
        self.assertContains(public_response, "Новый ответ.")
        self.assertNotContains(
            public_response,
            "Можно ли нанести логотип или индивидуальный дизайн?",
        )

    def test_packaging_sections_can_be_edited_from_site_content_manager(self):
        admin_user = get_user_model().objects.create_superuser(
            username="packaging_sections_admin",
            email="packaging-sections-admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)
        editor_url = reverse("site_content_manager")
        page = SitePageSection.Page.PACKAGING
        editor_response = self.client.get(editor_url, {"page": page})
        options_formset = editor_response.context["packaging_options_formset"]
        options_heading_form = editor_response.context[
            "packaging_options_heading_form"
        ]
        extras_formset = editor_response.context["packaging_extras_formset"]
        extras_heading_form = editor_response.context[
            "packaging_extras_heading_form"
        ]
        self.assertIsNotNone(options_formset)
        self.assertIsNotNone(extras_formset)
        self.assertContains(editor_response, "Упаковка — основные варианты")
        self.assertContains(editor_response, "Упаковка — дополнительные варианты")

        def formset_data(formset):
            data = {
                f"{formset.prefix}-TOTAL_FORMS": str(len(formset.forms)),
                f"{formset.prefix}-INITIAL_FORMS": str(formset.initial_form_count()),
                f"{formset.prefix}-MIN_NUM_FORMS": "0",
                f"{formset.prefix}-MAX_NUM_FORMS": "1000",
            }
            for form in formset.forms:
                for field_name in form.fields:
                    if field_name == "image":
                        continue
                    name = f"{form.prefix}-{field_name}"
                    if field_name == "id":
                        data[name] = str(form.instance.pk)
                    elif field_name == "is_active":
                        if form[field_name].value():
                            data[name] = "on"
                    else:
                        data[name] = form[field_name].value() or ""
            return data

        def heading_form_data(form):
            return {
                f"{form.prefix}-{field_name}": form[field_name].value() or ""
                for field_name in form.fields
            }

        options_post = {
            "page": page,
            "action": "save_packaging_options",
            **formset_data(options_formset),
            **heading_form_data(options_heading_form),
            f"{options_formset.prefix}-0-title": "Обновлённая коробка",
            f"{options_formset.prefix}-0-title_en": "Updated box",
            f"{options_formset.prefix}-0-description": "Описание упаковки.",
            f"{options_formset.prefix}-0-description_en": "Packaging description.",
            f"{options_heading_form.prefix}-section_title": "Новая упаковка",
            f"{options_heading_form.prefix}-section_title_en": "New packaging",
        }
        response = self.client.post(editor_url, options_post)
        self.assertRedirects(response, f"{editor_url}?page={page}")

        extras_post = {
            "page": page,
            "action": "save_packaging_extras",
            **formset_data(extras_formset),
            **heading_form_data(extras_heading_form),
            f"{extras_formset.prefix}-0-title": "Новая брендированная коробка",
            f"{extras_formset.prefix}-0-title_en": "New branded box",
            f"{extras_formset.prefix}-0-description": "Описание брендирования.",
            f"{extras_formset.prefix}-0-description_en": "Branding description.",
            f"{extras_heading_form.prefix}-section_title": "Новые дополнения",
            f"{extras_heading_form.prefix}-section_title_en": "New extras",
        }
        response = self.client.post(editor_url, extras_post)
        self.assertRedirects(response, f"{editor_url}?page={page}")

        options_card = SitePageSection.objects.get(
            page=page,
            group="options",
            display_order=0,
        )
        extras_card = SitePageSection.objects.get(
            page=page,
            group="extras",
            display_order=0,
        )
        self.assertEqual(options_card.title, "Обновлённая коробка")
        self.assertEqual(options_card.section_title, "Новая упаковка")
        self.assertEqual(extras_card.title, "Новая брендированная коробка")
        self.assertEqual(extras_card.section_title, "Новые дополнения")

        public_response = self.client.get(reverse("packaging"))
        for rendered_text in (
            "Новая упаковка",
            "Обновлённая коробка",
            "Описание упаковки.",
            "Новые дополнения",
            "Новая брендированная коробка",
            "Описание брендирования.",
        ):
            with self.subTest(text=rendered_text):
                self.assertContains(public_response, rendered_text)

    def test_catalog_promo_cards_can_be_edited_from_site_content_manager(self):
        admin_user = get_user_model().objects.create_superuser(
            username="catalog_promos_admin",
            email="catalog-promos-admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)
        editor_url = reverse("site_content_manager")
        page = SitePageSection.Page.CATALOG
        editor_response = self.client.get(editor_url, {"page": page})
        formset = editor_response.context["catalog_promo_formset"]
        self.assertIsNotNone(formset)
        self.assertEqual(formset.initial_form_count(), 3)
        self.assertContains(editor_response, "Каталог — промо-карточки")
        self.assertContains(editor_response, "Добавить промо-карточку")

        post_data = {
            "page": page,
            "action": "save_catalog_promos",
            f"{formset.prefix}-TOTAL_FORMS": str(formset.total_form_count()),
            f"{formset.prefix}-INITIAL_FORMS": str(formset.initial_form_count()),
            f"{formset.prefix}-MIN_NUM_FORMS": "0",
            f"{formset.prefix}-MAX_NUM_FORMS": "1000",
        }
        for index, promo_form in enumerate(formset.forms):
            for field_name in promo_form.fields:
                field_key = f"{promo_form.prefix}-{field_name}"
                if field_name == "id":
                    post_data[field_key] = str(promo_form.instance.pk or "")
                elif field_name == "DELETE":
                    if index == 2:
                        post_data[field_key] = "on"
                elif field_name == "is_active":
                    if promo_form[field_name].value():
                        post_data[field_key] = "on"
                else:
                    post_data[field_key] = promo_form[field_name].value() or ""

        new_index = formset.initial_form_count()
        post_data.update(
            {
                f"{formset.prefix}-0-title": "Обновлённое предложение",
                f"{formset.prefix}-0-title_en": "Updated offer",
                f"{formset.prefix}-0-description": "Описание предложения.",
                f"{formset.prefix}-0-description_en": "Offer description.",
                f"{formset.prefix}-0-url": "/updated-offer/",
                f"{formset.prefix}-0-display_order": "2",
                f"{formset.prefix}-1-display_order": "1",
                f"{formset.prefix}-{new_index}-title": "Новое предложение",
                f"{formset.prefix}-{new_index}-title_en": "New offer",
                f"{formset.prefix}-{new_index}-description": "Описание новой акции.",
                f"{formset.prefix}-{new_index}-description_en": "New offer description.",
                f"{formset.prefix}-{new_index}-url": "/new-offer/",
                f"{formset.prefix}-{new_index}-display_order": "3",
                f"{formset.prefix}-{new_index}-is_active": "on",
            }
        )

        response = self.client.post(editor_url, post_data)

        self.assertRedirects(response, f"{editor_url}?page={page}")
        promos = SitePageSection.objects.filter(
            page=page,
            group="promos",
        ).order_by("display_order", "pk")
        self.assertEqual(promos.count(), 3)
        self.assertEqual(
            list(promos.values_list("title", "display_order", "url")),
            [
                ("Мастер-классы", 0, "mailto:info@lukomorye.ru?subject=Мастер-класс"),
                ("Обновлённое предложение", 1, "/updated-offer/"),
                ("Новое предложение", 2, "/new-offer/"),
            ],
        )

        public_response = self.client.get(reverse("catalog:category_list"))
        self.assertContains(public_response, "Обновлённое предложение")
        self.assertContains(public_response, "Описание предложения.")
        self.assertContains(public_response, 'href="/updated-offer/"')
        self.assertContains(public_response, "Новое предложение")
        self.assertContains(public_response, 'href="/new-offer/"')
        self.assertNotContains(public_response, "Пряники с логотипом")

    def test_business_client_contacts_can_be_edited_from_all_pages(self):
        admin_user = get_user_model().objects.create_superuser(
            username="corporate_contacts_saver",
            email="corporate-contacts-saver@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)

        editor_response = self.client.get(
            reverse("site_content_manager"),
            {"page": SiteContentBlock.Page.ALL},
        )
        form = editor_response.context["business_clients_contact_form"]
        post_data = {
            "page": SiteContentBlock.Page.ALL,
            "action": "save_business_clients_contacts",
            **{
                field_name: form.initial[field_name]
                for field_name in form.fields
            },
        }
        post_data.update(
            {
                "phone_value": "+7 999 111-22-33",
                "phone_url": "tel:+79991112233",
                "email_value": "corporate@example.com",
                "email_url": "mailto:corporate@example.com",
                "address_value": "New corporate office",
                "address_description": "Business center New",
            }
        )

        response = self.client.post(reverse("site_content_manager"), post_data)

        self.assertRedirects(
            response,
            f"{reverse('site_content_manager')}?page=all",
        )
        corporate_contacts = list(
            SitePageSection.objects.filter(
                page=SitePageSection.Page.BUSINESS_CLIENTS,
                group="contacts",
            ).order_by("display_order", "pk")
        )
        self.assertEqual(corporate_contacts[0].value, "+7 999 111-22-33")
        self.assertEqual(corporate_contacts[1].value, "corporate@example.com")
        self.assertEqual(corporate_contacts[2].value, "New corporate office")
        self.assertEqual(corporate_contacts[2].description, "Business center New")

        public_response = self.client.get(reverse("business_clients"))
        self.assertContains(public_response, "+7 999 111-22-33")
        self.assertContains(public_response, "corporate@example.com")
        self.assertContains(public_response, "New corporate office")
        self.assertContains(public_response, "Business center New")

    def test_business_client_sections_are_editable_and_rendered(self):
        admin_user = get_user_model().objects.create_superuser(
            username="business_client_sections_admin",
            email="business-client-sections-admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)
        editor_url = reverse("site_content_manager")
        page = SitePageSection.Page.BUSINESS_CLIENTS

        editor_response = self.client.get(editor_url, {"page": page})
        self.assertEqual(editor_response.status_code, 200)
        for form_name in (
            "business_clients_steps_heading_form",
            "business_clients_steps_formset",
            "business_clients_payment_heading_form",
            "business_clients_payment_formset",
            "business_clients_delivery_heading_form",
            "business_clients_delivery_formset",
            "business_clients_calculator_form",
        ):
            self.assertIsNotNone(editor_response.context[form_name])
        payment_heading_form = editor_response.context[
            "business_clients_payment_heading_form"
        ]
        calculator_form = editor_response.context[
            "business_clients_calculator_form"
        ]
        for field_name in ("value", "value_en", "url"):
            self.assertNotIn(field_name, payment_heading_form.fields)
            self.assertNotIn(field_name, calculator_form.fields)
        self.assertContains(editor_response, "Корпоративным клиентам — порядок работы")
        self.assertContains(editor_response, "Корпоративным клиентам — оплата и доставка")
        self.assertContains(editor_response, "Корпоративным клиентам — калькулятор заказа")
        self.assertNotContains(editor_response, "Button text")
        self.assertNotContains(editor_response, "Button link")

        def formset_data(formset):
            data = {
                f"{formset.prefix}-TOTAL_FORMS": str(len(formset.forms)),
                f"{formset.prefix}-INITIAL_FORMS": str(formset.initial_form_count()),
                f"{formset.prefix}-MIN_NUM_FORMS": "0",
                f"{formset.prefix}-MAX_NUM_FORMS": "1000",
            }
            for form in formset.forms:
                for field_name in form.fields:
                    name = f"{form.prefix}-{field_name}"
                    if field_name == "id":
                        data[name] = str(form.instance.pk)
                    else:
                        value = form[field_name].value()
                        data[name] = (
                            "on" if field_name == "is_active" and value else value or ""
                        )
            return data

        def form_data(form):
            return {
                f"{form.prefix}-{field_name}": form[field_name].value() or ""
                for field_name in form.fields
            }

        steps = editor_response.context["business_clients_steps_formset"]
        steps_data = {
            "page": page,
            "action": "save_business_clients_steps",
            **formset_data(steps),
            **form_data(editor_response.context["business_clients_steps_heading_form"]),
            f"{steps.prefix}-0-title": "Новая заявка",
            f"{steps.prefix}-0-title_en": "New request",
            "steps-heading-section_title": "Новый процесс работы",
            "steps-heading-section_title_en": "New work process",
            "steps-heading-section_description": "Обновлённое описание процесса.",
            "steps-heading-section_description_en": "Updated process introduction.",
        }
        response = self.client.post(editor_url, steps_data)
        self.assertRedirects(response, f"{editor_url}?page={page}")
        self.assertEqual(
            SitePageSection.objects.get(
                page=page,
                group="steps",
                display_order=0,
            ).title,
            "Новая заявка",
        )

        payment_formset = editor_response.context["business_clients_payment_formset"]
        delivery_formset = editor_response.context["business_clients_delivery_formset"]
        payment_button_before = (
            payment_heading_form.instance.value,
            payment_heading_form.instance.value_en,
            payment_heading_form.instance.url,
        )
        pricing_data = {
            "page": page,
            "action": "save_business_clients_pricing",
            **formset_data(payment_formset),
            **formset_data(delivery_formset),
            **form_data(editor_response.context["business_clients_payment_heading_form"]),
            **form_data(editor_response.context["business_clients_delivery_heading_form"]),
            f"{payment_formset.prefix}-0-title": "Новый способ оплаты",
            f"{payment_formset.prefix}-0-title_en": "New payment option",
            "payment-heading-section_title": "Новая оплата",
            "payment-heading-section_title_en": "New payment",
            f"{delivery_formset.prefix}-0-title": "Новая доставка",
            f"{delivery_formset.prefix}-0-title_en": "New delivery",
            "delivery-heading-section_title": "Новая доставка и самовывоз",
            "delivery-heading-section_title_en": "New delivery and pickup",
        }
        response = self.client.post(editor_url, pricing_data)
        self.assertRedirects(response, f"{editor_url}?page={page}")
        self.assertEqual(
            SitePageSection.objects.get(
                page=page,
                group="payment",
                display_order=0,
            ).title,
            "Новый способ оплаты",
        )
        self.assertEqual(
            (
                SitePageSection.objects.get(
                    page=page,
                    group="payment",
                    display_order=0,
                ).value,
                SitePageSection.objects.get(
                    page=page,
                    group="payment",
                    display_order=0,
                ).value_en,
                SitePageSection.objects.get(
                    page=page,
                    group="payment",
                    display_order=0,
                ).url,
            ),
            payment_button_before,
        )

        calculator_button_before = (
            calculator_form.instance.value,
            calculator_form.instance.value_en,
            calculator_form.instance.url,
        )
        calculator_data = {
            "page": page,
            "action": "save_business_clients_calculator",
            **form_data(calculator_form),
            "calculator-title": "Новый калькулятор заказа",
            "calculator-title_en": "New order calculator",
            "calculator-description": "Описание нового калькулятора.",
            "calculator-description_en": "Description of the new calculator.",
            "calculator-image_alt": "Новое изображение",
            "calculator-image_alt_en": "New image",
        }
        response = self.client.post(editor_url, calculator_data)
        self.assertRedirects(response, f"{editor_url}?page={page}")
        calculator = SitePageSection.objects.get(
            page=page,
            group="calculator",
            display_order=0,
        )
        self.assertEqual(
            (calculator.value, calculator.value_en, calculator.url),
            calculator_button_before,
        )

        business_clients_response = self.client.get(reverse("business_clients"))
        for rendered_text in (
            "Новая заявка",
            "Новый процесс работы",
            "Обновлённое описание процесса.",
            "Новая оплата",
            "Новый способ оплаты",
            "Новая доставка и самовывоз",
            "Новая доставка",
            "Новый калькулятор заказа",
            "Описание нового калькулятора.",
        ):
            with self.subTest(text=rendered_text):
                self.assertContains(business_clients_response, rendered_text)
        if payment_button_before[0]:
            self.assertContains(business_clients_response, payment_button_before[0])
        if payment_button_before[2]:
            self.assertContains(
                business_clients_response,
                f'href="{payment_button_before[2]}"',
            )
        if calculator_button_before[0]:
            self.assertContains(business_clients_response, calculator_button_before[0])
        if calculator_button_before[2]:
            self.assertContains(
                business_clients_response,
                f'href="{calculator_button_before[2]}"',
            )

    def test_partnership_directions_and_success_are_editable(self):
        admin_user = get_user_model().objects.create_superuser(
            username="partnership_sections_admin",
            email="partnership-sections-admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)
        editor_url = reverse("site_content_manager")
        page = SitePageSection.Page.PARTNERSHIP
        editor_response = self.client.get(editor_url, {"page": page})

        directions_formset = editor_response.context[
            "partnership_directions_formset"
        ]
        success_formset = editor_response.context[
            "partnership_success_formset"
        ]
        directions_heading_form = editor_response.context[
            "partnership_directions_heading_form"
        ]
        success_heading_form = editor_response.context[
            "partnership_success_heading_form"
        ]
        self.assertIsNotNone(directions_formset)
        self.assertIsNotNone(success_formset)
        self.assertContains(editor_response, "Партнёрство — направления сотрудничества")
        self.assertContains(editor_response, "Партнёрство — наши успехи")

        def formset_data(formset):
            data = {
                f"{formset.prefix}-TOTAL_FORMS": str(len(formset.forms)),
                f"{formset.prefix}-INITIAL_FORMS": str(formset.initial_form_count()),
                f"{formset.prefix}-MIN_NUM_FORMS": "0",
                f"{formset.prefix}-MAX_NUM_FORMS": "1000",
            }
            for form in formset.forms:
                for field_name in form.fields:
                    name = f"{form.prefix}-{field_name}"
                    if field_name == "id":
                        data[name] = str(form.instance.pk)
                    else:
                        data[name] = form[field_name].value() or ""
            return data

        def heading_data(form):
            return {
                f"{form.prefix}-{field_name}": form[field_name].value() or ""
                for field_name in form.fields
            }

        directions_data = {
            "page": page,
            "action": "save_partnership_directions",
            **formset_data(directions_formset),
            **heading_data(directions_heading_form),
            "partnership-directions-0-title": "Новое направление",
            "partnership-directions-0-title_en": "New direction",
            "partnership-directions-heading-section_title": "Новые направления",
            "partnership-directions-heading-section_title_en": "New directions",
            "partnership-directions-heading-section_description": "Новые условия сотрудничества.",
            "partnership-directions-heading-section_description_en": "New partnership options.",
        }
        response = self.client.post(editor_url, directions_data)
        self.assertRedirects(response, f"{editor_url}?page={page}")

        success_data = {
            "page": page,
            "action": "save_partnership_success",
            **formset_data(success_formset),
            **heading_data(success_heading_form),
            "partnership-success-0-title": "Новый показатель",
            "partnership-success-0-title_en": "New metric",
            "partnership-success-0-description": "Описание нового показателя.",
            "partnership-success-0-description_en": "Description of the new metric.",
            "partnership-success-heading-section_title": "Новые успехи",
            "partnership-success-heading-section_title_en": "New success",
            "partnership-success-heading-section_description": "Обновлённое описание успехов.",
            "partnership-success-heading-section_description_en": "Updated success introduction.",
        }
        response = self.client.post(editor_url, success_data)
        self.assertRedirects(response, f"{editor_url}?page={page}")

        directions = SitePageSection.objects.get(
            page=page,
            group="directions",
            display_order=0,
        )
        success = SitePageSection.objects.get(
            page=page,
            group="stats",
            display_order=0,
        )
        self.assertEqual(directions.title, "Новое направление")
        self.assertEqual(directions.section_title, "Новые направления")
        self.assertEqual(success.title, "Новый показатель")
        self.assertEqual(success.section_title, "Новые успехи")

        public_response = self.client.get(reverse("corporate"))
        for rendered_text in (
            "Новое направление",
            "Новые направления",
            "Новые условия сотрудничества.",
            "Новый показатель",
            "Новые успехи",
            "Описание нового показателя.",
        ):
            with self.subTest(text=rendered_text):
                self.assertContains(public_response, rendered_text)

    def test_home_about_form_updates_the_section_and_both_paragraphs(self):
        admin_user = get_user_model().objects.create_superuser(
            username="home_about_saver",
            email="home-about-saver@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)
        response = self.client.post(
            reverse("site_content_manager"),
            {
                "action": "save_home_about",
                "page": SitePageSection.Page.HOME,
                "section_eyebrow": "О бренде",
                "section_eyebrow_en": "About the brand",
                "section_title": "Новый заголовок о компании",
                "section_title_en": "A new company heading",
                "description": "Первый обновлённый абзац.",
                "description_en": "The updated first paragraph.",
                "description_2": "Второй обновлённый абзац.",
                "description_2_en": "The updated second paragraph.",
                "image_alt": "Фото о компании",
                "image_alt_en": "About section image",
                "is_active": "on",
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('site_content_manager')}?page=home",
        )
        sections = list(
            SitePageSection.objects.filter(
                page=SitePageSection.Page.HOME,
                group="home_about",
            ).order_by("display_order", "pk")
        )
        self.assertEqual(sections[0].section_title, "Новый заголовок о компании")
        self.assertEqual(sections[0].value_en, "More about us")
        self.assertEqual(sections[0].url, "/about/")
        self.assertEqual(sections[1].description, "Второй обновлённый абзац.")
        self.assertEqual(sections[1].description_en, "The updated second paragraph.")

        home_response = self.client.get(reverse("home"))
        self.assertContains(home_response, "Новый заголовок о компании")
        self.assertContains(home_response, "Первый обновлённый абзац.")
        self.assertContains(home_response, "Второй обновлённый абзац.")

    def test_home_about_form_creates_section_when_it_does_not_exist(self):
        admin_user = get_user_model().objects.create_superuser(
            username="home_about_creator",
            email="home-about-creator@example.com",
            password="test-password",
        )
        SitePageSection.objects.filter(
            page=SitePageSection.Page.HOME,
            group="home_about",
        ).delete()
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse("site_content_manager"),
            {
                "action": "save_home_about",
                "page": SitePageSection.Page.HOME,
                "section_title": "Created About section",
                "description": "Created first paragraph",
                "description_2": "Created second paragraph",
                "is_active": "on",
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('site_content_manager')}?page=home",
        )
        self.assertEqual(
            SitePageSection.objects.filter(
                page=SitePageSection.Page.HOME,
                group="home_about",
            ).count(),
            2,
        )

    def test_page_content_save_updates_public_page_intro(self):
        admin_user = get_user_model().objects.create_superuser(
            username="page_content_saver",
            email="page-content-saver@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)
        response = self.client.post(
            reverse("site_content_manager"),
            {
                "action": "save_page_content",
                "page": SitePageContent.Page.ABOUT,
                "eyebrow": "Новая подпись",
                "eyebrow_en": "New eyebrow",
                "title": "Новый заголовок о нас",
                "title_en": "New about heading",
                "subtitle": "Новый подзаголовок",
                "subtitle_en": "New subtitle",
                "description": "Новое описание страницы",
                "description_en": "New page description",
                "button_text": "Связаться",
                "button_text_en": "Contact",
                "button_url": "/contacts/",
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('site_content_manager')}?page=about",
        )
        self.assertEqual(SitePageContent.objects.get().page, SitePageContent.Page.ABOUT)
        about_response = self.client.get(reverse("about"))
        self.assertContains(about_response, "Новый заголовок о нас")
        self.assertContains(about_response, "Новое описание страницы")
        self.assertContains(about_response, 'href="/contacts/"')

    def test_selected_page_content_renders_on_each_static_page(self):
        pages = (
            (SitePageContent.Page.ABOUT, "about", "Custom about heading"),
            (
                SitePageContent.Page.BUSINESS_CLIENTS,
                "business_clients",
                "Custom business heading",
            ),
            (SitePageContent.Page.PARTNERSHIP, "corporate", "Custom partner heading"),
            (SitePageContent.Page.CONTACTS, "contacts", "Custom contacts heading"),
            (SitePageContent.Page.DELIVERY, "delivery", "Custom delivery heading"),
            (SitePageContent.Page.FAQ, "faq", "Custom FAQ heading"),
            (SitePageContent.Page.FEEDBACK, "feedback", "Custom feedback heading"),
            (SitePageContent.Page.PACKAGING, "packaging", "Custom packaging heading"),
            (SitePageContent.Page.CATALOG, "catalog:category_list", "Custom catalog heading"),
            (SitePageContent.Page.CATEGORIES, "catalog:categories", "Custom categories heading"),
        )
        for page, route_name, heading in pages:
            with self.subTest(page=page):
                SitePageContent.objects.create(page=page, title=heading)
                response = self.client.get(reverse(route_name))
                self.assertContains(response, heading)

    def test_page_content_photo_is_used_as_the_page_hero_image(self):
        image_buffer = BytesIO()
        Image.new("RGB", (1, 1), color="white").save(image_buffer, format="PNG")

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                page_content = SitePageContent.objects.create(
                    page=SitePageContent.Page.ABOUT,
                    image=SimpleUploadedFile(
                        "about-hero.png",
                        image_buffer.getvalue(),
                        content_type="image/png",
                    ),
                )

                response = self.client.get(reverse("about"))

                self.assertContains(
                    response,
                    f"background-image:url('{page_content.image.url}')",
                )

    def test_home_banner_save_updates_homepage_carousel(self):
        admin_user = get_user_model().objects.create_superuser(
            username="home_banner_saver",
            email="home-banner-saver@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)
        editor_response = self.client.get(
            f"{reverse('site_content_manager')}?page={SiteContentBlock.Page.HOME}"
        )
        self.assertEqual(editor_response.status_code, 200)
        slide_form = editor_response.context["slide_formset"].forms[0]
        self.assertEqual(
            set(slide_form.fields),
            {"image", "display_order", "is_active", "id"},
        )
        self.assertContains(editor_response, 'name="slides-0-image"')
        self.assertContains(editor_response, 'name="slides-0-is_active"')

        post_data = {
            "action": "save_home_slides",
            "page": SiteContentBlock.Page.HOME,
            "slides-TOTAL_FORMS": "4",
            "slides-INITIAL_FORMS": "0",
            "slides-MIN_NUM_FORMS": "0",
            "slides-MAX_NUM_FORMS": "1000",
        }
        for index in range(4):
            post_data.update(
                {
                    f"slides-{index}-display_order": str(index),
                    f"slides-{index}-is_active": "on",
                }
            )

        response = self.client.post(reverse("site_content_manager"), post_data)

        self.assertRedirects(
            response,
            f"{reverse('site_content_manager')}?page=home",
        )
        self.assertEqual(HomeHeroSlide.objects.count(), 4)
        home_response = self.client.get(reverse("home"))
        self.assertContains(home_response, 'class="hero-slide hero-slide-gifts"')
        self.assertContains(home_response, 'class="hero-slide hero-slide-sweets"')
        self.assertContains(home_response, 'class="hero-slide hero-slide-team"')
        self.assertNotContains(home_response, "Тёплые моменты теперь другие")
        self.assertNotContains(home_response, "Описание второго баннера")
        self.assertNotContains(home_response, "Открыть каталог")

    def test_blank_home_banner_form_does_not_create_an_active_slide(self):
        admin_user = get_user_model().objects.create_superuser(
            username="home_banner_blank_form",
            email="home-banner-blank-form@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)

        post_data = {
            "action": "save_home_slides",
            "page": SiteContentBlock.Page.HOME,
            "slides-TOTAL_FORMS": "4",
            "slides-INITIAL_FORMS": "0",
            "slides-MIN_NUM_FORMS": "0",
            "slides-MAX_NUM_FORMS": "1000",
            "slides-3-display_order": "3",
        }
        for index in range(3):
            post_data.update(
                {
                    f"slides-{index}-display_order": str(index),
                    f"slides-{index}-is_active": "on",
                }
            )

        response = self.client.post(reverse("site_content_manager"), post_data)

        self.assertRedirects(
            response,
            f"{reverse('site_content_manager')}?page=home",
        )
        self.assertEqual(HomeHeroSlide.objects.count(), 3)

    def test_site_content_manager_does_not_create_new_page_blocks(self):
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

        self.assertEqual(response.status_code, 200)
        self.assertFalse(SiteContentBlock.objects.exists())

    def test_editing_site_content_page_updates_and_stays_on_the_block(self):
        admin_user = get_user_model().objects.create_superuser(
            username="content_page_editor",
            email="content-page-editor@example.com",
            password="content-password",
        )
        block = SiteContentBlock.objects.create(
            page=SiteContentBlock.Page.ABOUT,
            title="Move this block",
        )
        self.client.force_login(admin_user)
        edit_url = reverse("site_content_edit", args=(block.pk,))

        response = self.client.post(
            edit_url,
            {
                "page": SiteContentBlock.Page.PARTNERSHIP,
                "title": block.title,
                "title_en": "",
                "description": "",
                "description_en": "",
                "display_order": "0",
                "is_active": "on",
            },
        )

        self.assertRedirects(response, edit_url)
        block.refresh_from_db()
        self.assertEqual(block.page, SiteContentBlock.Page.PARTNERSHIP)

        edit_response = self.client.get(edit_url)
        self.assertEqual(edit_response.status_code, 200)
        self.assertEqual(edit_response.context["form"].instance.page, "corporate")
        self.assertContains(edit_response, 'option value="corporate" selected')

        partnership_response = self.client.get(reverse("corporate"))
        about_response = self.client.get(reverse("about"))
        self.assertContains(partnership_response, "Move this block")
        self.assertNotContains(about_response, "Move this block")

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
                "display_order": "1",
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
        self.assertEqual(product.display_order, 0)

    def test_product_admin_shows_saved_display_numbers(self):
        admin_user = get_user_model().objects.create_superuser(
            username="numbered_products_admin",
            email="numbered-products-admin@example.com",
            password="test-password",
        )
        category = Category.objects.create(name="Numbered products category")
        for name, display_order in (
            ("Fourth product", 30),
            ("Second product", 10),
            ("Third product", 20),
            ("First product", 0),
        ):
            Product.objects.create(
                name=name,
                category=category,
                display_order=display_order,
            )
        self.client.force_login(admin_user)

        response = self.client.get(reverse("admin_section", args=("products",)))

        self.assertEqual(response.status_code, 200)
        for number in (1, 11, 21, 31):
            with self.subTest(number=number):
                self.assertContains(response, f"Номер отображения: {number}")
        self.assertNotContains(response, "site-content-existing-number")
        first_product = Product.objects.get(name="First product")
        edit_response = self.client.get(
            reverse("admin_section_edit", args=("products", first_product.pk))
        )
        self.assertEqual(
            edit_response.context["form"]["display_order"].value(),
            1,
        )
        self.assertContains(edit_response, "Номер отображения")
        content = response.content.decode()
        self.assertLess(content.index("First product"), content.index("Second product"))
        self.assertLess(content.index("Second product"), content.index("Third product"))
        self.assertLess(content.index("Third product"), content.index("Fourth product"))

    def test_product_display_number_is_one_based_on_create_and_edit(self):
        admin_user = get_user_model().objects.create_superuser(
            username="product_display_number_admin",
            email="product-display-number-admin@example.com",
            password="test-password",
        )
        category = Category.objects.create(name="Display number category")
        product = Product.objects.create(
            name="Display number product",
            category=category,
            display_order=4,
        )
        self.client.force_login(admin_user)

        edit_response = self.client.get(
            reverse("admin_section_edit", args=("products", product.pk))
        )
        self.assertEqual(
            edit_response.context["form"]["display_order"].value(),
            5,
        )
        response = self.client.post(
            reverse("admin_section_edit", args=("products", product.pk)),
            {
                "name": product.name,
                "name_en": "",
                "category": category.pk,
                "description": "",
                "description_en": "",
                "price": "",
                "image_url": "",
                "display_order": "2",
                "is_active": "on",
                "is_featured": "on",
            },
        )
        self.assertRedirects(
            response,
            reverse("admin_section_edit", args=("products", product.pk)),
        )
        product.refresh_from_db()
        self.assertEqual(product.display_order, 1)

    def test_category_display_number_is_one_based_on_create_edit_and_list(self):
        admin_user = get_user_model().objects.create_superuser(
            username="category_display_number_admin",
            email="category-display-number-admin@example.com",
            password="test-password",
        )
        Category.objects.create(
            name="First numbered category",
            display_order=0,
        )
        second_category = Category.objects.create(
            name="Second numbered category",
            display_order=1,
        )
        self.client.force_login(admin_user)

        list_response = self.client.get(
            reverse("admin_section", args=("categories",))
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "Номер отображения: 1")
        self.assertContains(list_response, "Номер отображения: 2")
        list_content = list_response.content.decode()
        self.assertLess(
            list_content.index("First numbered category"),
            list_content.index("Second numbered category"),
        )

        edit_url = reverse("admin_section_edit", args=("categories", second_category.pk))
        edit_response = self.client.get(edit_url)
        self.assertEqual(edit_response.context["form"]["display_order"].value(), 2)
        self.assertContains(edit_response, "Номер отображения")

        response = self.client.post(
            edit_url,
            {
                "name": second_category.name,
                "name_en": "",
                "description": "",
                "description_en": "",
                "image_url": "",
                "display_order": "1",
                "is_active": "on",
            },
        )
        self.assertRedirects(
            response,
            reverse("admin_section_edit", args=("categories", second_category.pk)),
        )
        second_category.refresh_from_db()
        self.assertEqual(second_category.display_order, 0)

        create_response = self.client.get(
            reverse("admin_section_new", args=("categories",))
        )
        self.assertEqual(create_response.context["form"]["display_order"].value(), 1)

    def test_product_filter_display_number_is_one_based_on_create_edit_and_list(self):
        admin_user = get_user_model().objects.create_superuser(
            username="filter_display_number_admin",
            email="filter-display-number-admin@example.com",
            password="test-password",
        )
        ProductFilterOption.objects.create(
            filter_type=ProductFilterOption.FilterType.SIZE,
            value="small",
            label="Small filter option",
            display_order=0,
        )
        second_option = ProductFilterOption.objects.create(
            filter_type=ProductFilterOption.FilterType.SIZE,
            value="large",
            label="Large filter option",
            display_order=1,
        )
        self.client.force_login(admin_user)

        list_response = self.client.get(reverse("admin_section", args=("filters",)))

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "Номер отображения: 1")
        self.assertContains(list_response, "Номер отображения: 2")
        list_content = list_response.content.decode()
        self.assertLess(
            list_content.index("Small filter option"),
            list_content.index("Large filter option"),
        )

        edit_url = reverse("admin_section_edit", args=("filters", second_option.pk))
        edit_response = self.client.get(edit_url)
        self.assertEqual(edit_response.context["form"]["display_order"].value(), 2)
        self.assertContains(edit_response, "Номер отображения")

        response = self.client.post(
            edit_url,
            {
                "filter_type": ProductFilterOption.FilterType.SIZE,
                "value": second_option.value,
                "label": second_option.label,
                "label_en": "",
                "display_order": "1",
                "is_active": "on",
            },
        )
        self.assertRedirects(
            response,
            reverse("admin_section_edit", args=("filters", second_option.pk)),
        )
        second_option.refresh_from_db()
        self.assertEqual(second_option.display_order, 0)

        create_response = self.client.get(reverse("admin_section_new", args=("filters",)))
        self.assertEqual(create_response.context["form"]["display_order"].value(), 1)

    def test_dough_and_icing_filter_descriptions_can_be_edited(self):
        admin_user = get_user_model().objects.create_superuser(
            username="filter_descriptions_admin",
            email="filter-descriptions-admin@example.com",
            password="test-password",
        )
        options = (
            ProductFilterOption.objects.create(
                filter_type=ProductFilterOption.FilterType.DOUGH,
                value="test-classic-dough",
                label="Классическое тесто",
                label_en="Classic dough",
            ),
            ProductFilterOption.objects.create(
                filter_type=ProductFilterOption.FilterType.COATING,
                value="test-icing",
                label="Айсинг",
                label_en="Icing",
            ),
        )
        self.client.force_login(admin_user)

        for option, description, description_en in (
            (options[0], "Мягкое классическое тесто.", "Soft classic dough."),
            (options[1], "Покрытие из айсинга.", "Icing coating."),
        ):
            with self.subTest(filter_type=option.filter_type):
                edit_url = reverse("admin_section_edit", args=("filters", option.pk))
                response = self.client.post(
                    edit_url,
                    {
                        "filter_type": option.filter_type,
                        "value": option.value,
                        "label": option.label,
                        "label_en": option.label_en,
                        "description": description,
                        "description_en": description_en,
                        "display_order": "1",
                        "is_active": "on",
                    },
                )
                self.assertRedirects(response, edit_url)
                option.refresh_from_db()
                self.assertEqual(option.description, description)
                self.assertEqual(option.description_en, description_en)

        catalog_response = self.client.get(reverse("catalog:category_list"))
        self.assertContains(
            catalog_response,
            'class="catalog-filter-help-button" type="button"',
        )
        self.assertContains(catalog_response, "Мягкое классическое тесто.")
        self.assertContains(catalog_response, "Покрытие из айсинга.")

    def test_product_filter_options_are_easy_to_select_by_group(self):
        admin_user = get_user_model().objects.create_superuser(
            username="product_filter_groups_admin",
            email="product-filter-groups-admin@example.com",
            password="test-password",
        )
        category = Category.objects.create(name="Filter options category")
        size_option = ProductFilterOption.objects.create(
            filter_type=ProductFilterOption.FilterType.SIZE,
            value="medium",
            label="Средний",
            label_en="Medium",
        )
        packaging_option = ProductFilterOption.objects.create(
            filter_type=ProductFilterOption.FilterType.PACKAGING,
            value="gift-box",
            label="Подарочная коробка",
            label_en="Gift box",
        )
        self.client.force_login(admin_user)

        editor_response = self.client.get(
            reverse("admin_section_new", args=("products",))
        )
        filter_options_field = editor_response.context["form"].fields[
            "filter_options"
        ]
        self.assertIsInstance(
            filter_options_field.widget,
            forms.CheckboxSelectMultiple,
        )
        filter_groups = [choice[0] for choice in filter_options_field.choices]
        self.assertIn("Размер", filter_groups)
        self.assertIn("Упаковка", filter_groups)
        self.assertContains(editor_response, "Отметьте все подходящие параметры.")
        self.assertContains(editor_response, 'type="checkbox"')
        self.assertContains(editor_response, "Подарочная коробка")

        response = self.client.post(
            reverse("admin_section_new", args=("products",)),
            {
                "name": "Product with grouped filters",
                "name_en": "Product with grouped filters EN",
                "category": category.pk,
                "description": "Description",
                "description_en": "English description",
                "price": "120.00",
                "image_url": "",
                "display_order": "1",
                "filter_options": [str(size_option.pk), str(packaging_option.pk)],
                "is_active": "on",
                "is_featured": "on",
            },
        )

        product = Product.objects.get(name="Product with grouped filters")
        self.assertRedirects(
            response,
            reverse("admin_section_edit", args=("products", product.pk)),
        )
        self.assertSetEqual(
            set(product.filter_options.values_list("pk", flat=True)),
            {size_option.pk, packaging_option.pk},
        )

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
            configuration={
                "flavor": "classic",
                "quantity": 3,
                "size": "5",
                "shape": "heart",
                "coating": "icing",
                "packaging": "ribbon",
                "delivery": "moscow",
                "payment": "organization",
            },
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
        for visible_option in (
            "Вкус",
            "Имбирный пряник (классика)",
            "Количество",
            "Покрытие",
            "Пищевая печать на глазури",
            "Способ оплаты",
            "От организации, 100% предоплата",
        ):
            with self.subTest(option=visible_option):
                self.assertContains(order_response, visible_option)
        self.assertNotContains(order_response, "'flavor':")
        self.assertNotContains(order_response, "'payment':")
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

    def test_feedback_can_be_deleted_from_admin_with_delete_permission(self):
        admin_user = get_user_model().objects.create_user(
            username="feedback_delete_admin",
            email="feedback-delete-admin@example.com",
            is_staff=True,
            is_superuser=True,
        )
        feedback = FeedbackSubmission.objects.create(
            name="Feedback to delete",
            email="feedback-delete@example.com",
            subject="Delete this feedback",
            message="This feedback should be removable.",
            consent_given=True,
        )
        delete_url = reverse(
            "admin_section_delete",
            args=("messages", feedback.pk),
        )
        self.client.force_login(admin_user)

        list_response = self.client.get(reverse("admin_section", args=("messages",)))
        self.assertContains(list_response, "Удалить")
        self.assertEqual(self.client.get(delete_url).status_code, 405)
        self.assertTrue(FeedbackSubmission.objects.filter(pk=feedback.pk).exists())

        response = self.client.post(delete_url)

        self.assertRedirects(response, reverse("admin_section", args=("messages",)))
        self.assertFalse(FeedbackSubmission.objects.filter(pk=feedback.pk).exists())

    def test_feedback_delete_requires_delete_permission(self):
        manager = get_user_model().objects.create_user(
            username="feedback_delete_manager",
            is_staff=True,
        )
        view_permission = Permission.objects.get(
            content_type__app_label="core",
            codename="view_feedbacksubmission",
        )
        manager.user_permissions.add(view_permission)
        feedback = FeedbackSubmission.objects.create(
            name="Protected feedback",
            email="protected-feedback@example.com",
            subject="Protected",
            message="This feedback must remain.",
            consent_given=True,
        )
        delete_url = reverse(
            "admin_section_delete",
            args=("messages", feedback.pk),
        )
        self.client.force_login(manager)

        response = self.client.post(delete_url)

        self.assertEqual(response.status_code, 403)
        self.assertTrue(FeedbackSubmission.objects.filter(pk=feedback.pk).exists())

    def test_feedback_can_be_hidden_and_restored_from_admin(self):
        admin_user = get_user_model().objects.create_user(
            username="feedback_visibility_admin",
            email="feedback-visibility-admin@example.com",
            is_staff=True,
            is_superuser=True,
        )
        feedback = FeedbackSubmission.objects.create(
            name="Feedback visibility",
            email="feedback-visibility@example.com",
            subject="Visibility toggle feedback",
            message="This feedback can be hidden and restored.",
            consent_given=True,
        )
        list_url = reverse("admin_section", args=("messages",))
        hide_url = reverse(
            "admin_section_visibility",
            args=("messages", feedback.pk, "hide"),
        )
        show_url = reverse(
            "admin_section_visibility",
            args=("messages", feedback.pk, "show"),
        )
        self.client.force_login(admin_user)

        visible_response = self.client.get(list_url)
        self.assertContains(visible_response, "Скрыть")
        self.assertContains(visible_response, "Visibility toggle feedback")
        self.assertEqual(self.client.get(hide_url).status_code, 405)

        self.assertRedirects(self.client.post(hide_url), list_url)
        feedback.refresh_from_db()
        self.assertTrue(feedback.is_hidden)
        visible_response = self.client.get(list_url)
        self.assertNotContains(visible_response, "Visibility toggle feedback")
        self.assertEqual(
            self.client.get(reverse("admin_dashboard")).context[
                "new_feedback_count"
            ],
            0,
        )

        hidden_url = f"{list_url}?hidden=1"
        hidden_response = self.client.get(hidden_url)
        self.assertContains(hidden_response, "Visibility toggle feedback")
        self.assertContains(hidden_response, "Показать")
        manager_response = self.client.get(reverse("manager_dashboard"))
        self.assertNotIn(feedback, manager_response.context["feedback_items"])

        self.assertRedirects(self.client.post(show_url), list_url)
        feedback.refresh_from_db()
        self.assertFalse(feedback.is_hidden)
        self.assertContains(self.client.get(list_url), "Visibility toggle feedback")

    def test_feedback_visibility_requires_change_permission(self):
        manager = get_user_model().objects.create_user(
            username="feedback_visibility_manager",
            is_staff=True,
        )
        manager.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="core",
                codename="view_feedbacksubmission",
            )
        )
        feedback = FeedbackSubmission.objects.create(
            name="Protected feedback visibility",
            email="protected-visibility@example.com",
            subject="Protected visibility",
            message="Only users with change permission may hide this.",
            consent_given=True,
        )
        hide_url = reverse(
            "admin_section_visibility",
            args=("messages", feedback.pk, "hide"),
        )
        self.client.force_login(manager)

        response = self.client.post(hide_url)

        self.assertEqual(response.status_code, 403)
        feedback.refresh_from_db()
        self.assertFalse(feedback.is_hidden)

    def test_cart_order_items_render_as_labeled_product_details(self):
        admin_user = get_user_model().objects.create_superuser(
            username="cart_order_details_admin",
            email="cart-order-details-admin@example.com",
            password="test-password",
        )
        order = Preorder.objects.create(
            name="Cart order customer",
            email="cart-order@example.com",
            phone="+7 900 000-00-00",
            configuration={
                "items": [
                    {
                        "product_id": 2,
                        "name": "Подарочные мишки",
                        "quantity": 2,
                        "size": "8",
                        "coating": "painting",
                        "dough": "chocolate",
                        "packaging": "gift_box",
                        "unit_price": "2490",
                    },
                    {
                        "product_id": 1,
                        "name": "Печенье-сердца",
                        "quantity": 1,
                        "size": "8",
                        "coating": "chocolate",
                        "dough": "classic",
                        "packaging": "gift_box",
                        "unit_price": "1490",
                    },
                ],
                "delivery": "moscow",
                "payment": "organization",
            },
            unit_price="1990.00",
            discount_percent=0,
            delivery_cost="700.00",
            total_price="5470.00",
            consent_given=True,
        )
        self.client.force_login(admin_user)

        response = self.client.get(
            reverse("admin_section_edit", args=("orders", order.pk))
        )

        self.assertEqual(response.status_code, 200)
        for visible_detail in (
            "Подарочные мишки",
            "Печенье-сердца",
            "Количество",
            "Покрытие",
            "Роспись на айсинге",
            "Тесто",
            "Шоколадное",
            "Подарочная коробка",
            "2490 ₽",
            "1490 ₽",
            "Доставка по Москве (в пределах МКАД)",
            "От организации, 100% предоплата",
        ):
            with self.subTest(detail=visible_detail):
                self.assertContains(response, visible_detail)
        self.assertNotContains(response, "'product_id':")
        self.assertNotContains(response, "'gift_box'")

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


    def test_calculator_settings_require_permission_and_can_be_saved(self):
        manager = get_user_model().objects.create_user(
            username="calculator_manager",
            password="test-password",
            is_staff=True,
        )
        self.client.force_login(manager)
        calculator_url = reverse("calculator_settings")

        dashboard = self.client.get(self.url)
        self.assertRedirects(
            dashboard,
            reverse("manager_dashboard"),
            fetch_redirect_response=False,
        )
        self.assertEqual(self.client.get(calculator_url).status_code, 403)

        admin_user = get_user_model().objects.create_superuser(
            username="calculator_admin",
            email="calculator-admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)
        response = self.client.get(calculator_url)

        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        data = {
            name: form[name].value() if form[name].value() is not None else ""
            for name in form.fields
        }
        data.update(
            {
                "base_unit_price": "110",
                "product_count": "2",
                "product_0_name": "Пряник",
                "product_0_name_en": "Gingerbread",
                "product_1_name": "Печенье",
                "product_1_name_en": "Cookies",
                "product_1_base_price": "45",
                "delivery_cost_moscow": "750",
                "discount_quantity_1": "100",
                "discount_percent_1": "25",
                "lead_time_days": "5",
            }
        )
        response = self.client.post(calculator_url, data)

        self.assertRedirects(response, calculator_url)
        settings = CalculatorSettings.objects.get(pk=1)
        self.assertEqual(settings.pricing["base_unit_price"], "110")
        self.assertEqual(
            settings.pricing["products"],
            [
                {
                    "value": "пряник",
                    "label": "Пряник",
                    "label_en": "Gingerbread",
                    "base_unit_price": "110",
                },
                {
                    "value": "печенье",
                    "label": "Печенье",
                    "label_en": "Cookies",
                    "base_unit_price": "45",
                },
            ],
        )
        self.assertEqual(settings.pricing["delivery_costs"]["moscow"], "750")
        self.assertEqual(settings.pricing["discount_tiers"][0], [100, 25])
        self.assertEqual(settings.pricing["lead_time_days"], 5)
        home = self.client.get(reverse("home"))
        self.assertContains(home, 'data-base-price="110"')
        self.assertContains(home, 'data-base-price="45"')
        self.assertContains(home, "Печенье")


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

    def test_manager_page_requires_staff_and_allows_staff_without_data_permissions(self):
        response = self.client.get(self.manager_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

        self.client.force_login(self.manager)
        response = self.client.get(self.manager_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "У вашей учётной записи пока нет доступа")

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
        self.assertContains(response, 'name="delivery_date"')
        self.assertEqual(response.context["order_counts"][Preorder.Status.NEW], 1)

        delivery_date = date.today() + timedelta(days=7)
        response = self.client.post(
            reverse(self.status_url_name, args=[self.order.pk]),
            {
                "status": Preorder.Status.PRODUCTION,
                "delivery_date": delivery_date.isoformat(),
            },
        )

        self.assertRedirects(response, self.manager_url)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Preorder.Status.PRODUCTION)
        self.assertEqual(self.order.delivery_date, delivery_date)

    def test_manager_can_filter_feedback_by_source(self):
        self.grant_order_permissions("view_feedbacksubmission")
        business_feedback = FeedbackSubmission.objects.create(
            name="Sam",
            email="sam@example.com",
            subject="Corporate order question",
            message="A business client inquiry.",
            consent_given=True,
            source=FeedbackSubmission.Source.BUSINESS_CLIENTS,
        )
        FeedbackSubmission.objects.create(
            name="Lee",
            email="lee@example.com",
            subject="Partnership question",
            message="A partnership inquiry.",
            consent_given=True,
            source=FeedbackSubmission.Source.PARTNERSHIP,
        )
        self.client.force_login(self.manager)

        response = self.client.get(
            self.manager_url,
            {"feedback_source": FeedbackSubmission.Source.BUSINESS_CLIENTS},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, business_feedback.subject)
        self.assertContains(response, "Корпоративные клиенты")
        self.assertNotContains(response, "Partnership question")
        self.assertEqual(
            response.context["selected_feedback_source"],
            FeedbackSubmission.Source.BUSINESS_CLIENTS,
        )

        response = self.client.get(
            self.manager_url,
            {"feedback_source": "not-a-source"},
        )
        self.assertContains(response, "Partnership question")
        self.assertContains(response, business_feedback.subject)
        self.assertEqual(response.context["selected_feedback_source"], "")

    def test_manager_order_update_rejects_invalid_delivery_date(self):
        self.grant_order_permissions("view_preorder", "change_preorder")
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse(self.status_url_name, args=[self.order.pk]),
            {
                "status": Preorder.Status.PRODUCTION,
                "delivery_date": "not-a-date",
            },
        )

        self.assertRedirects(response, self.manager_url)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Preorder.Status.NEW)
        self.assertIsNone(self.order.delivery_date)

    def test_manager_can_hide_and_delete_feedback_from_dashboard(self):
        self.grant_order_permissions(
            "view_feedbacksubmission",
            "change_feedbacksubmission",
            "delete_feedbacksubmission",
        )
        feedback = FeedbackSubmission.objects.create(
            name="Sam",
            email="sam@example.com",
            subject="Dashboard feedback",
            message="Please follow up.",
            consent_given=True,
        )
        self.client.force_login(self.manager)

        response = self.client.get(self.manager_url)

        self.assertContains(response, "Скрыть")
        self.assertContains(response, "Удалить")
        self.assertContains(
            response,
            reverse("admin_section_edit", args=("messages", feedback.pk)),
        )
        self.assertRegex(
            response.content.decode(),
            r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}",
        )
        hide_url = reverse(
            "admin_section_visibility",
            args=("messages", feedback.pk, "hide"),
        )
        self.assertRedirects(
            self.client.post(hide_url, {"return_to_manager": "1"}),
            self.manager_url,
        )
        feedback.refresh_from_db()
        self.assertTrue(feedback.is_hidden)

        second_feedback = FeedbackSubmission.objects.create(
            name="Lee",
            email="lee@example.com",
            subject="Delete dashboard feedback",
            message="This can be deleted.",
            consent_given=True,
        )
        delete_url = reverse(
            "admin_section_delete",
            args=("messages", second_feedback.pk),
        )
        self.assertRedirects(
            self.client.post(delete_url, {"return_to_manager": "1"}),
            self.manager_url,
        )
        self.assertFalse(
            FeedbackSubmission.objects.filter(pk=second_feedback.pk).exists()
        )

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

    def test_custom_pricing_is_used_by_server_calculations_and_homepage(self):
        settings = CalculatorSettings.objects.create(
            pricing={
                "base_unit_price": "110",
                "size_multipliers": {"3": "0.55", "5": "1", "7": "1.4", "10": "1.9", "12": "2.4", "15": "3"},
                "flavor_additions": {"classic": "0", "chocolate": "15", "honey": "10", "cinnamon": "8"},
                "coating_additions": {"icing": "0", "painting": "15", "partial": "8", "none": "-15"},
                "packaging_additions": {"ribbon": "0", "box": "35", "premium": "80", "none": "-15"},
                "delivery_costs": {"moscow": "750", "outside": "1200", "pickup": "0"},
                "discount_tiers": [[100, 25], [50, 15], [20, 10]],
                "lead_time_days": 5,
            }
        )

        quote = calculate_quote(self.configuration, settings.pricing)
        response = self.client.get(reverse("home"))

        self.assertEqual(quote["unit_price"], Decimal("110"))
        self.assertEqual(quote["discount_percent"], 25)
        self.assertEqual(quote["delivery_cost"], Decimal("750"))
        self.assertEqual(quote["lead_time_days"], 5)
        self.assertEqual(quote["total_price"], Decimal("9000.00"))
        self.assertContains(response, 'data-base-price="110"')
        self.assertContains(response, 'data-cost="750"')
        self.assertContains(response, "5 дн.")
        self.assertEqual(
            response.context["calculator_pricing"]["discount_tiers"],
            ((100, 25), (50, 15), (20, 10)),
        )
        preorder_response = self.client.post(
            reverse("preorder"),
            {
                **self.configuration,
                "name": "Иван",
                "email": "ivan@example.com",
                "phone": "+74951234567",
                "address": "Москва",
                "consent_given": "on",
            },
        )
        self.assertRedirects(preorder_response, "/#calculator")
        preorder = Preorder.objects.get()
        self.assertEqual(preorder.unit_price, Decimal("110"))
        self.assertEqual(preorder.discount_percent, 25)
        self.assertEqual(preorder.delivery_cost, Decimal("750"))
        self.assertEqual(preorder.total_price, Decimal("9000.00"))

    def test_selected_product_controls_quote_and_is_saved_with_preorder(self):
        settings = CalculatorSettings.objects.create(
            pricing={
                "base_unit_price": "98",
                "products": [
                    {
                        "value": "gingerbread",
                        "label": "Пряник",
                        "label_en": "Gingerbread",
                        "base_unit_price": "98",
                    },
                    {
                        "value": "cookies",
                        "label": "Печенье",
                        "label_en": "Cookies",
                        "base_unit_price": "45",
                    },
                ],
            }
        )
        configuration = {**self.configuration, "product": "cookies"}

        quote = calculate_quote(configuration, settings.pricing)
        response = self.client.post(
            reverse("preorder"),
            {
                **configuration,
                "name": "Иван",
                "email": "ivan@example.com",
                "phone": "+74951234567",
                "address": "Москва",
                "consent_given": "on",
            },
        )

        self.assertEqual(quote["unit_price"], Decimal("45"))
        self.assertRedirects(response, "/#calculator")
        preorder = Preorder.objects.get()
        self.assertEqual(preorder.configuration["product"], "cookies")
        self.assertEqual(preorder.configuration["product_name"], "Печенье")
        self.assertEqual(preorder.unit_price, Decimal("45"))

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
        self.assertContains(response, "<title>Обратная связь — Вкусно Да Сладко</title>")
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
        self.assertEqual(submission.source, FeedbackSubmission.Source.FEEDBACK)

    def test_quick_feedback_submission_returns_json_and_saves_message(self):
        response = self.client.post(
            reverse("quick_feedback"),
            {
                "name": "Иван",
                "email": "ivan@example.com",
                "subject": "Вопрос о заказе",
                "message": "Подскажите сроки изготовления.",
                "consent_given": "on",
            },
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Спасибо!", response.json()["message"])
        self.assertTrue(
            FeedbackSubmission.objects.filter(
                name="Иван",
                email="ivan@example.com",
                subject="Вопрос о заказе",
                source=FeedbackSubmission.Source.CONTACT,
            ).exists()
        )
        self.assertEqual(self.client.get(reverse("quick_feedback")).status_code, 405)

    def test_quick_feedback_submission_records_selected_source(self):
        response = self.client.post(
            reverse("quick_feedback"),
            {
                "name": "Иван",
                "email": "ivan@example.com",
                "subject": "Корпоративный заказ",
                "message": "Нужен заказ для команды.",
                "consent_given": "on",
                "source": FeedbackSubmission.Source.BUSINESS_CLIENTS,
                "phone": "+7 900 000-00-00",
            },
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            FeedbackSubmission.objects.get().source,
            FeedbackSubmission.Source.BUSINESS_CLIENTS,
        )
        self.assertEqual(FeedbackSubmission.objects.get().phone, "+7 900 000-00-00")

    def test_quick_feedback_submission_rejects_unknown_source(self):
        response = self.client.post(
            reverse("quick_feedback"),
            {
                "name": "Иван",
                "email": "ivan@example.com",
                "subject": "Вопрос",
                "message": "Нужна помощь.",
                "consent_given": "on",
                "source": "not-a-source",
            },
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(FeedbackSubmission.objects.exists())

    def test_quick_feedback_submission_returns_field_validation_errors(self):
        response = self.client.post(
            reverse("quick_feedback"),
            {
                "name": "Иван",
                "email": "not-an-email",
                "subject": "Вопрос",
                "message": "Нужна помощь.",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json()["errors"])
        self.assertIn("consent_given", response.json()["errors"])
        self.assertFalse(FeedbackSubmission.objects.exists())

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
        self.assertContains(
            response,
            'querySelector(".contact-float-toggle[type=\\"button\\"]")',
        )
        self.assertContains(response, 'aria-controls="contact-float-menu"')
        self.assertContains(response, 'aria-label="Открыть способы связи"')
        self.assertContains(response, '>Связаться</span>')
        self.assertContains(response, "Оставить отзыв")
        self.assertContains(response, 'id="contact-float-feedback"')
        self.assertContains(response, 'role="dialog" aria-modal="true"')
        self.assertContains(response, reverse("quick_feedback"))
        self.assertContains(response, 'WhatsApp')
        self.assertContains(response, 'href="https://max.ru/"')
        self.assertContains(response, 'aria-label="Написать в MAX"')
        self.assertContains(response, 'Позвонить')
        self.assertContains(response, 'class="wordmark-name">Вкусно Да Сладко</span>')
        self.assertContains(response, 'class="wordmark-caption">Кондитерские изделия</span>')
        self.assertContains(response, 'class="site-intro-name">Вкусно Да Сладко</span>')
        self.assertContains(response, 'class="footer-brand-name">Вкусно Да Сладко</span>')
        self.assertContains(response, "Вкусно Да Сладко. Все права защищены.")
        self.assertContains(response, 'href="/#calculator"')
        self.assertContains(response, "Перейти к калькулятору")
        self.assertContains(response, ">Наша продукция</span>")

        partnership_response = self.client.get(reverse("corporate"))
        self.assertContains(partnership_response, "data-open-partnership-inquiry")
        self.assertContains(partnership_response, 'id="partnership-inquiry-modal"')
        self.assertContains(partnership_response, 'action="/feedback/quick/"')

        self.client.post(
            reverse("set_language"),
            {"language": "en", "next": reverse("home")},
        )
        english_response = self.client.get(reverse("home"))
        self.assertContains(
            english_response,
            'class="wordmark-name">Vkusno Da Sladko</span>',
        )
        self.assertContains(
            english_response,
            'class="footer-brand-name">Vkusno Da Sladko</span>',
        )
        self.assertContains(
            english_response,
            'class="mobile-menu-brand-name">Vkusno Da Sladko</span>',
        )
        self.assertContains(
            english_response,
            'class="site-intro-name">Vkusno Da Sladko</span>',
        )
        self.assertContains(english_response, '<span class="site-intro-mark">V</span>')
        self.assertContains(
            self.client.get(reverse("business_clients")),
            'data-brand="Vkusno Da Sladko"',
        )
        self.assertContains(
            self.client.get(reverse("corporate")),
            'data-brand="Vkusno Da Sladko"',
        )

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
        self.assertContains(response, "<title>О нас — Вкусно Да Сладко</title>")
        self.assertContains(response, 'aria-current="page">О нас</span>')
        self.assertContains(response, "Наша история")
        self.assertContains(response, "«Вкусно Да Сладко» родилось")
        self.assertNotContains(response, "Лукоморье родилось")
        self.assertContains(response, "Наши ценности")
        self.assertContains(response, "5000+")
        self.assertContains(response, 'href="mailto:hello@lukomorye.example"')
        self.assertContains(response, f'href="{reverse("about")}">О нас</a>')

    def test_partnership_page_renders_directions_metrics_and_navigation(self):
        response = self.client.get(reverse("corporate"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<title>Партнёрство с «Вкусно Да Сладко» — Вкусно Да Сладко</title>")
        self.assertContains(response, 'class="about-breadcrumbs"', count=1)
        self.assertNotContains(response, 'class="partnership-kicker"')
        self.assertNotContains(response, 'class="partnership-card-arrow"')
        self.assertContains(response, "Направления сотрудничества")
        self.assertContains(response, "Франшиза")
        self.assertContains(response, "Производителям и поставщикам")
        self.assertContains(response, "Наши успехи — ваши возможности")
        self.assertContains(response, f'href="{reverse("business_clients")}">Корпоративным клиентам</a>')
        self.assertContains(response, "data-open-partnership-inquiry")
        self.assertContains(response, 'id="partnership-inquiry-modal"')
        self.assertContains(response, 'id="partnership-inquiry-subject"')
        self.assertContains(response, 'name="source" value="partnership"')
        self.assertContains(response, 'name="phone" type="tel"')
        self.assertContains(response, '<option value="Франшиза">Франшиза</option>')
        self.assertContains(response, '<option value="Реклама и сотрудничество">Реклама и сотрудничество</option>')
        self.assertContains(response, '<option value="Другое">Другое</option>')

    def test_business_clients_page_renders_its_own_content(self):
        response = self.client.get(reverse("business_clients"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<title>Корпоративным клиентам — Вкусно Да Сладко</title>")
        self.assertContains(response, 'data-feedback-source="business_clients"')
        self.assertContains(response, "Индивидуальные решения")
        self.assertContains(response, "Взаимодействие")
        self.assertContains(response, "Калькулятор заказа")

    def test_business_clients_breadcrumb_is_not_repeated_as_the_eyebrow(self):
        SitePageContent.objects.create(
            page=SitePageContent.Page.BUSINESS_CLIENTS,
            eyebrow="Главная / Корпоративным клиентам ",
            eyebrow_en="Home / Business clients ",
        )

        response = self.client.get(reverse("business_clients"))

        self.assertContains(response, 'class="about-breadcrumbs"', count=1)
        self.assertNotContains(response, 'class="business-clients-kicker"')

        page_content = SitePageContent.objects.get(
            page=SitePageContent.Page.BUSINESS_CLIENTS
        )
        page_content.eyebrow = "Подарки для бизнеса"
        page_content.save(update_fields=("eyebrow",))
        custom_eyebrow_response = self.client.get(reverse("business_clients"))
        self.assertNotContains(
            custom_eyebrow_response,
            'class="business-clients-kicker"',
        )

    def test_business_clients_page_does_not_repeat_configured_address(self):
        SitePageSection.objects.filter(
            page=SitePageSection.Page.BUSINESS_CLIENTS,
            group="contacts",
        ).delete()
        SitePageSection.objects.create(
            page=SitePageSection.Page.BUSINESS_CLIENTS,
            group="contacts",
            title="Телефон",
            title_en="Phone",
            value="+7 000 000-00-00",
            value_en="+7 000 000-00-00",
            url="tel:+70000000000",
            display_order=0,
        )
        SitePageSection.objects.create(
            page=SitePageSection.Page.BUSINESS_CLIENTS,
            group="contacts",
            title="E-mail",
            title_en="E-mail",
            value="info@example.com",
            value_en="info@example.com",
            url="mailto:info@example.com",
            display_order=1,
        )
        SitePageSection.objects.create(
            page=SitePageSection.Page.BUSINESS_CLIENTS,
            group="contacts",
            title="Адрес",
            title_en="Address",
            value="г. Москва, ул. Приморская, д. 10, стр. 1",
            value_en="Moscow, ul. Primorskaya, 10, bldg. 1",
            description="Бизнес-центр «Примор»",
            description_en="Business center «Primere»",
            display_order=2,
        )

        response = self.client.get(reverse("business_clients"))

        self.assertEqual(
            response.content.count(
                "г. Москва, ул. Приморская, д. 10, стр. 1".encode()
            ),
            1,
        )

    def test_footer_contact_information_uses_contact_page_details(self):
        SitePageSection.objects.filter(
            page=SitePageSection.Page.CONTACTS,
            group="details",
        ).delete()
        SitePageSection.objects.create(
            page=SitePageSection.Page.CONTACTS,
            group="details",
            title="Телефон",
            title_en="Phone",
            value="+7 999 111-22-33",
            value_en="+7 999 111-22-33",
            url="tel:+79991112233",
            display_order=0,
        )
        SitePageSection.objects.create(
            page=SitePageSection.Page.CONTACTS,
            group="details",
            title="E-mail",
            title_en="E-mail",
            value="footer@example.com",
            value_en="footer@example.com",
            url="mailto:footer@example.com",
            display_order=1,
        )
        SitePageSection.objects.create(
            page=SitePageSection.Page.CONTACTS,
            group="details",
            title="Адрес",
            title_en="Address",
            value="Новый адрес офиса",
            value_en="New office address",
            display_order=2,
        )

        response = self.client.get(reverse("home"))

        self.assertContains(response, "+7 999 111-22-33")
        self.assertContains(response, 'href="mailto:footer@example.com"')
        self.assertContains(response, "Новый адрес офиса")
        self.assertNotContains(response, "+7 800 123-45-67")

    def test_delivery_page_renders_methods_pickup_and_useful_information(self):
        response = self.client.get(reverse("delivery"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<title>Доставка и самовывоз — Вкусно Да Сладко</title>")
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
        self.assertContains(response, "<title>Варианты упаковки — Вкусно Да Сладко</title>")
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
        self.assertNotContains(response, "Подарки, созданные с душой")
        self.assertNotContains(response, "Внимание, которое объединяет")
        self.assertNotContains(response, 'class="hero-content"')
        self.assertNotContains(response, 'class="button button-light"')
        self.assertContains(response, 'class="hero-arrow hero-arrow-next"')
        self.assertContains(response, 'class="hero-dot is-active"')

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
        self.assertContains(response, "<h2>Наша продукция</h2>")
        self.assertNotContains(response, "Популярные наборы")
        self.assertContains(response, "Подарки компании")
        self.assertContains(response, "Праздничный набор")
        self.assertContains(response, "Скрытый товар")
        self.assertNotContains(response, '<span aria-hidden="true">↗</span>')
        self.assertNotContains(response, "Скрытая категория")
        self.assertNotContains(response, "Товар скрытой категории")
