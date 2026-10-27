from django.http import JsonResponse
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .favorites import get_favorite_ids
from .forms import CatalogFilterForm
from .models import Category, Product


def category_list(request):
    filter_form = CatalogFilterForm(request.GET or None)
    products = Product.objects.filter(
        is_active=True,
        category__is_active=True,
    ).select_related("category")

    if filter_form.is_valid():
        query = filter_form.cleaned_data["query"].strip()
        selected_categories = filter_form.cleaned_data["categories"]
        min_price = filter_form.cleaned_data["min_price"]
        max_price = filter_form.cleaned_data["max_price"]

        if query:
            products = products.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )
        if selected_categories:
            products = products.filter(category__in=selected_categories)
        if min_price is not None:
            products = products.filter(price__gte=min_price)
        if max_price is not None:
            products = products.filter(price__lte=max_price)

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
    return render(
        request,
        "catalog/category_list.html",
        {
            "categories": categories,
            "products": products,
            "favorite_ids": get_favorite_ids(request),
            "filter_form": filter_form,
            "selected_category_ids": request.GET.getlist("categories"),
        },
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
