from django.contrib.auth import get_user_model
from django.test import TestCase


User = get_user_model()


class AccountTests(TestCase):
    def test_registration_creates_user_and_logs_them_in(self):
        response = self.client.post(
            "/account/register/",
            {
                "username": "new_customer",
                "first_name": "Анна",
                "last_name": "Иванова",
                "email": "anna@example.com",
                "password1": "A-long-password-482!",
                "password2": "A-long-password-482!",
            },
        )

        self.assertRedirects(response, "/account/")
        user = User.objects.get(username="new_customer")
        self.assertEqual(user.email, "anna@example.com")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_registration_rejects_duplicate_email(self):
        User.objects.create_user(
            username="first_customer",
            email="taken@example.com",
            password="A-long-password-482!",
        )

        response = self.client.post(
            "/account/register/",
            {
                "username": "second_customer",
                "first_name": "",
                "last_name": "",
                "email": "TAKEN@example.com",
                "password1": "Another-long-password-583!",
                "password2": "Another-long-password-583!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Аккаунт с такой почтой уже существует.")
        self.assertFalse(User.objects.filter(username="second_customer").exists())

    def test_login_logout_and_protected_dashboard(self):
        user = User.objects.create_user(
            username="returning_customer",
            password="A-long-password-482!",
        )

        response = self.client.get("/account/")
        self.assertRedirects(response, "/account/login/?next=/account/")

        response = self.client.post(
            "/account/login/",
            {"username": user.username, "password": "A-long-password-482!"},
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
            },
        )

        self.assertRedirects(response, "/account/profile/")
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Мария")
        self.assertEqual(user.last_name, "Петрова")
        self.assertEqual(user.email, "maria@example.com")

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
            "/account/favorites/",
            "/account/addresses/",
            "/account/profile/",
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, f"/account/login/?next={url}")
