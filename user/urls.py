from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from .forms import LoginForm
from . import views

app_name = "accounts"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="user/login.html",
            authentication_form=LoginForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("register/", views.register, name="register"),
    path("verify-email/<uidb64>/<token>/", views.verify_email, name="verify_email"),
    path("verification-sent/", views.email_verification_sent, name="email_verification_sent"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="user/password_reset_form.html",
            email_template_name="user/password_reset_email.txt",
            subject_template_name="user/password_reset_subject.txt",
            success_url=reverse_lazy("accounts:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="user/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="user/password_reset_confirm.html",
            success_url=reverse_lazy("accounts:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="user/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
    path("", views.dashboard, name="dashboard"),
    path("orders/", views.orders, name="orders"),
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),
    path("orders/<int:order_id>/contract/", views.order_contract, name="order_contract"),
    path(
        "orders/<int:order_id>/contracts/<int:contract_id>/",
        views.order_contract,
        name="order_contract_file",
    ),
    path("favorites/", views.favorites, name="favorites"),
    path("addresses/", views.addresses, name="addresses"),
    path("profile/", views.profile, name="profile"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
