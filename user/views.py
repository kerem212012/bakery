from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from catalog.favorites import get_favorite_ids
from catalog.models import Product

from .forms import AccountProfileForm, RegistrationForm


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Аккаунт создан. Добро пожаловать!")
        return redirect("accounts:dashboard")

    return render(request, "user/register.html", {"form": form})


@login_required
def dashboard(request):
    return render(request, "user/dashboard.html")


@login_required
def orders(request):
    return render(
        request,
        "user/section.html",
        {
            "account_active": "orders",
            "section_key": "orders",
            "section_title": "Мои заказы",
            "section_intro": "История ваших покупок и статусы заказов.",
        },
    )


def favorites(request):
    favorites = Product.objects.filter(
        pk__in=get_favorite_ids(request),
        is_active=True,
        category__is_active=True,
    ).select_related("category")
    return render(
        request,
        "user/favorites.html",
        {"favorites": favorites},
    )


@login_required
def addresses(request):
    return render(
        request,
        "user/section.html",
        {
            "account_active": "addresses",
            "section_key": "addresses",
            "section_title": "Адрес доставки",
            "section_intro": "Адреса для будущих заказов.",
        },
    )


@login_required
def profile(request):
    form = AccountProfileForm(
        request.POST or None,
        instance=request.user,
        prefix="profile",
    )
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Данные профиля сохранены.")
            return redirect("accounts:profile")
        messages.error(request, "Проверьте данные профиля и попробуйте ещё раз.")

    return render(
        request,
        "user/profile.html",
        {"account_active": "profile", "profile_form": form},
    )
