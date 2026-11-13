from io import BytesIO
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from catalog.models import Category, Product
from core.models import Preorder, PreorderContract

from .models import CustomerDeliveryAddress, CustomerProfile


User = get_user_model()


class AccountTests(TestCase):
    def test_english_order_pages_translate_account_status_and_catalog_items(self):
        user = User.objects.create_user(
            username="english_customer",
            email="english-customer@example.com",
            password=None,
        )
        category = Category.objects.create(
            name="Подарочные наборы",
            name_en="Gift sets",
        )
        product = Product.objects.create(
            name="Подарочный набор",
            name_en="English gift set",
            category=category,
        )
        order = Preorder.objects.create(
            user=user,
            name="Anna",
            email=user.email,
            phone="+7 900 000-00-00",
            configuration={
                "items": [
                    {
                        "product_id": product.pk,
                        "name": product.name,
                        "quantity": 2,
                        "size": "8",
                        "coating": "painting",
                        "dough": "classic",
                        "packaging": "gift_box",
                        "unit_price": "100.00",
                    }
                ],
                "delivery": "pickup",
                "payment": "card",
            },
            unit_price="100.00",
            discount_percent=0,
            delivery_cost="0.00",
            total_price="200.00",
            status=Preorder.Status.PRODUCTION,
            consent_given=True,
        )
        self.client.force_login(user)
        self.client.post(
            reverse("set_language"),
            {"language": "en", "next": reverse("accounts:orders")},
        )

        orders_page = self.client.get(reverse("accounts:orders"))
        self.assertContains(orders_page, "Your orders")
        self.assertContains(orders_page, "1 order")
        self.assertContains(orders_page, "English gift set × 2")
        self.assertContains(orders_page, "In production")
        self.assertContains(orders_page, "Approximate delivery date: To be confirmed")

        detail_page = self.client.get(
            reverse("accounts:order_detail", args=[order.pk])
        )
        self.assertContains(detail_page, "Order progress")
        self.assertContains(detail_page, "Hand-painted icing")
        self.assertContains(detail_page, "Pickup")

    def test_orders_page_shows_only_orders_owned_by_the_logged_in_user(self):
        user = User.objects.create_user(
            username="order_customer",
            email="order-customer@example.com",
            password="A-long-password-482!",
        )
        other_user = User.objects.create_user(
            username="other_customer",
            email="other-customer@example.com",
            password="A-long-password-583!",
        )
        order_values = {
            "name": "Анна",
            "email": "order-customer@example.com",
            "phone": "+7 900 000-00-00",
            "configuration": {
                "items": [{"name": "Подарочный набор", "quantity": 2}],
                "delivery": "pickup",
                "payment": "card",
            },
            "unit_price": "1490.00",
            "discount_percent": 0,
            "delivery_cost": "0.00",
            "total_price": "2980.00",
            "consent_given": True,
        }
        order = Preorder.objects.create(user=user, **order_values)
        Preorder.objects.create(
            user=other_user,
            **{**order_values, "email": "other-customer@example.com"},
        )
        self.client.force_login(user)

        response = self.client.get(reverse("accounts:orders"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Заказ #{order.pk}")
        self.assertContains(response, "Подарочный набор × 2")
        self.assertContains(response, "1 заказ")
        self.assertNotContains(response, "Заказ #2")
        self.assertContains(response, "Приблизительный срок доставки: Уточняется")

    def test_dashboard_shows_current_user_order_count_and_recent_order(self):
        user = User.objects.create_user(
            username="dashboard_customer",
            email="dashboard-customer@example.com",
            password="A-long-password-482!",
        )
        order = Preorder.objects.create(
            user=user,
            name="Анна",
            email=user.email,
            phone="+7 900 000-00-00",
            configuration={"quantity": 4, "size": "8"},
            unit_price="100.00",
            discount_percent=0,
            delivery_cost="700.00",
            total_price="1100.00",
            consent_given=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("accounts:dashboard"))

        self.assertContains(response, "Мои заказы")
        self.assertContains(response, "1 заказ")
        self.assertContains(response, f"Заказ #{order.pk}")
        self.assertContains(response, "4 шт. · 8 см")
        self.assertContains(response, "Приблизительный срок доставки: Уточняется")
        self.assertContains(response, "За последний год")
        self.assertContains(response, "Общая сумма")
        self.assertContains(response, "Ближайшая доставка")

    def test_dashboard_overview_metrics_use_current_user_orders_and_nearest_delivery(self):
        user = User.objects.create_user(
            username="dashboard_metrics_customer",
            email="dashboard-metrics@example.com",
            password="A-long-password-482!",
        )
        order_values = {
            "user": user,
            "name": "Анна",
            "email": user.email,
            "phone": "+7 900 000-00-00",
            "configuration": {"quantity": 1},
            "unit_price": "100.00",
            "discount_percent": 0,
            "delivery_cost": "0.00",
            "consent_given": True,
        }
        recent_order = Preorder.objects.create(
            **order_values,
            total_price="100.00",
            delivery_date=timezone.localdate() + timedelta(days=5),
        )
        next_delivery_order = Preorder.objects.create(
            **order_values,
            total_price="250.00",
            delivery_date=timezone.localdate() + timedelta(days=2),
        )
        old_order = Preorder.objects.create(
            **order_values,
            total_price="500.00",
        )
        Preorder.objects.filter(pk=old_order.pk).update(
            created_at=timezone.now() - timedelta(days=400)
        )
        Preorder.objects.create(
            **order_values,
            total_price="900.00",
            delivery_date=timezone.localdate() - timedelta(days=1),
        )
        Preorder.objects.create(
            **order_values,
            total_price="1200.00",
            delivery_date=timezone.localdate() + timedelta(days=1),
            status=Preorder.Status.CANCELLED,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("accounts:dashboard"))

        self.assertEqual(response.context["year_orders_count"], 4)
        self.assertEqual(response.context["total_spent"], Decimal("2950.00"))
        self.assertEqual(response.context["next_delivery"].pk, next_delivery_order.pk)
        self.assertNotEqual(response.context["next_delivery"].pk, recent_order.pk)
        self.assertContains(response, f"Заказ №{next_delivery_order.pk}")
        self.assertContains(response, "Главная")
        self.assertContains(response, 'aria-current="page"')

    def test_order_detail_shows_items_and_production_tracking(self):
        user = User.objects.create_user(
            username="tracking_customer",
            email="tracking-customer@example.com",
            password="A-long-password-482!",
        )
        order = Preorder.objects.create(
            user=user,
            name="Анна",
            email=user.email,
            phone="+7 900 000-00-00",
            address="Москва, ул. Примерная, 1",
            configuration={
                "items": [
                    {
                        "name": "Подарочный набор",
                        "quantity": 2,
                        "size": "8",
                        "unit_price": "1490.00",
                    },
                ],
                "delivery": "moscow",
                "payment": "card",
            },
            unit_price="1490.00",
            discount_percent=0,
            delivery_cost="700.00",
            total_price="3680.00",
            status=Preorder.Status.PRODUCTION,
            consent_given=True,
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse("accounts:order_detail", args=[order.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Состав заказа")
        self.assertContains(response, "Подарочный набор")
        self.assertContains(response, "В производстве")
        self.assertContains(response, "Доставка по Москве")
        self.assertContains(response, 'class="account-order-step is-complete"')
        self.assertContains(response, 'class="account-order-step is-current"')

    def test_customer_cannot_view_another_users_order_detail(self):
        user = User.objects.create_user(
            username="order_owner",
            email="order-owner@example.com",
            password="A-long-password-482!",
        )
        other_user = User.objects.create_user(
            username="order_viewer",
            email="order-viewer@example.com",
            password="A-long-password-583!",
        )
        order = Preorder.objects.create(
            user=user,
            name="Анна",
            email=user.email,
            phone="+7 900 000-00-00",
            configuration={"quantity": 1},
            unit_price="100.00",
            discount_percent=0,
            delivery_cost="700.00",
            total_price="800.00",
            consent_given=True,
        )
        self.client.force_login(other_user)

        response = self.client.get(
            reverse("accounts:order_detail", args=[order.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_customer_can_save_delivery_address_for_future_orders(self):
        user = User.objects.create_user(
            username="address_customer",
            email="address-customer@example.com",
            password="A-long-password-482!",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("accounts:addresses"),
            {"delivery_address": "Москва, ул. Примерная, 12, кв. 4"},
        )

        self.assertRedirects(response, reverse("accounts:addresses"))
        self.assertEqual(
            user.customer_profile.delivery_address,
            "Москва, ул. Примерная, 12, кв. 4",
        )
        self.assertContains(
            self.client.get(reverse("accounts:addresses")),
            "Москва, ул. Примерная, 12, кв. 4",
        )

    def test_customer_can_save_multiple_addresses_and_choose_a_default(self):
        user = User.objects.create_user(
            username="multiple_address_customer",
            email="multiple-address@example.com",
            password="A-long-password-482!",
        )
        self.client.force_login(user)
        addresses_url = reverse("accounts:addresses")
        first_address = "Москва, ул. Первая, 1"
        second_address = "Москва, ул. Вторая, 2"

        self.client.post(addresses_url, {"delivery_address": first_address})
        self.client.post(addresses_url, {"delivery_address": second_address})

        saved_addresses = list(user.customer_profile.delivery_addresses.all())
        self.assertEqual(len(saved_addresses), 2)
        self.assertEqual(
            [address.delivery_address for address in saved_addresses],
            [first_address, second_address],
        )
        first_saved_address = next(
            address for address in saved_addresses
            if address.delivery_address == first_address
        )
        second_saved_address = next(
            address for address in saved_addresses
            if address.delivery_address == second_address
        )
        self.assertTrue(first_saved_address.is_default)
        self.assertFalse(second_saved_address.is_default)

        self.client.post(
            addresses_url,
            {"action": "default", "address_id": second_saved_address.pk},
        )

        first_saved_address.refresh_from_db()
        second_saved_address.refresh_from_db()
        user.customer_profile.refresh_from_db()
        self.assertFalse(first_saved_address.is_default)
        self.assertTrue(second_saved_address.is_default)
        self.assertEqual(user.customer_profile.delivery_address, second_address)
        response = self.client.get(addresses_url)
        self.assertContains(response, first_address)
        self.assertContains(response, second_address)

        self.client.post(
            addresses_url,
            {"action": "delete", "address_id": second_saved_address.pk},
        )

        first_saved_address.refresh_from_db()
        user.customer_profile.refresh_from_db()
        self.assertTrue(first_saved_address.is_default)
        self.assertEqual(user.customer_profile.delivery_address, first_address)
        self.assertFalse(
            CustomerDeliveryAddress.objects.filter(pk=second_saved_address.pk).exists()
        )

    def test_registration_hides_customer_type_and_shows_business_fields(self):
        response = self.client.get("/account/register/")

        self.assertNotContains(response, "Физическое лицо")
        self.assertNotContains(response, "Тип клиента")
        self.assertNotIn("customer_type", response.context["form"].fields)
        self.assertContains(response, 'id="registration-business-fields"')
        self.assertNotContains(response, 'id="registration-business-fields" hidden')
        self.assertNotContains(response, "Название организации")
        self.assertNotContains(response, "Контактное лицо")
        self.assertNotContains(response, "Юридический адрес")
        self.assertNotIn("username", response.context["form"].fields)
        self.assertContains(response, reverse("terms"))
        self.assertContains(response, reverse("personal_data_consent"))
        html = response.content.decode()
        self.assertLess(html.index('name="inn"'), html.index('name="phone"'))
        self.assertLess(
            html.index('name="password1"'),
            html.index('name="password2"'),
        )
        self.assertLess(
            html.index('name="password2"'),
            html.index('name="agreement_accepted"'),
        )
        self.assertLess(
            html.index('name="agreement_accepted"'),
            html.index('name="personal_data_consent"'),
        )
        self.assertLess(
            html.index('name="personal_data_consent"'),
            html.index('class="button button-dark auth-submit"'),
        )

    def test_legal_documents_are_available(self):
        documents = (
            ("privacy_policy", "Политика обработки персональных данных"),
            ("personal_data_consent", "Согласие на обработку персональных данных"),
            ("terms", "Пользовательское соглашение"),
            ("public_offer", "Публичная оферта"),
        )
        for route_name, title in documents:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, title)
                self.assertContains(response, "Проект документа")

    def test_registration_creates_user_and_logs_them_in(self):
        response = self.client.post(
            "/account/register/",
            {
                "first_name": "Анна",
                "last_name": "Иванова",
                "email": "anna@example.com",
                "password1": "A-long-password-482!",
                "password2": "A-long-password-482!",
                "phone": "+7 900 000-00-00",
                "inn": "1234567890",
                "customer_type": CustomerProfile.CustomerType.LEGAL_ENTITY,
                "agreement_accepted": "on",
                "personal_data_consent": "on",
            },
        )

        self.assertRedirects(response, "/account/")
        user = User.objects.get(email="anna@example.com")
        self.assertEqual(user.username, "anna")
        self.assertEqual(user.email, "anna@example.com")
        self.assertEqual(
            user.customer_profile.customer_type,
            CustomerProfile.CustomerType.LEGAL_ENTITY,
        )
        self.assertEqual(user.customer_profile.phone, "+7 900 000-00-00")
        self.assertIsNotNone(user.customer_profile.terms_accepted_at)
        self.assertEqual(
            user.customer_profile.terms_accepted_at,
            user.customer_profile.personal_data_consent_at,
        )
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_registration_returns_to_next_and_preserves_cart_session(self):
        category = Category.objects.create(name="Подарки")
        product = Product.objects.create(name="Пряник", category=category)
        session = self.client.session
        item_id = f"{product.pk}:8:painting:classic:gift_box"
        session["cart"] = {
            item_id: {
                "product_id": product.pk,
                "quantity": 1,
                "size": "8",
                "coating": "painting",
                "dough": "classic",
                "packaging": "gift_box",
            }
        }
        session.save()
        cart_url = reverse("catalog:cart")

        response = self.client.post(
            reverse("accounts:register"),
            {
                "next": cart_url,
                "email": "returning-cart@example.com",
                "password1": "A-long-password-482!",
                "password2": "A-long-password-482!",
                "customer_type": CustomerProfile.CustomerType.LEGAL_ENTITY,
                "inn": "1234567890",
                "phone": "+7 900 000-00-00",
                "agreement_accepted": "on",
                "personal_data_consent": "on",
            },
        )

        self.assertRedirects(response, cart_url)
        self.assertEqual(self.client.session["cart"][item_id]["quantity"], 1)
        self.assertEqual(
            int(self.client.session["_auth_user_id"]),
            User.objects.get(email="returning-cart@example.com").pk,
        )

    def test_only_order_owner_and_order_managers_can_access_contract(self):
        user = User.objects.create_user(
            username="contract_owner",
            email="contract-owner@example.com",
            password="A-long-password-482!",
        )
        other_user = User.objects.create_user(
            username="not_contract_owner",
            email="not-contract-owner@example.com",
            password="A-long-password-583!",
        )
        order = Preorder.objects.create(
            user=user,
            name="Contract owner",
            email=user.email,
            phone="+7 900 000-00-00",
            configuration={"items": []},
            unit_price="100.00",
            discount_percent=0,
            delivery_cost="0.00",
            total_price="100.00",
            payment_status=Preorder.PaymentStatus.PAID,
            consent_given=True,
        )
        contract = PreorderContract.objects.create(
            preorder=order,
            file=SimpleUploadedFile(
                "signed.pdf",
                b"%PDF-1.4 private contract",
                content_type="application/pdf",
            ),
        )
        self.addCleanup(contract.file.delete, save=False)
        contract_url = reverse("accounts:order_contract", args=[order.pk])

        self.client.force_login(other_user)
        self.assertEqual(self.client.get(contract_url).status_code, 404)

        self.client.force_login(user)
        detail_response = self.client.get(
            reverse("accounts:order_detail", args=[order.pk])
        )
        self.assertContains(detail_response, "Открыть PDF")
        self.assertContains(detail_response, "Оплачено")

        response = self.client.get(contract_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(b"".join(response.streaming_content), b"%PDF-1.4 private contract")
        self.assertNotIn("attachment", response.get("Content-Disposition", ""))
        for close_resource in response._resource_closers:
            close_resource()

    def test_customer_cannot_view_contract_until_payment_is_marked_paid(self):
        user = User.objects.create_user(
            username="pending_contract_owner",
            email="pending-contract@example.com",
            password="A-long-password-482!",
        )
        order = Preorder.objects.create(
            user=user,
            name="Pending contract owner",
            email=user.email,
            phone="+7 900 000-00-00",
            configuration={"items": []},
            unit_price="100.00",
            discount_percent=0,
            delivery_cost="0.00",
            total_price="100.00",
            payment_status=Preorder.PaymentStatus.PENDING,
            consent_given=True,
        )
        contract = PreorderContract.objects.create(
            preorder=order,
            file=SimpleUploadedFile("signed.pdf", b"%PDF-1.4 private contract"),
        )
        self.addCleanup(contract.file.delete, save=False)
        self.client.force_login(user)
        detail_url = reverse("accounts:order_detail", args=[order.pk])
        contract_url = reverse("accounts:order_contract", args=[order.pk])

        self.assertNotContains(self.client.get(detail_url), "Открыть PDF")
        self.assertEqual(self.client.get(contract_url).status_code, 404)

        order.payment_status = Preorder.PaymentStatus.PAID
        order.save(update_fields=("payment_status",))
        self.assertContains(self.client.get(detail_url), "Открыть PDF")
        response = self.client.get(contract_url)
        self.assertEqual(response.status_code, 200)
        for close_resource in response._resource_closers:
            close_resource()

        response = self.client.get(f"{contract_url}?download=1")
        self.assertIn("attachment", response["Content-Disposition"])
        for close_resource in response._resource_closers:
            close_resource()

    def test_registration_requires_separate_terms_and_data_consent(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "email": "no-consent@example.com",
                "password1": "A-long-password-482!",
                "password2": "A-long-password-482!",
                "customer_type": CustomerProfile.CustomerType.INDIVIDUAL,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="no-consent@example.com").exists())
        self.assertIn(
            "Необходимо принять пользовательское соглашение.",
            response.context["form"]["agreement_accepted"].errors,
        )
        self.assertIn(
            "Необходимо дать согласие на обработку персональных данных.",
            response.context["form"]["personal_data_consent"].errors,
        )

    def test_legal_entity_registration_requires_tax_and_contact_fields(self):
        response = self.client.post(
            "/account/register/",
            {
                "email": "legal@example.com",
                "password1": "A-long-password-482!",
                "password2": "A-long-password-482!",
                "customer_type": CustomerProfile.CustomerType.LEGAL_ENTITY,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="legal@example.com").exists())
        for field in ("inn", "phone"):
            with self.subTest(field=field):
                self.assertIn("Обязательное поле для юридического лица.", response.context["form"][field].errors)
        self.assertFalse(response.context["form"]["kpp"].errors)

    def test_legal_entity_registration_saves_remaining_details(self):
        response = self.client.post(
            "/account/register/",
            {
                "email": "legal@example.com",
                "password1": "A-long-password-482!",
                "password2": "A-long-password-482!",
                "customer_type": CustomerProfile.CustomerType.LEGAL_ENTITY,
                "agreement_accepted": "on",
                "personal_data_consent": "on",
                "inn": "1234567890",
                "phone": "+7 900 123-45-67",
            },
        )

        self.assertRedirects(response, "/account/")
        profile = CustomerProfile.objects.get(user__email="legal@example.com")
        self.assertEqual(profile.customer_type, CustomerProfile.CustomerType.LEGAL_ENTITY)
        self.assertEqual(profile.inn, "1234567890")
        self.assertEqual(profile.kpp, "")
        self.assertEqual(profile.phone, "+7 900 123-45-67")

    def test_legal_entity_registration_validates_tax_identifier_formats(self):
        response = self.client.post(
            "/account/register/",
            {
                "email": "invalid-legal@example.com",
                "password1": "A-long-password-482!",
                "password2": "A-long-password-482!",
                "customer_type": CustomerProfile.CustomerType.LEGAL_ENTITY,
                "inn": "123",
                "kpp": "12",
                "phone": "+7 900 123-45-67",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="invalid-legal@example.com").exists())
        self.assertContains(response, "Введите 10 или 12 цифр.")
        self.assertContains(response, "Введите 9 цифр.")

    def test_admin_can_export_selected_legal_entities_as_xlsx(self):
        admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="A-long-password-482!",
        )
        legal_user = User.objects.create_user(
            username="legal_export",
            email="legal-export@example.com",
        )
        CustomerProfile.objects.create(
            user=legal_user,
            customer_type=CustomerProfile.CustomerType.LEGAL_ENTITY,
            inn="1234567890",
            kpp="123456789",
            phone="+7 900 123-45-67",
        )
        individual_user = User.objects.create_user(username="individual_export")
        individual_profile = CustomerProfile.objects.create(user=individual_user)
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse("admin:user_customerprofile_changelist"),
            {
                "action": "export_legal_entities_xlsx",
                "_selected_action": [str(legal_user.customer_profile.pk), str(individual_profile.pk)],
                "index": "0",
            },
        )

        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        workbook = load_workbook(BytesIO(response.content), read_only=True)
        rows = list(workbook.active.iter_rows(values_only=True))
        self.assertEqual(rows[0][0:4], ("Телефон", "ИНН", "КПП", "Email"))
        self.assertEqual(len(rows), 2)

    def test_non_staff_users_cannot_access_customer_admin(self):
        response = self.client.get(reverse("admin:user_customerprofile_changelist"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_registration_rejects_duplicate_email(self):
        User.objects.create_user(
            username="first_customer",
            email="taken@example.com",
            password="A-long-password-482!",
        )

        response = self.client.post(
            "/account/register/",
            {
                "first_name": "",
                "last_name": "",
                "email": "TAKEN@example.com",
                "password1": "Another-long-password-583!",
                "password2": "Another-long-password-583!",
                "customer_type": CustomerProfile.CustomerType.INDIVIDUAL,
                "agreement_accepted": "on",
                "personal_data_consent": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Аккаунт с такой почтой уже существует.")
        self.assertEqual(User.objects.filter(email__iexact="taken@example.com").count(), 1)

    def test_login_logout_and_protected_dashboard(self):
        user = User.objects.create_user(
            username="returning_customer",
            email="returning@example.com",
            password="A-long-password-482!",
        )

        response = self.client.get("/account/")
        self.assertRedirects(response, "/account/login/?next=/account/")

        response = self.client.post(
            "/account/login/",
            {"username": user.email.upper(), "password": "A-long-password-482!"},
        )
        self.assertRedirects(response, "/account/")
        self.assertContains(self.client.get("/account/"), "Личный кабинет")

        response = self.client.post("/account/logout/")
        self.assertRedirects(response, "/")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_dashboard_saves_profile_details(self):
        user = User.objects.create_user(
            username="profile_customer",
            email="before@example.com",
            password="A-long-password-482!",
        )
        self.client.force_login(user)

        response = self.client.post(
            "/account/profile/",
            {
                "profile-first_name": "Мария",
                "profile-last_name": "Петрова",
                "profile-email": "maria@example.com",
                "profile-phone": "+7 900 000-00-00",
            },
        )

        self.assertRedirects(response, "/account/profile/")
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Мария")
        self.assertEqual(user.last_name, "Петрова")
        self.assertEqual(user.email, "maria@example.com")
        self.assertEqual(user.customer_profile.phone, "+7 900 000-00-00")

        profile_response = self.client.get("/account/profile/")
        self.assertContains(profile_response, "Телефон")
        self.assertContains(profile_response, 'name="profile-phone"')
        self.assertContains(profile_response, 'value="+7 900 000-00-00"')
        self.assertContains(profile_response, 'name="password-old_password"')
        self.assertContains(profile_response, 'name="password-new_password1"')
        self.assertContains(profile_response, 'name="password-new_password2"')

    def test_profile_password_can_be_changed_without_signing_out(self):
        user = User.objects.create_user(
            username="password_change_customer",
            email="password-change@example.com",
            password="A-long-password-482!",
        )
        self.client.force_login(user)

        response = self.client.post(
            "/account/profile/",
            {
                "action": "change_password",
                "password-old_password": "A-long-password-482!",
                "password-new_password1": "An-even-longer-password-583!",
                "password-new_password2": "An-even-longer-password-583!",
            },
        )

        self.assertRedirects(response, "/account/profile/")
        user.refresh_from_db()
        self.assertTrue(user.check_password("An-even-longer-password-583!"))
        self.assertEqual(
            self.client.session["_auth_user_id"],
            str(user.pk),
        )

    def test_profile_password_change_requires_the_current_password(self):
        user = User.objects.create_user(
            username="password_change_invalid_customer",
            email="password-change-invalid@example.com",
            password="A-long-password-482!",
        )
        self.client.force_login(user)

        response = self.client.post(
            "/account/profile/",
            {
                "action": "change_password",
                "password-old_password": "incorrect-current-password",
                "password-new_password1": "An-even-longer-password-583!",
                "password-new_password2": "An-even-longer-password-583!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("old_password", response.context["password_form"].errors)
        user.refresh_from_db()
        self.assertTrue(user.check_password("A-long-password-482!"))

    def test_account_sections_have_distinct_pages_and_active_navigation(self):
        user = User.objects.create_user(
            username="section_customer",
            password="A-long-password-482!",
        )
        self.client.force_login(user)

        pages = (
            ("/account/", "Личный кабинет", "/account/orders/"),
            ("/account/orders/", "Мои заказы", "/account/favorites/"),
            ("/account/favorites/", "Избранное", "/account/addresses/"),
            ("/account/addresses/", "Адрес доставки", "/account/profile/"),
            ("/account/profile/", "Мои данные", "/account/"),
        )
        for url, heading, next_page in pages:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f"<h1>{heading}</h1>", html=True)
                self.assertContains(response, f'href="{next_page}"')

    def test_account_sections_require_authentication(self):
        for url in (
            "/account/orders/",
            "/account/addresses/",
            "/account/profile/",
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, f"/account/login/?next={url}")
