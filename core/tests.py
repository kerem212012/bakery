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
from .models import (
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
        self.assertEqual(response.context["form"].instance.pk, None)
        self.assertEqual(
            list(response.context["site_blocks"].values_list("title", flat=True)),
            ["First about block", "Second about block"],
        )
        self.assertContains(response, 'option value="about" selected')
        self.assertNotContains(response, "Catalog block")

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
        self.assertEqual(home_response.context["slide_formset"].total_form_count(), 3)
        self.assertEqual(
            home_response.context["slide_formset"].forms[1]["title"].value(),
            "Тёплые моменты в каждой детали",
        )

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

    def test_section_editor_hides_button_fields_but_keeps_nonbutton_values(self):
        admin_user = get_user_model().objects.create_superuser(
            username="section_field_visibility_admin",
            email="section-field-visibility@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)

        home_response = self.client.get(
            reverse("site_content_manager"),
            {"page": SitePageSection.Page.HOME},
        )
        about_response = self.client.get(
            reverse("site_content_manager"),
            {"page": SitePageSection.Page.ABOUT},
        )
        home_forms = {
            form.instance.group: form
            for form in home_response.context["section_formset"].forms
            if form.instance.pk
        }
        about_forms = {
            form.instance.group: form
            for form in about_response.context["section_formset"].forms
            if form.instance.pk
        }

        self.assertFalse(home_forms["home_about"].show_value_fields)
        self.assertFalse(home_forms["home_about"].show_url_field)
        self.assertIn("value", about_forms["stats"].fields)
        self.assertIn("value_en", about_forms["stats"].fields)
        self.assertFalse(about_forms["stats"].show_url_field)

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

    def test_page_picker_exposes_structured_content_for_every_static_page(self):
        admin_user = get_user_model().objects.create_superuser(
            username="all_page_sections_admin",
            email="all-page-sections-admin@example.com",
            password="test-pass-123",
        )
        self.client.force_login(admin_user)
        pages = (
            SitePageSection.Page.HOME,
            SitePageSection.Page.ABOUT,
            SitePageSection.Page.BUSINESS_CLIENTS,
            SitePageSection.Page.PARTNERSHIP,
            SitePageSection.Page.CONTACTS,
            SitePageSection.Page.DELIVERY,
            SitePageSection.Page.FAQ,
            SitePageSection.Page.FEEDBACK,
            SitePageSection.Page.PACKAGING,
            SitePageSection.Page.CATALOG,
            SitePageSection.Page.CATEGORIES,
        )

        for page in pages:
            with self.subTest(page=page):
                response = self.client.get(
                    reverse("site_content_manager"),
                    {"page": page},
                )
                self.assertEqual(response.status_code, 200)
                self.assertIsNotNone(response.context["section_formset"])
                self.assertContains(response, "Разделы и карточки страницы")

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

    def test_page_sections_save_and_render_structured_about_content(self):
        admin_user = get_user_model().objects.create_superuser(
            username="page_section_saver",
            email="page-section-saver@example.com",
            password="test-pass-123",
        )
        SitePageSection.objects.filter(page=SitePageSection.Page.ABOUT).delete()
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse("site_content_manager"),
            {
                "action": "save_page_sections",
                "page": SitePageSection.Page.ABOUT,
                "sections-TOTAL_FORMS": "1",
                "sections-INITIAL_FORMS": "0",
                "sections-MIN_NUM_FORMS": "0",
                "sections-MAX_NUM_FORMS": "1000",
                "sections-0-group": "promises",
                "sections-0-title": "Carefully selected ingredients",
                "sections-0-title_en": "Carefully selected ingredients",
                "sections-0-description": "Edited promise text",
                "sections-0-description_en": "Edited promise text",
                "sections-0-display_order": "0",
                "sections-0-is_active": "on",
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('site_content_manager')}?page=about",
        )
        section = SitePageSection.objects.get(page=SitePageSection.Page.ABOUT)
        self.assertEqual(section.group, "promises")
        about_response = self.client.get(reverse("about"))
        self.assertContains(about_response, "Carefully selected ingredients")
        self.assertContains(about_response, "Edited promise text")

    def test_page_section_editor_hides_button_text_and_url(self):
        admin_user = get_user_model().objects.create_superuser(
            username="page_section_button_editor",
            email="page-section-button-editor@example.com",
            password="test-password",
        )
        SitePageSection.objects.filter(page=SitePageSection.Page.HOME).delete()
        SitePageSection.objects.create(
            page=SitePageSection.Page.HOME,
            group="home_about",
            title="About our bakery",
        )
        self.client.force_login(admin_user)

        editor_response = self.client.get(
            reverse("site_content_manager"),
            {"page": SitePageSection.Page.HOME},
        )

        about_form = next(
            form
            for form in editor_response.context["section_formset"].forms
            if form.instance.group == "home_about"
        )
        self.assertFalse(about_form.show_value_fields)
        self.assertFalse(about_form.show_url_field)

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
        post_data = {
            "action": "save_home_slides",
            "page": SiteContentBlock.Page.HOME,
            "slides-TOTAL_FORMS": "3",
            "slides-INITIAL_FORMS": "0",
            "slides-MIN_NUM_FORMS": "0",
            "slides-MAX_NUM_FORMS": "1000",
        }
        for index, slide in enumerate(
            (
                {
                    "eyebrow": "Первая подпись",
                    "title": "Первый баннер",
                    "description": "Первое описание",
                    "button_text": "Первая кнопка",
                    "button_url": "#popular",
                },
                {
                    "eyebrow": "Вторая подпись",
                    "title": "Тёплые моменты теперь другие",
                    "description": "Описание второго баннера",
                    "button_text": "Открыть каталог",
                    "button_url": "/catalog/",
                },
                {
                    "eyebrow": "Третья подпись",
                    "title": "Третий баннер",
                    "description": "Третье описание",
                    "button_text": "Подробнее",
                    "button_url": "/about/",
                },
            )
        ):
            post_data.update(
                {
                    f"slides-{index}-eyebrow": slide["eyebrow"],
                    f"slides-{index}-eyebrow_en": f"Banner {index + 1}",
                    f"slides-{index}-title": slide["title"],
                    f"slides-{index}-title_en": f"Banner heading {index + 1}",
                    f"slides-{index}-description": slide["description"],
                    f"slides-{index}-description_en": f"Banner description {index + 1}",
                    f"slides-{index}-button_text": slide["button_text"],
                    f"slides-{index}-button_text_en": f"Button {index + 1}",
                    f"slides-{index}-button_url": slide["button_url"],
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
        home_response = self.client.get(reverse("home"))
        self.assertContains(home_response, "Тёплые моменты теперь другие")
        self.assertContains(home_response, "Описание второго баннера")
        self.assertContains(home_response, 'href="/catalog/"')

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

        block = SiteContentBlock.objects.get()
        edit_url = reverse("site_content_edit", args=(block.pk,))
        self.assertRedirects(response, edit_url)
        self.assertEqual(block.page, SiteContentBlock.Page.ABOUT)
        self.assertEqual(block.title, "Custom page heading")
        self.assertEqual(block.display_order, 2)
        edit_response = self.client.get(edit_url)
        self.assertEqual(edit_response.status_code, 200)
        self.assertContains(edit_response, 'option value="about" selected')
        about_response = self.client.get(reverse("about"))
        home_response = self.client.get(reverse("home"))
        self.assertContains(about_response, "Custom page heading")
        self.assertNotContains(home_response, "Custom page heading")

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
        self.assertIn(reverse("accounts:login"), response["Location"])

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
        self.assertNotContains(response, '<span aria-hidden="true">↗</span>')
        self.assertNotContains(response, "Скрытая категория")
        self.assertNotContains(response, "Товар скрытой категории")
