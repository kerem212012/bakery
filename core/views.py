from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalog.models import Category, Product
from user.models import CustomerProfile

from .calculator import calculate_quote, localized_calculator_options
from .forms import FeedbackForm, PreorderForm
from .models import FeedbackSubmission, Preorder, PreorderAttachment


@staff_member_required(login_url="admin:login")
def admin_dashboard(request):
    user = request.user
    can_view_products = user.has_perm("catalog.view_product")
    can_view_categories = user.has_perm("catalog.view_category")
    can_view_filter_options = user.has_perm("catalog.view_productfilteroption")
    can_view_orders = user.has_perm("core.view_preorder")
    can_view_customers = user.has_perm("user.view_customerprofile")
    can_view_feedback = user.has_perm("core.view_feedbacksubmission")

    return render(
        request,
        "core/admin_dashboard.html",
        {
            "can_view_products": can_view_products,
            "can_add_products": user.has_perm("catalog.add_product"),
            "can_view_categories": can_view_categories,
            "can_add_categories": user.has_perm("catalog.add_category"),
            "can_view_filter_options": can_view_filter_options,
            "can_view_orders": can_view_orders,
            "can_view_customers": can_view_customers,
            "can_view_feedback": can_view_feedback,
            "product_count": Product.objects.count() if can_view_products else None,
            "active_product_count": (
                Product.objects.filter(is_active=True).count()
                if can_view_products
                else None
            ),
            "category_count": Category.objects.count() if can_view_categories else None,
            "new_order_count": (
                Preorder.objects.filter(status=Preorder.Status.NEW).count()
                if can_view_orders
                else None
            ),
            "customer_count": (
                CustomerProfile.objects.count() if can_view_customers else None
            ),
            "new_feedback_count": (
                FeedbackSubmission.objects.filter(
                    status=FeedbackSubmission.Status.NEW
                ).count()
                if can_view_feedback
                else None
            ),
            "recent_orders": (
                Preorder.objects.select_related("user").order_by("-created_at")[:5]
                if can_view_orders
                else ()
            ),
        },
    )


@staff_member_required(login_url="admin:login")
def manager_dashboard(request):
    user = request.user
    can_view_orders = user.has_perm("core.view_preorder")
    can_change_orders = user.has_perm("core.change_preorder")
    can_view_feedback = user.has_perm("core.view_feedbacksubmission")
    if not can_view_orders and not can_view_feedback:
        raise PermissionDenied

    order_status_labels = {
        Preorder.Status.NEW: ("New", "Новый"),
        Preorder.Status.CONTACTED: ("Confirmed", "Подтверждён"),
        Preorder.Status.PRODUCTION: ("In production", "В производстве"),
        Preorder.Status.SHIPPING: ("On the way", "В пути"),
        Preorder.Status.COMPLETED: ("Delivered", "Доставлен"),
        Preorder.Status.CANCELLED: ("Cancelled", "Отменён"),
    }
    orders = (
        list(Preorder.objects.order_by("-created_at")[:12])
        if can_view_orders
        else []
    )
    status_label_index = 0 if request.LANGUAGE_CODE == "en" else 1
    for order in orders:
        order.manager_status_label = order_status_labels[order.status][status_label_index]
    order_counts = (
        {
            status: Preorder.objects.filter(status=status).count()
            for status, _ in Preorder.Status.choices
        }
        if can_view_orders
        else {}
    )
    feedback_items = (
        list(FeedbackSubmission.objects.order_by("-created_at")[:6])
        if can_view_feedback
        else []
    )
    feedback_status_labels = {
        FeedbackSubmission.Status.NEW: ("New", "Новое"),
        FeedbackSubmission.Status.IN_PROGRESS: ("In progress", "В работе"),
        FeedbackSubmission.Status.RESOLVED: ("Resolved", "Решено"),
    }
    for item in feedback_items:
        item.manager_status_label = feedback_status_labels[item.status][status_label_index]
    return render(
        request,
        "core/manager_dashboard.html",
        {
            "can_view_orders": can_view_orders,
            "can_change_orders": can_change_orders,
            "can_view_feedback": can_view_feedback,
            "orders": orders,
            "order_counts": order_counts,
            "order_status_choices": [
                (value, order_status_labels[value][0 if request.LANGUAGE_CODE == "en" else 1])
                for value, _ in Preorder.Status.choices
            ],
            "feedback_items": feedback_items,
            "new_feedback_count": (
                FeedbackSubmission.objects.filter(
                    status=FeedbackSubmission.Status.NEW
                ).count()
                if can_view_feedback
                else 0
            ),
        },
    )


@staff_member_required(login_url="admin:login")
@require_POST
def manager_update_order_status(request, order_id):
    if not request.user.has_perms(("core.view_preorder", "core.change_preorder")):
        raise PermissionDenied
    order = get_object_or_404(Preorder, pk=order_id)
    status = request.POST.get("status")
    if status not in dict(Preorder.Status.choices):
        message = (
            "Choose a valid order status."
            if request.LANGUAGE_CODE == "en"
            else "Выберите допустимый статус заказа."
        )
        messages.error(request, message)
    else:
        order.status = status
        order.save(update_fields=("status",))
        message = (
            f"Order #{order.pk} status updated."
            if request.LANGUAGE_CODE == "en"
            else f"Статус заказа №{order.pk} обновлён."
        )
        messages.success(request, message)
    return redirect("manager_dashboard")


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
        if request.LANGUAGE_CODE == "en":
            messages.success(request, "Your pre-order has been sent. We will be in touch.")
        else:
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
        "calculator_options": localized_calculator_options(),
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
            message = (
                "Thank you! We have received your message and will reply by email."
                if request.LANGUAGE_CODE == "en"
                else "Спасибо! Ваше обращение принято. Мы свяжемся с вами по электронной почте."
            )
            messages.success(request, message)
            return redirect("feedback")
        message = (
            "Please check the form and correct the marked errors."
            if request.LANGUAGE_CODE == "en"
            else "Проверьте форму и исправьте отмеченные ошибки."
        )
        messages.error(request, message)
    return render(request, "core/feedback.html", {"form": form})


def delivery(request):
    return render(request, "core/delivery.html")


def packaging(request):
    return render(request, "core/packaging.html")


def faq(request):
    faq_items = [
        {
            "number": "01",
            "question": "What products can you make to order?",
            "answer": "We create custom sweet sets, gift boxes, branded sets with logos, and seasonal desserts for events. We tailor the flavor, design, and packaging to each order.",
        },
        {
            "number": "02",
            "question": "Can you add a logo or custom design?",
            "answer": "Yes. We personalize corporate and private orders with logos, brand colors, and packaging designed to match your style.",
        },
        {
            "number": "03",
            "question": "What is the minimum order quantity?",
            "answer": "The minimum quantity depends on the product and personalization. We are happy to discuss options for smaller gift sets and custom products.",
        },
        {
            "number": "04",
            "question": "How long does production take?",
            "answer": "Timing depends on order size, design complexity, and our current production schedule. We confirm a timeline when approving the design and set contents.",
        },
        {
            "number": "05",
            "question": "What packaging options are available?",
            "answer": "We offer classic boxes, gift sets, ribbons, wrapping paper, kraft baskets, and custom packaging for your event or brand.",
        },
        {
            "number": "06",
            "question": "Do you deliver?",
            "answer": "Yes. We deliver in Moscow, the Moscow region, and other regions of Russia. We can help choose a convenient delivery method and confirm timing and cost.",
        },
        {
            "number": "07",
            "question": "Which payment methods do you accept?",
            "answer": "You can pay by bank card, bank transfer, or electronic payment. Payment terms for corporate orders can be agreed with our manager.",
        },
        {
            "number": "08",
            "question": "Can I order a sample?",
            "answer": "Yes. For large and corporate orders, we can prepare a sample or trial set so you can review the quality, flavor, and design before production.",
        },
    ] if request.LANGUAGE_CODE == "en" else [
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
