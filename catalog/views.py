from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.db import connection
from django.db.models import Count, F, Q
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.calculator import DELIVERY_COSTS
from core.models import Preorder, PreorderAttachment
from user.models import CustomerProfile

from .cart_forms import (
    COATING_OPTIONS,
    DOUGH_OPTIONS,
    PACKAGING_OPTIONS,
    SIZE_OPTIONS,
    CartCheckoutForm,
    CartItemForm,
)
from .favorites import get_favorite_ids
from .forms import CatalogFilterForm
from .models import Category, Product, ProductFilterOption

CART_SESSION_KEY = "cart"
DEFAULT_PRODUCT_PRICE = Decimal("1490")


def _session_cart(request):
    cart = request.session.get(CART_SESSION_KEY, {})
    return cart if isinstance(cart, dict) else {}


def _item_id(product_id, configuration):
    return ":".join(
        (
            str(product_id),
            configuration["size"],
            configuration["coating"],
            configuration["dough"],
            configuration["packaging"],
        )
    )


def _cart_items(request):
    cart = _session_cart(request)
    items = []
    stale_ids = []
    labels = {
        "coating": dict(COATING_OPTIONS),
        "dough": dict(DOUGH_OPTIONS),
        "packaging": dict(PACKAGING_OPTIONS),
    }

    for item_id, item in cart.items():
        try:
            product_id = int(item["product_id"])
            form = CartItemForm(data=item)
            if not form.is_valid():
                stale_ids.append(item_id)
                continue
            product = Product.objects.select_related("category").get(
                pk=product_id,
                is_active=True,
                category__is_active=True,
            )
        except (KeyError, TypeError, ValueError, Product.DoesNotExist):
            stale_ids.append(item_id)
            continue

        quantity = form.cleaned_data["quantity"]
        size = form.cleaned_data["size"]
        base_price = product.price or DEFAULT_PRODUCT_PRICE
        unit_price = (base_price * Decimal(size) ** 2 / Decimal("64")).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        items.append(
            {
                "item_id": item_id,
                "product": product,
                "quantity": quantity,
                "size": size,
                "coating": form.cleaned_data["coating"],
                "dough": form.cleaned_data["dough"],
                "packaging": form.cleaned_data["packaging"],
                "coating_label": labels["coating"][form.cleaned_data["coating"]],
                "dough_label": labels["dough"][form.cleaned_data["dough"]],
                "packaging_label": labels["packaging"][form.cleaned_data["packaging"]],
                "unit_price": unit_price,
                "line_total": unit_price * quantity,
            }
        )

    if stale_ids:
        for item_id in stale_ids:
            cart.pop(item_id, None)
        request.session[CART_SESSION_KEY] = cart
    return items


def _cart_context(request, form=None):
    items = _cart_items(request)
    item_count = sum(item["quantity"] for item in items)
    subtotal = sum((item["line_total"] for item in items), Decimal("0"))
    delivery = form["delivery"].value() if form and form.is_bound else "moscow"
    delivery_cost = DELIVERY_COSTS.get(delivery, DELIVERY_COSTS["moscow"])
    initial = {"delivery": "moscow", "payment": "card"}
    if request.user.is_authenticated:
        saved_address = CustomerProfile.objects.filter(user=request.user).values_list(
            "delivery_address", flat=True
        ).first()
        if saved_address:
            initial["address"] = saved_address

    return {
        "items": items,
        "item_count": item_count,
        "subtotal": subtotal,
        "delivery_cost": delivery_cost,
        "total": subtotal + delivery_cost,
        "form": form or CartCheckoutForm(initial=initial),
        "size_options": SIZE_OPTIONS,
        "coating_options": COATING_OPTIONS,
        "dough_options": DOUGH_OPTIONS,
        "packaging_options": PACKAGING_OPTIONS,
        "delivery_options": tuple(
            (value, label, DELIVERY_COSTS[value])
            for value, label in CartCheckoutForm.base_fields["delivery"].choices
        ),
    }


def cart(request):
    if request.method == "POST":
        form = CartCheckoutForm(request.POST, request.FILES)
        context = _cart_context(request, form)
        if not context["items"]:
            messages.error(request, "Корзина пуста.")
            return redirect("catalog:cart")
        if form.is_valid():
            subtotal = context["subtotal"]
            delivery_cost = DELIVERY_COSTS[form.cleaned_data["delivery"]]
            configuration = {
                "items": [
                    {
                        "product_id": item["product"].pk,
                        "name": item["product"].name,
                        "quantity": item["quantity"],
                        "size": item["size"],
                        "coating": item["coating"],
                        "dough": item["dough"],
                        "packaging": item["packaging"],
                        "unit_price": str(item["unit_price"]),
                    }
                    for item in context["items"]
                ],
                "delivery": form.cleaned_data["delivery"],
                "payment": form.cleaned_data["payment"],
            }
            total_quantity = context["item_count"]
            unit_price = (subtotal / total_quantity).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            with transaction.atomic():
                preorder = Preorder.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    name=form.cleaned_data["name"],
                    email=form.cleaned_data["email"],
                    phone=form.cleaned_data["phone"],
                    address=form.cleaned_data["address"],
                    comment=form.cleaned_data["comment"],
                    configuration=configuration,
                    unit_price=unit_price,
                    discount_percent=0,
                    delivery_cost=delivery_cost,
                    total_price=subtotal + delivery_cost,
                    consent_given=True,
                )
                PreorderAttachment.objects.bulk_create(
                    PreorderAttachment(preorder=preorder, file=file)
                    for file in form.cleaned_data["attachments"]
                )
                if request.user.is_authenticated and form.cleaned_data["address"]:
                    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
                    if profile.delivery_address != form.cleaned_data["address"]:
                        profile.delivery_address = form.cleaned_data["address"]
                        profile.save(update_fields=("delivery_address",))
            request.session.pop(CART_SESSION_KEY, None)
            messages.success(
                request,
                f"Заказ #{preorder.pk} оформлен. Мы свяжемся с вами для подтверждения.",
            )
            if request.user.is_authenticated:
                return redirect("accounts:order_detail", order_id=preorder.pk)
            return redirect("catalog:cart")
    else:
        form = None
    return render(request, "catalog/cart.html", _cart_context(request, form))


@require_POST
def add_to_cart(request, product_id):
    if not request.user.is_authenticated:
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")
        if not next_url or not url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            next_url = reverse("catalog:category_list")
        return redirect_to_login(next_url, login_url=reverse("accounts:login"))

    product = get_object_or_404(
        Product,
        pk=product_id,
        is_active=True,
        category__is_active=True,
    )
    form = CartItemForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Не удалось добавить товар: проверьте выбранные параметры.")
        return redirect("catalog:category_list")

    configuration = form.cleaned_data
    item_id = _item_id(product.pk, configuration)
    cart = _session_cart(request)
    existing_item = cart.get(item_id)
    current_quantity = (
        existing_item.get("quantity", 0) if isinstance(existing_item, dict) else 0
    )
    try:
        current_quantity = int(current_quantity)
    except (TypeError, ValueError):
        current_quantity = 0
    cart[item_id] = {
        "product_id": product.pk,
        **configuration,
        "quantity": min(current_quantity + configuration["quantity"], 99),
    }
    request.session[CART_SESSION_KEY] = cart
    messages.success(request, f"«{product.name}» добавлен в корзину.")
    return redirect("catalog:cart")


@require_POST
def update_cart_item(request, item_id):
    cart = _session_cart(request)
    item = cart.get(item_id)
    if not isinstance(item, dict):
        messages.error(request, "Товар не найден в корзине.")
        return redirect("catalog:cart")
    form = CartItemForm(request.POST)
    if form.is_valid():
        product_id = int(item.get("product_id"))
        updated_item = {"product_id": product_id, **form.cleaned_data}
        new_item_id = _item_id(product_id, form.cleaned_data)
        if new_item_id != item_id:
            cart.pop(item_id)
            existing_item = cart.get(new_item_id)
            try:
                existing_quantity = int(existing_item.get("quantity", 0))
            except (AttributeError, TypeError, ValueError):
                existing_quantity = 0
            updated_item["quantity"] = min(
                existing_quantity + form.cleaned_data["quantity"], 99
            )
        cart[new_item_id] = updated_item
        request.session[CART_SESSION_KEY] = cart
    else:
        messages.error(request, "Не удалось обновить товар: проверьте выбранные параметры.")
    return redirect("catalog:cart")


@require_POST
def remove_cart_item(request, item_id):
    cart = _session_cart(request)
    cart.pop(item_id, None)
    request.session[CART_SESSION_KEY] = cart
    return redirect("catalog:cart")


@require_POST
def clear_cart(request):
    request.session.pop(CART_SESSION_KEY, None)
    return redirect("catalog:cart")

def category_list(request):
    filter_form = CatalogFilterForm(request.GET or None)
    products = Product.objects.filter(
        is_active=True,
        category__is_active=True,
    ).select_related("category")

    if filter_form.is_valid():
        query = filter_form.cleaned_data["query"].strip()
        search_mode = filter_form.cleaned_data["search_mode"]
        selected_categories = filter_form.cleaned_data["categories"]
        min_price = filter_form.cleaned_data["min_price"]
        max_price = filter_form.cleaned_data["max_price"]
        selected_options = {
            "size": filter_form.cleaned_data["sizes"],
            "coating": filter_form.cleaned_data["coatings"],
            "dough": filter_form.cleaned_data["doughs"],
            "color": filter_form.cleaned_data["colors"],
            "occasion": filter_form.cleaned_data["occasions"],
            "packaging": filter_form.cleaned_data["packaging"],
        }

        if query:
            if search_mode == "name":
                if connection.vendor == "sqlite":
                    matching_ids = [
                        product_id
                        for product_id, name in products.values_list("pk", "name")
                        if query.casefold() in name.casefold()
                    ]
                    products = products.filter(pk__in=matching_ids)
                else:
                    products = products.filter(name__icontains=query)
            else:
                products = products.filter(
                    Q(name__icontains=query) | Q(description__icontains=query)
                )
        if selected_categories:
            products = products.filter(category__in=selected_categories)
        if min_price is not None:
            products = products.filter(price__gte=min_price)
        if max_price is not None:
            products = products.filter(price__lte=max_price)
        for filter_type, values in selected_options.items():
            if values:
                products = products.filter(
                    filter_options__filter_type=filter_type,
                    filter_options__value__in=values,
                    filter_options__is_active=True,
                )
        products = products.distinct()

        sort = filter_form.cleaned_data["sort"] or "popular"
        if sort == "price_asc":
            products = products.order_by(F("price").asc(nulls_last=True), "name")
        elif sort == "price_desc":
            products = products.order_by(F("price").desc(nulls_last=True), "name")
        elif sort == "name":
            products = products.order_by("name")
        else:
            products = products.order_by("-is_featured", "display_order", "name")
    else:
        products = products.order_by("-is_featured", "display_order", "name")

    categories = Category.objects.filter(is_active=True).annotate(
        active_product_count=Count("products", filter=Q(products__is_active=True))
    )
    total_product_count = Product.objects.filter(
        is_active=True,
        category__is_active=True,
    ).count()
    filter_options = ProductFilterOption.objects.filter(is_active=True).annotate(
        product_count=Count(
            "products",
            filter=Q(products__is_active=True, products__category__is_active=True),
        )
    ).distinct()
    selected_filter_values = {
        field: request.GET.getlist(field)
        for field in ("sizes", "coatings", "doughs", "colors", "occasions", "packaging")
    }
    filter_groups = [
        {
            "type": filter_type,
            "name": field_name,
            "title": label,
            "options": filter_options.filter(filter_type=filter_type),
            "selected_values": selected_filter_values[field_name],
        }
        for (filter_type, label), field_name in zip(
            ProductFilterOption.FilterType.choices,
            ("sizes", "coatings", "doughs", "colors", "occasions", "packaging"),
        )
    ]
    return render(
        request,
        "catalog/category_list.html",
        {
            "categories": categories,
            "quick_categories": categories[:5],
            "products": products,
            "total_product_count": total_product_count,
            "filter_groups": filter_groups,
            "favorite_ids": get_favorite_ids(request),
            "filter_form": filter_form,
            "selected_category_ids": request.GET.getlist("categories"),
            "selected_filter_values": selected_filter_values,
        },
    )


def category_overview(request):
    categories = Category.objects.filter(is_active=True).annotate(
        active_product_count=Count("products", filter=Q(products__is_active=True))
    )
    return render(
        request,
        "catalog/category_overview.html",
        {"categories": categories},
    )


@require_POST
def toggle_favorite(request, product_id):
    product = get_object_or_404(
        Product,
        pk=product_id,
        is_active=True,
        category__is_active=True,
    )
    favorite_ids = get_favorite_ids(request)
    if product.pk in favorite_ids:
        favorite_ids.remove(product.pk)
        is_favorite = False
    else:
        favorite_ids.add(product.pk)
        is_favorite = True

    request.session["favorite_product_ids"] = sorted(favorite_ids)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(
            {"is_favorite": is_favorite, "favorites_count": len(favorite_ids)}
        )

    redirect_to = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(
        redirect_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        redirect_to = reverse("catalog:category_list")
    return redirect(redirect_to)


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    products = category.products.filter(is_active=True)
    return render(
        request,
        "catalog/category_detail.html",
        {
            "category": category,
            "products": products,
            "favorite_ids": get_favorite_ids(request),
        },
    )


def product_detail(request, category_slug, product_slug):
    category = get_object_or_404(Category, slug=category_slug, is_active=True)
    product = get_object_or_404(
        Product,
        slug=product_slug,
        category=category,
        is_active=True,
    )
    related_products = (
        Product.objects.filter(category=category, is_active=True)
        .exclude(pk=product.pk)
        .order_by("display_order", "name")[:4]
    )
    return render(
        request,
        "catalog/product_detail.html",
        {
            "category": category,
            "product": product,
            "related_products": related_products,
            "is_favorite": product.pk in get_favorite_ids(request),
        },
    )
