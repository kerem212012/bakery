from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render

from catalog.models import Category, Product

from .calculator import CALCULATOR_OPTIONS, calculate_quote
from .forms import PreorderForm
from .models import Preorder, PreorderAttachment


def home(request):
    preorder_form = PreorderForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and preorder_form.is_valid():
        configuration = {
            field: preorder_form.cleaned_data[field]
            for field in (
                "flavor",
                "quantity",
                "size",
                "shape",
                "coating",
                "packaging",
                "delivery",
                "payment",
            )
        }
        quote = calculate_quote(configuration)
        with transaction.atomic():
            preorder = Preorder.objects.create(
                name=preorder_form.cleaned_data["name"],
                email=preorder_form.cleaned_data["email"],
                phone=preorder_form.cleaned_data["phone"],
                delivery_date=preorder_form.cleaned_data["delivery_date"],
                address=preorder_form.cleaned_data["address"],
                comment=preorder_form.cleaned_data["comment"],
                configuration=configuration,
                unit_price=quote["unit_price"],
                discount_percent=quote["discount_percent"],
                delivery_cost=quote["delivery_cost"],
                total_price=quote["total_price"],
                consent_given=True,
            )
            PreorderAttachment.objects.bulk_create(
                PreorderAttachment(preorder=preorder, file=file)
                for file in preorder_form.cleaned_data["attachments"]
            )
        messages.success(request, "Предзаказ отправлен. Мы свяжемся с вами.")
        return redirect("/#calculator")

    context = {
        "categories": Category.objects.filter(is_active=True),
        "popular_products": Product.objects.filter(
            is_active=True,
            is_featured=True,
            category__is_active=True,
        ).select_related("category"),
        "showcase_products": Product.objects.filter(
            is_active=True,
            category__is_active=True,
        )
        .select_related("category")
        .order_by("-is_featured", "display_order", "name")[:9],
        "preorder_form": preorder_form,
        "calculator_options": CALCULATOR_OPTIONS,
    }
    return render(request, "core/home.html", context)


def about(request):
    return render(request, "core/about.html")


def corporate(request):
    return render(request, "core/corporate.html")


def delivery(request):
    return render(request, "core/delivery.html")


def packaging(request):
    return render(request, "core/packaging.html")
