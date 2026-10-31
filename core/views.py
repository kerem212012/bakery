from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render

from catalog.models import Category, Product

from .calculator import CALCULATOR_OPTIONS, calculate_quote
from .forms import FeedbackForm, PreorderForm
from .models import FeedbackSubmission, Preorder, PreorderAttachment


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
                user=request.user if request.user.is_authenticated else None,
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


def contacts(request):
    return render(request, "core/contacts.html")


def feedback(request):
    form = FeedbackForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            FeedbackSubmission.objects.create(**form.cleaned_data)
            messages.success(
                request,
                "Спасибо! Ваше обращение принято. Мы свяжемся с вами по электронной почте.",
            )
            return redirect("feedback")
        messages.error(request, "Проверьте форму и исправьте отмеченные ошибки.")
    return render(request, "core/feedback.html", {"form": form})


def delivery(request):
    return render(request, "core/delivery.html")


def packaging(request):
    return render(request, "core/packaging.html")


def faq(request):
    faq_items = [
        {
            "number": "01",
            "question": "Какие изделия вы изготавливаете на заказ?",
            "answer": "Мы создаём индивидуальные сладкие наборы, подарочные коробки, фирменные наборы с логотипом и сезонные десерты для мероприятий. В каждом заказе учитываем вкус, оформление и формат упаковки.",
        },
        {
            "number": "02",
            "question": "Можно ли нанести логотип или индивидуальный дизайн?",
            "answer": "Да. Мы делаем персонализацию под брендинг, корпоративные подарки и частные заказы: наносим логотип, добавляем фирменные цвета и оформляем упаковку в вашем стиле.",
        },
        {
            "number": "03",
            "question": "Какой минимальный тираж?",
            "answer": "Минимальный тираж зависит от формата изделия и типа персонализации. Для небольших подарочных наборов и изделий на заказ мы готовы обсуждать индивидуальные условия.",
        },
        {
            "number": "04",
            "question": "Какие сроки изготовления?",
            "answer": "Сроки зависят от объёма заказа, сложности оформления и текущей загрузки производства. Обычно обсуждаем сроки на этапе согласования макета и состава набора.",
        },
        {
            "number": "05",
            "question": "Какие варианты упаковки доступны?",
            "answer": "У нас есть классическая коробочная упаковка, подарочные наборы, ленты, бумага, крафтовые корзины и индивидуальная упаковка под событие или фирменный стиль.",
        },
        {
            "number": "06",
            "question": "Осуществляете ли доставку?",
            "answer": "Да, мы доставляем заказы по Москве, Московской области и в другие регионы России. Подберём удобный способ доставки и расскажем о сроках и стоимости.",
        },
        {
            "number": "07",
            "question": "Какие способы оплаты?",
            "answer": "Оплата возможна банковской картой, переводом по реквизитам, через электронные платежи и по предварительному согласованию с менеджером для корпоративных заказов.",
        },
        {
            "number": "08",
            "question": "Можно ли заказать образец?",
            "answer": "Да. Для крупных и корпоративных заказов мы можем подготовить образец или пробный набор, чтобы вы могли оценить качество, вкус и оформление до запуска тиража.",
        },
    ]
    return render(request, "core/faq.html", {"faq_items": faq_items})
