from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from catalog.cart_forms import (
    COATING_OPTIONS,
    DOUGH_OPTIONS,
    PACKAGING_OPTIONS,
    localized_cart_options,
)
from catalog.favorites import get_favorite_ids
from catalog.models import Product
from core.calculator import DELIVERY_CHOICES, PAYMENT_CHOICES, localized_choices
from core.models import Preorder

from .forms import AccountProfileForm, DeliveryAddressForm, RegistrationForm
from .models import CustomerProfile


def _orders_count_label(count, language_code="ru"):
    if language_code == "en":
        return f"{count} {'order' if count == 1 else 'orders'}"
    last_two_digits = count % 100
    last_digit = count % 10
    if 11 <= last_two_digits <= 14:
        noun = "заказов"
    elif last_digit == 1:
        noun = "заказ"
    elif 2 <= last_digit <= 4:
        noun = "заказа"
    else:
        noun = "заказов"
    return f"{count} {noun}"


def _order_row(order, language_code="ru"):
    configuration = order.configuration if isinstance(order.configuration, dict) else {}
    items = configuration.get("items")
    if isinstance(items, list) and items:
        order_items = [item for item in items if isinstance(item, dict)]
        if language_code == "en":
            product_ids = [
                item.get("product_id")
                for item in order_items
                if isinstance(item.get("product_id"), int)
            ]
            products_by_id = {
                product.pk: product
                for product in Product.objects.filter(pk__in=product_ids)
            }
        else:
            products_by_id = {}
        summary = ", ".join(
            f'{products_by_id[item["product_id"]].localized_name if item.get("product_id") in products_by_id else item.get("name", "Product" if language_code == "en" else "Товар")} × {item.get("quantity", 1)}'
            for item in order_items
        )
        item_count = sum(
            item.get("quantity", 1)
            for item in items
            if isinstance(item, dict) and isinstance(item.get("quantity", 1), int)
        )
    else:
        quantity_label = "pcs" if language_code == "en" else "шт."
        details = [f'{configuration.get("quantity", 1)} {quantity_label}']
        if configuration.get("size"):
            size_unit = "cm" if language_code == "en" else "см"
            details.append(f'{configuration["size"]} {size_unit}')
        summary = " · ".join(details)
        item_count = configuration.get("quantity", 1)
    status_labels = {
        "new": "Received",
        "contacted": "Confirmed",
        "confirmed": "Confirmed",
        "production": "In production",
        "shipping": "On the way",
        "completed": "Delivered",
        "cancelled": "Cancelled",
    }
    return {
        "order": order,
        "summary": summary,
        "item_count": item_count,
        "status_label": (
            status_labels.get(order.status, order.get_status_display())
            if language_code == "en"
            else order.get_status_display()
        ),
    }


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        message = (
            "Your account has been created. Welcome!"
            if request.LANGUAGE_CODE == "en"
            else "Аккаунт создан. Добро пожаловать!"
        )
        messages.success(request, message)
        return redirect("accounts:dashboard")

    return render(request, "user/register.html", {"form": form})


@login_required
def dashboard(request):
    orders = request.user.preorders.all()
    orders_count = orders.count()
    recent_orders = [_order_row(order, request.LANGUAGE_CODE) for order in orders[:3]]
    saved_address = CustomerProfile.objects.filter(user=request.user).values_list(
        "delivery_address", flat=True
    ).first()
    return render(
        request,
        "user/dashboard.html",
        {
            "orders_count": orders_count,
            "orders_count_label": _orders_count_label(orders_count, request.LANGUAGE_CODE),
            "recent_orders": recent_orders,
            "saved_address_label": (
                ("Saved" if request.LANGUAGE_CODE == "en" else "Сохранён")
                if saved_address
                else "—"
            ),
        },
    )


@login_required
def orders(request):
    user_orders = request.user.preorders.all()
    orders_count = user_orders.count()
    return render(
        request,
        "user/section.html",
        {
            "account_active": "orders",
            "section_key": "orders",
            "section_title": "My orders" if request.LANGUAGE_CODE == "en" else "Мои заказы",
            "section_intro": (
                "Your purchase history and order statuses."
                if request.LANGUAGE_CODE == "en"
                else "История ваших покупок и статусы заказов."
            ),
            "order_rows": [
                _order_row(order, request.LANGUAGE_CODE)
                for order in user_orders
            ],
            "orders_count": orders_count,
            "orders_count_label": _orders_count_label(orders_count, request.LANGUAGE_CODE),
        },
    )


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Preorder,
        pk=order_id,
        user=request.user,
    )
    configuration = order.configuration if isinstance(order.configuration, dict) else {}
    configured_items = configuration.get("items")
    items = []
    coating_labels = dict(localized_cart_options(COATING_OPTIONS, "coating"))
    dough_labels = dict(localized_cart_options(DOUGH_OPTIONS, "dough"))
    packaging_labels = dict(localized_cart_options(PACKAGING_OPTIONS, "packaging"))
    if isinstance(configured_items, list) and configured_items:
        for configured_item in configured_items:
            if not isinstance(configured_item, dict):
                continue
            quantity = configured_item.get("quantity", 1)
            if not isinstance(quantity, int) or quantity < 1:
                quantity = 1
            try:
                unit_price = Decimal(str(configured_item.get("unit_price", order.unit_price)))
            except (InvalidOperation, TypeError, ValueError):
                unit_price = order.unit_price
            product = (
                Product.objects.filter(pk=configured_item.get("product_id")).first()
                if request.LANGUAGE_CODE == "en"
                and isinstance(configured_item.get("product_id"), int)
                else None
            )
            items.append(
                {
                    "name": (
                        product.localized_name
                        if product
                        else configured_item.get(
                            "name",
                            "Product" if request.LANGUAGE_CODE == "en" else "Товар",
                        )
                    ),
                    "quantity": quantity,
                    "size": configured_item.get("size", ""),
                    "coating": coating_labels.get(
                        configured_item.get("coating", ""),
                        configured_item.get("coating", ""),
                    ),
                    "dough": dough_labels.get(
                        configured_item.get("dough", ""),
                        configured_item.get("dough", ""),
                    ),
                    "packaging": packaging_labels.get(
                        configured_item.get("packaging", ""),
                        configured_item.get("packaging", ""),
                    ),
                    "unit_price": unit_price,
                    "line_total": unit_price * quantity,
                }
            )
    else:
        quantity = configuration.get("quantity", 1)
        if not isinstance(quantity, int) or quantity < 1:
            quantity = 1
        items.append(
            {
                "name": (
                    "Custom order"
                    if request.LANGUAGE_CODE == "en"
                    else "Индивидуальный заказ"
                ),
                "quantity": quantity,
                "size": configuration.get("size", ""),
                "coating": configuration.get("coating", ""),
                "dough": configuration.get("flavor", ""),
                "packaging": configuration.get("packaging", ""),
                "unit_price": order.unit_price,
                "line_total": order.unit_price * quantity,
            }
        )

    status_stages = (
        (
            (Preorder.Status.NEW, "Received"),
            (Preorder.Status.CONTACTED, "Confirmed"),
            (Preorder.Status.PRODUCTION, "In production"),
            (Preorder.Status.SHIPPING, "On the way"),
            (Preorder.Status.COMPLETED, "Delivered"),
        )
        if request.LANGUAGE_CODE == "en"
        else (
            (Preorder.Status.NEW, "Принят"),
            (Preorder.Status.CONTACTED, "Подтверждён"),
            (Preorder.Status.PRODUCTION, "В производстве"),
            (Preorder.Status.SHIPPING, "В пути"),
            (Preorder.Status.COMPLETED, "Доставлен"),
        )
    )
    legacy_status = {
        "contacted": Preorder.Status.CONTACTED,
        "completed": Preorder.Status.COMPLETED,
    }.get(order.status, order.status)
    current_stage = next(
        (index for index, (status, _) in enumerate(status_stages) if status == legacy_status),
        0,
    )
    delivery_label = dict(
        localized_choices(DELIVERY_CHOICES, "delivery")
    ).get(configuration.get("delivery"), "Not specified" if request.LANGUAGE_CODE == "en" else "Не указана")
    payment_label = dict(
        localized_choices(PAYMENT_CHOICES, "payment")
    ).get(configuration.get("payment"), "Not specified" if request.LANGUAGE_CODE == "en" else "Не указан")
    order_status_label = {
        "new": "Received",
        "contacted": "Confirmed",
        "confirmed": "Confirmed",
        "production": "In production",
        "shipping": "On the way",
        "completed": "Delivered",
        "cancelled": "Cancelled",
    }.get(order.status, order.get_status_display()) if request.LANGUAGE_CODE == "en" else order.get_status_display()

    return render(
        request,
        "user/order_detail.html",
        {
            "account_active": "orders",
            "order": order,
            "items": items,
            "item_count": sum(item["quantity"] for item in items),
            "delivery_label": delivery_label,
            "payment_label": payment_label,
            "order_status_label": order_status_label,
            "status_stages": [
                {
                    "label": label,
                    "is_complete": index < current_stage,
                    "is_current": index == current_stage and order.status != Preorder.Status.CANCELLED,
                }
                for index, (_, label) in enumerate(status_stages)
            ],
            "is_cancelled": order.status == Preorder.Status.CANCELLED,
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
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    form = DeliveryAddressForm(request.POST or None, instance=profile)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            message = (
                "Delivery address saved."
                if request.LANGUAGE_CODE == "en"
                else "Адрес доставки сохранён."
            )
            messages.success(request, message)
            return redirect("accounts:addresses")
        message = (
            "Could not save the address. Check the field and try again."
            if request.LANGUAGE_CODE == "en"
            else "Не удалось сохранить адрес. Проверьте поле и попробуйте снова."
        )
        messages.error(request, message)

    return render(
        request,
        "user/section.html",
        {
            "account_active": "addresses",
            "section_key": "addresses",
            "section_title": "Delivery addresses" if request.LANGUAGE_CODE == "en" else "Адрес доставки",
            "section_intro": (
                "Addresses for future orders."
                if request.LANGUAGE_CODE == "en"
                else "Адреса для будущих заказов."
            ),
            "address_form": form,
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
            message = (
                "Profile details saved."
                if request.LANGUAGE_CODE == "en"
                else "Данные профиля сохранены."
            )
            messages.success(request, message)
            return redirect("accounts:profile")
        message = (
            "Please check your profile details and try again."
            if request.LANGUAGE_CODE == "en"
            else "Проверьте данные профиля и попробуйте ещё раз."
        )
        messages.error(request, message)

    return render(
        request,
        "user/profile.html",
        {"account_active": "profile", "profile_form": form},
    )
