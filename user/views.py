from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from catalog.cart_forms import COATING_OPTIONS, DOUGH_OPTIONS, PACKAGING_OPTIONS
from catalog.favorites import get_favorite_ids
from catalog.models import Product
from core.calculator import DELIVERY_CHOICES, PAYMENT_CHOICES
from core.models import Preorder

from .forms import AccountProfileForm, DeliveryAddressForm, RegistrationForm
from .models import CustomerProfile


def _orders_count_label(count):
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


def _order_row(order):
    configuration = order.configuration if isinstance(order.configuration, dict) else {}
    items = configuration.get("items")
    if isinstance(items, list) and items:
        summary = ", ".join(
            f'{item.get("name", "Товар")} × {item.get("quantity", 1)}'
            for item in items
            if isinstance(item, dict)
        )
        item_count = sum(
            item.get("quantity", 1)
            for item in items
            if isinstance(item, dict) and isinstance(item.get("quantity", 1), int)
        )
    else:
        details = [f'{configuration.get("quantity", 1)} шт.']
        if configuration.get("size"):
            details.append(f'{configuration["size"]} см')
        summary = " · ".join(details)
        item_count = configuration.get("quantity", 1)
    return {"order": order, "summary": summary, "item_count": item_count}


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
    orders = request.user.preorders.all()
    orders_count = orders.count()
    recent_orders = [_order_row(order) for order in orders[:3]]
    saved_address = CustomerProfile.objects.filter(user=request.user).values_list(
        "delivery_address", flat=True
    ).first()
    return render(
        request,
        "user/dashboard.html",
        {
            "orders_count": orders_count,
            "orders_count_label": _orders_count_label(orders_count),
            "recent_orders": recent_orders,
            "saved_address_label": "Сохранён" if saved_address else "—",
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
            "section_title": "Мои заказы",
            "section_intro": "История ваших покупок и статусы заказов.",
            "order_rows": [_order_row(order) for order in user_orders],
            "orders_count": orders_count,
            "orders_count_label": _orders_count_label(orders_count),
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
    coating_labels = dict(COATING_OPTIONS)
    dough_labels = dict(DOUGH_OPTIONS)
    packaging_labels = dict(PACKAGING_OPTIONS)
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
            items.append(
                {
                    "name": configured_item.get("name", "Товар"),
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
                "name": "Индивидуальный заказ",
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
        (Preorder.Status.NEW, "Принят"),
        (Preorder.Status.CONTACTED, "Подтверждён"),
        (Preorder.Status.PRODUCTION, "В производстве"),
        (Preorder.Status.SHIPPING, "В пути"),
        (Preorder.Status.COMPLETED, "Доставлен"),
    )
    legacy_status = {
        "contacted": Preorder.Status.CONTACTED,
        "completed": Preorder.Status.COMPLETED,
    }.get(order.status, order.status)
    current_stage = next(
        (index for index, (status, _) in enumerate(status_stages) if status == legacy_status),
        0,
    )
    delivery_label = dict(DELIVERY_CHOICES).get(configuration.get("delivery"), "Не указана")
    payment_label = dict(PAYMENT_CHOICES).get(configuration.get("payment"), "Не указан")

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
            messages.success(request, "Адрес доставки сохранён.")
            return redirect("accounts:addresses")
        messages.error(request, "Не удалось сохранить адрес. Проверьте поле и попробуйте снова.")

    return render(
        request,
        "user/section.html",
        {
            "account_active": "addresses",
            "section_key": "addresses",
            "section_title": "Адрес доставки",
            "section_intro": "Адреса для будущих заказов.",
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
            messages.success(request, "Данные профиля сохранены.")
            return redirect("accounts:profile")
        messages.error(request, "Проверьте данные профиля и попробуйте ещё раз.")

    return render(
        request,
        "user/profile.html",
        {"account_active": "profile", "profile_form": form},
    )
