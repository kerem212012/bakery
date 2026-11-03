from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.forms import modelformset_factory
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalog.forms import (
    CategoryEditorForm,
    ProductEditorForm,
    ProductFilterOptionEditorForm,
)
from catalog.models import Category, Product, ProductFilterOption
from user.models import CustomerProfile

from .calculator import calculate_quote, localized_calculator_options
from .forms import (
    AdminFeedbackStatusForm,
    AdminOrderStatusForm,
    AboutPromiseForm,
    AboutStorySectionForm,
    AboutValueCardForm,
    AboutValuesHeadingForm,
    BusinessClientsCalculatorForm,
    BusinessClientsCardForm,
    BusinessClientsPaymentHeadingForm,
    BusinessClientsSectionHeadingForm,
    BusinessClientsSectionTitleForm,
    ContactRequisitesForm,
    ContactDetailsForm,
    DeliveryHelpCardForm,
    DeliveryMethodsCardForm,
    DeliveryPickupDetailForm,
    DeliveryPickupHeadingForm,
    DeliverySectionHeadingForm,
    FAQQuestionForm,
    FeedbackForm,
    HomeAboutSectionForm,
    HomeHeroSlideBaseFormSet,
    HOME_HERO_SLIDE_DEFAULTS,
    HomeHeroSlideForm,
    PackagingCardForm,
    PartnershipDirectionForm,
    PartnershipSuccessForm,
    PreorderForm,
    SiteContentBlockForm,
    SitePageContentForm,
)
from .models import (
    FeedbackSubmission,
    HomeHeroSlide,
    Preorder,
    PreorderAttachment,
    SiteContentBlock,
    SitePageContent,
    SitePageSection,
)


SITE_CONTENT_PERMISSIONS = (
    "core.add_sitepagecontent",
    "core.change_sitepagecontent",
    "core.add_homeheroslide",
    "core.change_homeheroslide",
    "core.add_sitecontentblock",
    "core.change_sitecontentblock",
    "core.add_sitepagesection",
    "core.change_sitepagesection",
)


def _can_manage_site_content(user):
    return user.is_superuser or user.has_perms(SITE_CONTENT_PERMISSIONS)


@staff_member_required(login_url="accounts:login")
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
            "can_manage_site_content": _can_manage_site_content(user),
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


@staff_member_required(login_url="accounts:login")
def site_content_manager(request, block_id=None):
    if not _can_manage_site_content(request.user):
        raise PermissionDenied

    block = get_object_or_404(SiteContentBlock, pk=block_id) if block_id else None
    page_choices = dict(SiteContentBlock.Page.choices)
    selected_page = block.page if block else SiteContentBlock.Page.CATALOG
    if not block:
        selected_page = request.POST.get("page", selected_page) if request.method == "POST" else request.GET.get("page", selected_page)

    if selected_page not in page_choices:
        raise Http404("Unknown site content page.")

    page_content = SitePageContent.objects.filter(page=selected_page).first()
    form = None
    content_form = None
    slide_formset = None
    home_about_form = None
    about_story_form = None
    about_promises_formset = None
    about_values_formset = None
    about_values_heading_form = None
    contact_details_form = None
    contact_requisites_form = None
    business_clients_contact_form = None
    business_clients_steps_heading_form = None
    business_clients_steps_formset = None
    business_clients_payment_heading_form = None
    business_clients_payment_formset = None
    business_clients_delivery_heading_form = None
    business_clients_delivery_formset = None
    business_clients_calculator_form = None
    partnership_directions_heading_form = None
    partnership_directions_formset = None
    partnership_success_heading_form = None
    partnership_success_formset = None
    delivery_methods_heading_form = None
    delivery_methods_formset = None
    delivery_pickup_heading_form = None
    delivery_pickup_formset = None
    delivery_help_heading_form = None
    delivery_help_formset = None
    faq_questions_formset = None
    packaging_options_heading_form = None
    packaging_options_formset = None
    packaging_extras_heading_form = None
    packaging_extras_formset = None
    home_about_sections = (
        list(
            SitePageSection.objects.filter(
                page=SitePageSection.Page.HOME,
                group="home_about",
            ).order_by("display_order", "pk")
        )
        if selected_page == SitePageSection.Page.HOME
        else []
    )
    home_about_instance = home_about_sections[0] if home_about_sections else None
    home_about_secondary = (
        home_about_sections[1] if len(home_about_sections) > 1 else None
    )
    about_story_instance = (
        SitePageSection.objects.filter(
            page=SitePageSection.Page.ABOUT,
            group="story",
        )
        .order_by("display_order", "pk")
        .first()
        if selected_page == SitePageSection.Page.ABOUT
        else None
    )
    about_promises_queryset = (
        SitePageSection.objects.filter(
            page=SitePageSection.Page.ABOUT,
            group="promises",
        ).order_by("display_order", "pk")
        if selected_page == SitePageSection.Page.ABOUT
        else SitePageSection.objects.none()
    )
    about_values_queryset = (
        SitePageSection.objects.filter(
            page=SitePageSection.Page.ABOUT,
            group="values",
        ).order_by("display_order", "pk")
        if selected_page == SitePageSection.Page.ABOUT
        else SitePageSection.objects.none()
    )
    about_values_heading_instance = about_values_queryset.first()
    contact_details_queryset = (
        SitePageSection.objects.filter(
            page=SitePageSection.Page.CONTACTS,
            group="details",
        ).order_by("display_order", "pk")
        if selected_page == SiteContentBlock.Page.ALL
        else SitePageSection.objects.none()
    )
    contact_requisites_queryset = (
        SitePageSection.objects.filter(
            page=SitePageSection.Page.CONTACTS,
            group="requisites",
        ).order_by("display_order", "pk")
        if selected_page == SitePageSection.Page.CONTACTS
        else SitePageSection.objects.none()
    )
    contact_requisites_instance = (
        contact_requisites_queryset.first()
        or SitePageSection(
            page=SitePageSection.Page.CONTACTS,
            group="requisites",
            display_order=0,
        )
    )
    business_clients_contacts_queryset = (
        SitePageSection.objects.filter(
            page=SitePageSection.Page.BUSINESS_CLIENTS,
            group="contacts",
        ).order_by("display_order", "pk")
        if selected_page == SiteContentBlock.Page.ALL
        else SitePageSection.objects.none()
    )
    business_clients_steps_queryset = (
        SitePageSection.objects.filter(
            page=SitePageSection.Page.BUSINESS_CLIENTS,
            group="steps",
        ).order_by("display_order", "pk")
        if selected_page == SitePageSection.Page.BUSINESS_CLIENTS
        else SitePageSection.objects.none()
    )
    business_clients_payment_queryset = (
        SitePageSection.objects.filter(
            page=SitePageSection.Page.BUSINESS_CLIENTS,
            group="payment",
        ).order_by("display_order", "pk")
        if selected_page == SitePageSection.Page.BUSINESS_CLIENTS
        else SitePageSection.objects.none()
    )
    business_clients_delivery_queryset = (
        SitePageSection.objects.filter(
            page=SitePageSection.Page.BUSINESS_CLIENTS,
            group="delivery",
        ).order_by("display_order", "pk")
        if selected_page == SitePageSection.Page.BUSINESS_CLIENTS
        else SitePageSection.objects.none()
    )
    business_clients_calculator_queryset = (
        SitePageSection.objects.filter(
            page=SitePageSection.Page.BUSINESS_CLIENTS,
            group="calculator",
        ).order_by("display_order", "pk")
        if selected_page == SitePageSection.Page.BUSINESS_CLIENTS
        else SitePageSection.objects.none()
    )
    business_clients_steps_heading_instance = (
        business_clients_steps_queryset.filter(is_active=True).first()
        or business_clients_steps_queryset.first()
        or SitePageSection(
            page=SitePageSection.Page.BUSINESS_CLIENTS,
            group="steps",
            display_order=0,
        )
    )
    business_clients_payment_heading_instance = (
        business_clients_payment_queryset.filter(is_active=True).first()
        or business_clients_payment_queryset.first()
        or SitePageSection(
            page=SitePageSection.Page.BUSINESS_CLIENTS,
            group="payment",
            display_order=0,
        )
    )
    business_clients_delivery_heading_instance = (
        business_clients_delivery_queryset.filter(is_active=True).first()
        or business_clients_delivery_queryset.first()
        or SitePageSection(
            page=SitePageSection.Page.BUSINESS_CLIENTS,
            group="delivery",
            display_order=0,
        )
    )
    business_clients_calculator_instance = (
        business_clients_calculator_queryset.first()
        or SitePageSection(
            page=SitePageSection.Page.BUSINESS_CLIENTS,
            group="calculator",
            display_order=0,
        )
    )
    partnership_directions_queryset = (
        SitePageSection.objects.filter(
            page=SitePageSection.Page.PARTNERSHIP,
            group="directions",
        ).order_by("display_order", "pk")
        if selected_page == SitePageSection.Page.PARTNERSHIP
        else SitePageSection.objects.none()
    )
    partnership_success_queryset = (
        SitePageSection.objects.filter(
            page=SitePageSection.Page.PARTNERSHIP,
            group="stats",
        ).order_by("display_order", "pk")
        if selected_page == SitePageSection.Page.PARTNERSHIP
        else SitePageSection.objects.none()
    )
    partnership_directions_heading_instance = (
        partnership_directions_queryset.filter(is_active=True).first()
        or partnership_directions_queryset.first()
        or SitePageSection(
            page=SitePageSection.Page.PARTNERSHIP,
            group="directions",
            display_order=0,
        )
    )
    partnership_success_heading_instance = (
        partnership_success_queryset.filter(is_active=True).first()
        or partnership_success_queryset.first()
        or SitePageSection(
            page=SitePageSection.Page.PARTNERSHIP,
            group="stats",
            display_order=0,
        )
    )
    delivery_methods_queryset = (
        SitePageSection.objects.filter(
            page=SitePageSection.Page.DELIVERY,
            group="methods",
        ).order_by("display_order", "pk")
        if selected_page == SitePageSection.Page.DELIVERY
        else SitePageSection.objects.none()
    )
    delivery_pickup_queryset = (
        SitePageSection.objects.filter(
            page=SitePageSection.Page.DELIVERY,
            group="pickup",
        ).order_by("display_order", "pk")
        if selected_page == SitePageSection.Page.DELIVERY
        else SitePageSection.objects.none()
    )
    delivery_help_queryset = (
        SitePageSection.objects.filter(
            page=SitePageSection.Page.DELIVERY,
            group="notes",
        ).order_by("display_order", "pk")
        if selected_page == SitePageSection.Page.DELIVERY
        else SitePageSection.objects.none()
    )
    delivery_methods_heading_instance = (
        delivery_methods_queryset.first()
        or SitePageSection(
            page=SitePageSection.Page.DELIVERY,
            group="methods",
            display_order=0,
        )
    )
    delivery_pickup_heading_instance = (
        delivery_pickup_queryset.first()
        or SitePageSection(
            page=SitePageSection.Page.DELIVERY,
            group="pickup",
            display_order=0,
        )
    )
    delivery_pickup_items_queryset = (
        delivery_pickup_queryset.exclude(
            pk=delivery_pickup_heading_instance.pk
        )
        if delivery_pickup_heading_instance.pk
        else delivery_pickup_queryset
    )
    delivery_help_heading_instance = (
        delivery_help_queryset.first()
        or SitePageSection(
            page=SitePageSection.Page.DELIVERY,
            group="notes",
            display_order=0,
        )
    )
    faq_questions_queryset = (
        SitePageSection.objects.filter(
            page=SitePageSection.Page.FAQ,
            group="questions",
        ).order_by("display_order", "pk")
        if selected_page == SitePageSection.Page.FAQ
        else SitePageSection.objects.none()
    )
    packaging_options_queryset = (
        SitePageSection.objects.filter(
            page=SitePageSection.Page.PACKAGING,
            group="options",
        ).order_by("display_order", "pk")
        if selected_page == SitePageSection.Page.PACKAGING
        else SitePageSection.objects.none()
    )
    packaging_extras_queryset = (
        SitePageSection.objects.filter(
            page=SitePageSection.Page.PACKAGING,
            group="extras",
        ).order_by("display_order", "pk")
        if selected_page == SitePageSection.Page.PACKAGING
        else SitePageSection.objects.none()
    )
    packaging_options_heading_instance = (
        packaging_options_queryset.first()
        or SitePageSection(
            page=SitePageSection.Page.PACKAGING,
            group="options",
            display_order=0,
        )
    )
    packaging_extras_heading_instance = (
        packaging_extras_queryset.first()
        or SitePageSection(
            page=SitePageSection.Page.PACKAGING,
            group="extras",
            display_order=0,
        )
    )

    if block:
        if request.method == "POST":
            form = SiteContentBlockForm(
                request.POST,
                request.FILES,
                instance=block,
            )
            if form.is_valid():
                saved_block = form.save()
                message = (
                    "Site content saved."
                    if request.LANGUAGE_CODE == "en"
                    else "Контент сайта сохранён."
                )
                messages.success(request, message)
                return redirect("site_content_edit", block_id=saved_block.pk)
        else:
            form = SiteContentBlockForm(instance=block)
    else:
        if request.method == "POST" and request.POST.get("action") == "save_home_slides":
            slide_queryset = HomeHeroSlide.objects.all()
            slide_initial = HOME_HERO_SLIDE_DEFAULTS[slide_queryset.count() :]
            SlideFormSet = modelformset_factory(
                HomeHeroSlide,
                form=HomeHeroSlideForm,
                formset=HomeHeroSlideBaseFormSet,
                extra=max(0, len(HOME_HERO_SLIDE_DEFAULTS) - slide_queryset.count()),
            )
            slide_formset = SlideFormSet(
                request.POST,
                request.FILES,
                queryset=slide_queryset,
                initial=slide_initial,
                prefix="slides",
            )
            if slide_formset.is_valid():
                slide_formset.save()
                messages.success(
                    request,
                    "Home banners saved." if request.LANGUAGE_CODE == "en" else "Баннеры главной страницы сохранены.",
                )
                return redirect(f"{request.path}?page={SiteContentBlock.Page.HOME}")
        elif request.method == "POST" and request.POST.get("action") == "save_page_content":
            content_form = SitePageContentForm(
                request.POST,
                request.FILES,
                instance=page_content,
                page=selected_page,
            )
            if content_form.is_valid():
                saved_content = content_form.save(commit=False)
                saved_content.page = selected_page
                saved_content.save()
                messages.success(
                    request,
                    "Page content saved." if request.LANGUAGE_CODE == "en" else "Контент страницы сохранён.",
                )
                return redirect(f"{request.path}?page={selected_page}")
        elif (
            request.method == "POST"
            and request.POST.get("action") == "save_contact_requisites"
            and selected_page == SitePageSection.Page.CONTACTS
        ):
            contact_requisites_form = ContactRequisitesForm(
                request.POST,
                instance=contact_requisites_instance,
                prefix="contact-requisites",
            )
            if contact_requisites_form.is_valid():
                requisites = contact_requisites_form.save(commit=False)
                requisites.page = SitePageSection.Page.CONTACTS
                requisites.group = "requisites"
                requisites.display_order = 0
                requisites.save()
                messages.success(
                    request,
                    "Contact requisites saved."
                    if request.LANGUAGE_CODE == "en"
                    else "Реквизиты сохранены.",
                )
                return redirect(
                    f"{request.path}?page={SitePageSection.Page.CONTACTS}"
                )
        elif (
            request.method == "POST"
            and request.POST.get("action") == "save_home_about"
            and selected_page == SitePageSection.Page.HOME
        ):
            home_about_form = HomeAboutSectionForm(
                request.POST,
                request.FILES,
                instance=home_about_instance,
                secondary_instance=home_about_secondary,
            )
            if home_about_form.is_valid():
                with transaction.atomic():
                    home_about_form.save()
                messages.success(
                    request,
                    "Home about section saved."
                    if request.LANGUAGE_CODE == "en"
                    else "Раздел «О компании» на главной странице сохранён.",
                )
                return redirect(f"{request.path}?page={SitePageSection.Page.HOME}")
        elif (
            request.method == "POST"
            and request.POST.get("action") == "save_about_story"
            and selected_page == SitePageSection.Page.ABOUT
        ):
            about_story_form = AboutStorySectionForm(
                request.POST,
                request.FILES,
                instance=about_story_instance,
            )
            if about_story_form.is_valid():
                about_story_form.save()
                messages.success(
                    request,
                    "About story saved."
                    if request.LANGUAGE_CODE == "en"
                    else "История страницы «О нас» сохранена.",
                )
                return redirect(f"{request.path}?page={SitePageSection.Page.ABOUT}")
        elif (
            request.method == "POST"
            and request.POST.get("action") == "save_about_promises"
            and selected_page == SitePageSection.Page.ABOUT
        ):
            AboutPromisesFormSet = modelformset_factory(
                SitePageSection,
                form=AboutPromiseForm,
                extra=0,
            )
            about_promises_formset = AboutPromisesFormSet(
                request.POST,
                request.FILES,
                queryset=about_promises_queryset,
                prefix="promises",
            )
            if about_promises_formset.is_valid():
                with transaction.atomic():
                    for promise in about_promises_formset.save(commit=False):
                        promise.page = SitePageSection.Page.ABOUT
                        promise.group = "promises"
                        promise.save()
                messages.success(
                    request,
                    "About principles saved."
                    if request.LANGUAGE_CODE == "en"
                    else "Принципы страницы «О нас» сохранены.",
                )
                return redirect(f"{request.path}?page={SitePageSection.Page.ABOUT}")
        elif (
            request.method == "POST"
            and request.POST.get("action") == "save_about_values"
            and selected_page == SitePageSection.Page.ABOUT
        ):
            AboutValuesFormSet = modelformset_factory(
                SitePageSection,
                form=AboutValueCardForm,
                extra=0,
            )
            about_values_formset = AboutValuesFormSet(
                request.POST,
                request.FILES,
                queryset=about_values_queryset,
                prefix="values",
            )
            about_values_heading_form = AboutValuesHeadingForm(
                request.POST,
                prefix="values-heading",
                instance=about_values_heading_instance,
            )
            if (
                about_values_formset.is_valid()
                and about_values_heading_form.is_valid()
            ):
                with transaction.atomic():
                    for value_card in about_values_formset.save(commit=False):
                        value_card.page = SitePageSection.Page.ABOUT
                        value_card.group = "values"
                        value_card.save()
                    heading_instance = (
                        SitePageSection.objects.filter(
                            page=SitePageSection.Page.ABOUT,
                            group="values",
                        )
                        .order_by("display_order", "pk")
                        .first()
                    )
                    if heading_instance is None:
                        heading_instance = SitePageSection(
                            page=SitePageSection.Page.ABOUT,
                            group="values",
                        )
                    for field_name, value in about_values_heading_form.cleaned_data.items():
                        setattr(heading_instance, field_name, value)
                    heading_instance.save()
                messages.success(
                    request,
                    "About values saved."
                    if request.LANGUAGE_CODE == "en"
                    else "Ценности страницы «О нас» сохранены.",
                )
                return redirect(f"{request.path}?page={SitePageSection.Page.ABOUT}")
        elif (
            request.method == "POST"
            and request.POST.get("action") == "save_faq_questions"
            and selected_page == SitePageSection.Page.FAQ
        ):
            FAQQuestionsFormSet = modelformset_factory(
                SitePageSection,
                form=FAQQuestionForm,
                extra=1,
                can_delete=True,
            )
            faq_questions_formset = FAQQuestionsFormSet(
                request.POST,
                queryset=faq_questions_queryset,
                prefix="faq-questions",
            )
            if faq_questions_formset.is_valid():
                with transaction.atomic():
                    questions = faq_questions_formset.save(commit=False)
                    for deleted_question in faq_questions_formset.deleted_objects:
                        deleted_question.delete()
                    for question in questions:
                        question.page = SitePageSection.Page.FAQ
                        question.group = "questions"
                        question.save()
                messages.success(
                    request,
                    "FAQ questions saved."
                    if request.LANGUAGE_CODE == "en"
                    else "Вопросы и ответы сохранены.",
                )
                return redirect(f"{request.path}?page={SitePageSection.Page.FAQ}")
        elif (
            request.method == "POST"
            and request.POST.get("action")
            in {"save_packaging_options", "save_packaging_extras"}
            and selected_page == SitePageSection.Page.PACKAGING
        ):
            is_options = request.POST.get("action") == "save_packaging_options"
            group = "options" if is_options else "extras"
            queryset = (
                packaging_options_queryset if is_options else packaging_extras_queryset
            )
            heading_instance = (
                packaging_options_heading_instance
                if is_options
                else packaging_extras_heading_instance
            )
            PackagingFormSet = modelformset_factory(
                SitePageSection,
                form=PackagingCardForm,
                extra=0,
            )
            packaging_heading_form = BusinessClientsSectionTitleForm(
                request.POST,
                instance=heading_instance,
                prefix=f"packaging-{group}-heading",
            )
            packaging_formset = PackagingFormSet(
                request.POST,
                request.FILES,
                queryset=queryset,
                prefix=f"packaging-{group}",
            )
            if is_options:
                packaging_options_heading_form = packaging_heading_form
                packaging_options_formset = packaging_formset
            else:
                packaging_extras_heading_form = packaging_heading_form
                packaging_extras_formset = packaging_formset
            if packaging_heading_form.is_valid() and packaging_formset.is_valid():
                with transaction.atomic():
                    for card in packaging_formset.save(commit=False):
                        card.page = SitePageSection.Page.PACKAGING
                        card.group = group
                        card.save()
                    heading = packaging_heading_form.save(commit=False)
                    heading.page = SitePageSection.Page.PACKAGING
                    heading.group = group
                    if heading.pk:
                        heading.save(
                            update_fields=(
                                "page",
                                "group",
                                "section_title",
                                "section_title_en",
                            )
                        )
                    else:
                        heading.save()
                messages.success(
                    request,
                    (
                        "Packaging options saved."
                        if is_options
                        else "Additional packaging options saved."
                    )
                    if request.LANGUAGE_CODE == "en"
                    else (
                        "Варианты упаковки сохранены."
                        if is_options
                        else "Дополнительные варианты упаковки сохранены."
                    ),
                )
                return redirect(f"{request.path}?page={SitePageSection.Page.PACKAGING}")
        elif (
            request.method == "POST"
            and request.POST.get("action") == "save_delivery_methods"
            and selected_page == SitePageSection.Page.DELIVERY
        ):
            DeliveryMethodsFormSet = modelformset_factory(
                SitePageSection,
                form=DeliveryMethodsCardForm,
                extra=0,
            )
            delivery_methods_heading_form = DeliverySectionHeadingForm(
                request.POST,
                instance=delivery_methods_heading_instance,
                prefix="delivery-methods-heading",
            )
            delivery_methods_formset = DeliveryMethodsFormSet(
                request.POST,
                request.FILES,
                queryset=delivery_methods_queryset,
                prefix="delivery-methods",
            )
            if (
                delivery_methods_heading_form.is_valid()
                and delivery_methods_formset.is_valid()
            ):
                with transaction.atomic():
                    for method in delivery_methods_formset.save(commit=False):
                        method.page = SitePageSection.Page.DELIVERY
                        method.group = "methods"
                        method.save()
                    heading = delivery_methods_heading_form.save(commit=False)
                    heading.page = SitePageSection.Page.DELIVERY
                    heading.group = "methods"
                    if heading.pk:
                        heading.save(
                            update_fields=(
                                "page",
                                "group",
                                "section_title",
                                "section_title_en",
                                "section_description",
                                "section_description_en",
                            )
                        )
                    else:
                        heading.save()
                messages.success(
                    request,
                    "Delivery methods saved."
                    if request.LANGUAGE_CODE == "en"
                    else "Способы доставки сохранены.",
                )
                return redirect(f"{request.path}?page={SitePageSection.Page.DELIVERY}")
        elif (
            request.method == "POST"
            and request.POST.get("action") == "save_delivery_pickup"
            and selected_page == SitePageSection.Page.DELIVERY
        ):
            DeliveryPickupFormSet = modelformset_factory(
                SitePageSection,
                form=DeliveryPickupDetailForm,
                extra=0,
            )
            delivery_pickup_heading_form = DeliveryPickupHeadingForm(
                request.POST,
                instance=delivery_pickup_heading_instance,
                prefix="delivery-pickup-heading",
            )
            delivery_pickup_formset = DeliveryPickupFormSet(
                request.POST,
                queryset=delivery_pickup_items_queryset,
                prefix="delivery-pickup",
            )
            if (
                delivery_pickup_heading_form.is_valid()
                and delivery_pickup_formset.is_valid()
            ):
                with transaction.atomic():
                    for detail in delivery_pickup_formset.save(commit=False):
                        detail.page = SitePageSection.Page.DELIVERY
                        detail.group = "pickup"
                        detail.save()
                    heading = delivery_pickup_heading_form.save(commit=False)
                    heading.page = SitePageSection.Page.DELIVERY
                    heading.group = "pickup"
                    if heading.pk:
                        heading.save(
                            update_fields=(
                                "page",
                                "group",
                                "section_title",
                                "section_title_en",
                                "section_description",
                                "section_description_en",
                                "value",
                                "value_en",
                                "url",
                            )
                        )
                    else:
                        heading.save()
                messages.success(
                    request,
                    "Pickup information saved."
                    if request.LANGUAGE_CODE == "en"
                    else "Информация о самовывозе сохранена.",
                )
                return redirect(f"{request.path}?page={SitePageSection.Page.DELIVERY}")
        elif (
            request.method == "POST"
            and request.POST.get("action") == "save_delivery_help"
            and selected_page == SitePageSection.Page.DELIVERY
        ):
            DeliveryHelpFormSet = modelformset_factory(
                SitePageSection,
                form=DeliveryHelpCardForm,
                extra=0,
            )
            delivery_help_heading_form = DeliverySectionHeadingForm(
                request.POST,
                instance=delivery_help_heading_instance,
                prefix="delivery-help-heading",
            )
            delivery_help_formset = DeliveryHelpFormSet(
                request.POST,
                queryset=delivery_help_queryset,
                prefix="delivery-help",
            )
            if (
                delivery_help_heading_form.is_valid()
                and delivery_help_formset.is_valid()
            ):
                with transaction.atomic():
                    for help_item in delivery_help_formset.save(commit=False):
                        help_item.page = SitePageSection.Page.DELIVERY
                        help_item.group = "notes"
                        help_item.save()
                    heading = delivery_help_heading_form.save(commit=False)
                    heading.page = SitePageSection.Page.DELIVERY
                    heading.group = "notes"
                    if heading.pk:
                        heading.save(
                            update_fields=(
                                "page",
                                "group",
                                "section_title",
                                "section_title_en",
                                "section_description",
                                "section_description_en",
                            )
                        )
                    else:
                        heading.save()
                messages.success(
                    request,
                    "Delivery help information saved."
                    if request.LANGUAGE_CODE == "en"
                    else "Полезная информация о доставке сохранена.",
                )
                return redirect(f"{request.path}?page={SitePageSection.Page.DELIVERY}")
        elif (
            request.method == "POST"
            and request.POST.get("action") == "save_partnership_directions"
            and selected_page == SitePageSection.Page.PARTNERSHIP
        ):
            PartnershipDirectionsFormSet = modelformset_factory(
                SitePageSection,
                form=PartnershipDirectionForm,
                extra=0,
            )
            partnership_directions_heading_form = (
                BusinessClientsSectionHeadingForm(
                    request.POST,
                    instance=partnership_directions_heading_instance,
                    prefix="partnership-directions-heading",
                )
            )
            partnership_directions_formset = PartnershipDirectionsFormSet(
                request.POST,
                request.FILES,
                queryset=partnership_directions_queryset,
                prefix="partnership-directions",
            )
            if (
                partnership_directions_heading_form.is_valid()
                and partnership_directions_formset.is_valid()
            ):
                with transaction.atomic():
                    for direction in partnership_directions_formset.save(
                        commit=False
                    ):
                        direction.page = SitePageSection.Page.PARTNERSHIP
                        direction.group = "directions"
                        direction.save()
                    heading = partnership_directions_heading_form.save(
                        commit=False
                    )
                    heading.page = SitePageSection.Page.PARTNERSHIP
                    heading.group = "directions"
                    if heading.pk:
                        heading.save(
                            update_fields=(
                                "page",
                                "group",
                                "section_title",
                                "section_title_en",
                                "section_description",
                                "section_description_en",
                            )
                        )
                    else:
                        heading.save()
                messages.success(
                    request,
                    "Partnership directions saved."
                    if request.LANGUAGE_CODE == "en"
                    else "Направления сотрудничества сохранены.",
                )
                return redirect(
                    f"{request.path}?page={SitePageSection.Page.PARTNERSHIP}"
                )
        elif (
            request.method == "POST"
            and request.POST.get("action") == "save_partnership_success"
            and selected_page == SitePageSection.Page.PARTNERSHIP
        ):
            PartnershipSuccessFormSet = modelformset_factory(
                SitePageSection,
                form=PartnershipSuccessForm,
                extra=0,
            )
            partnership_success_heading_form = BusinessClientsSectionHeadingForm(
                request.POST,
                instance=partnership_success_heading_instance,
                prefix="partnership-success-heading",
            )
            partnership_success_formset = PartnershipSuccessFormSet(
                request.POST,
                queryset=partnership_success_queryset,
                prefix="partnership-success",
            )
            if (
                partnership_success_heading_form.is_valid()
                and partnership_success_formset.is_valid()
            ):
                with transaction.atomic():
                    for achievement in partnership_success_formset.save(
                        commit=False
                    ):
                        achievement.page = SitePageSection.Page.PARTNERSHIP
                        achievement.group = "stats"
                        achievement.save()
                    heading = partnership_success_heading_form.save(
                        commit=False
                    )
                    heading.page = SitePageSection.Page.PARTNERSHIP
                    heading.group = "stats"
                    if heading.pk:
                        heading.save(
                            update_fields=(
                                "page",
                                "group",
                                "section_title",
                                "section_title_en",
                                "section_description",
                                "section_description_en",
                            )
                        )
                    else:
                        heading.save()
                messages.success(
                    request,
                    "Partnership success section saved."
                    if request.LANGUAGE_CODE == "en"
                    else "Раздел об успехах сотрудничества сохранён.",
                )
                return redirect(
                    f"{request.path}?page={SitePageSection.Page.PARTNERSHIP}"
                )
        elif (
            request.method == "POST"
            and request.POST.get("action") == "save_business_clients_steps"
            and selected_page == SitePageSection.Page.BUSINESS_CLIENTS
        ):
            BusinessClientsStepsFormSet = modelformset_factory(
                SitePageSection,
                form=BusinessClientsCardForm,
                extra=0,
            )
            business_clients_steps_heading_form = BusinessClientsSectionHeadingForm(
                request.POST,
                instance=business_clients_steps_heading_instance,
                prefix="steps-heading",
            )
            business_clients_steps_formset = BusinessClientsStepsFormSet(
                request.POST,
                queryset=business_clients_steps_queryset,
                prefix="steps",
            )
            if (
                business_clients_steps_heading_form.is_valid()
                and business_clients_steps_formset.is_valid()
            ):
                with transaction.atomic():
                    for step in business_clients_steps_formset.save(commit=False):
                        step.page = SitePageSection.Page.BUSINESS_CLIENTS
                        step.group = "steps"
                        step.save()
                    heading = business_clients_steps_heading_form.save(commit=False)
                    heading.page = SitePageSection.Page.BUSINESS_CLIENTS
                    heading.group = "steps"
                    if heading.pk:
                        heading.save(
                            update_fields=(
                                "page",
                                "group",
                                "section_title",
                                "section_title_en",
                                "section_description",
                                "section_description_en",
                            )
                        )
                    else:
                        heading.save()
                messages.success(
                    request,
                    "Business client process saved."
                    if request.LANGUAGE_CODE == "en"
                    else "Раздел о порядке работы сохранён.",
                )
                return redirect(
                    f"{request.path}?page={SitePageSection.Page.BUSINESS_CLIENTS}"
                )
        elif (
            request.method == "POST"
            and request.POST.get("action") == "save_business_clients_pricing"
            and selected_page == SitePageSection.Page.BUSINESS_CLIENTS
        ):
            BusinessClientsPricingFormSet = modelformset_factory(
                SitePageSection,
                form=BusinessClientsCardForm,
                extra=0,
            )
            BusinessClientsDeliveryFormSet = modelformset_factory(
                SitePageSection,
                form=BusinessClientsCardForm,
                extra=0,
            )
            business_clients_payment_heading_form = BusinessClientsPaymentHeadingForm(
                request.POST,
                instance=business_clients_payment_heading_instance,
                prefix="payment-heading",
            )
            business_clients_payment_formset = BusinessClientsPricingFormSet(
                request.POST,
                queryset=business_clients_payment_queryset,
                prefix="payment",
            )
            business_clients_delivery_heading_form = BusinessClientsSectionTitleForm(
                request.POST,
                instance=business_clients_delivery_heading_instance,
                prefix="delivery-heading",
            )
            business_clients_delivery_formset = BusinessClientsDeliveryFormSet(
                request.POST,
                queryset=business_clients_delivery_queryset,
                prefix="delivery",
            )
            if (
                business_clients_payment_heading_form.is_valid()
                and business_clients_payment_formset.is_valid()
                and business_clients_delivery_heading_form.is_valid()
                and business_clients_delivery_formset.is_valid()
            ):
                with transaction.atomic():
                    for card in business_clients_payment_formset.save(commit=False):
                        card.page = SitePageSection.Page.BUSINESS_CLIENTS
                        card.group = "payment"
                        card.save()
                    for card in business_clients_delivery_formset.save(commit=False):
                        card.page = SitePageSection.Page.BUSINESS_CLIENTS
                        card.group = "delivery"
                        card.save()
                    payment_heading = (
                        business_clients_payment_heading_form.save(commit=False)
                    )
                    payment_heading.page = SitePageSection.Page.BUSINESS_CLIENTS
                    payment_heading.group = "payment"
                    if payment_heading.pk:
                        payment_heading.save(
                            update_fields=(
                                "page",
                                "group",
                                "section_title",
                                "section_title_en",
                            )
                        )
                    else:
                        payment_heading.save()
                    delivery_heading = (
                        business_clients_delivery_heading_form.save(commit=False)
                    )
                    delivery_heading.page = SitePageSection.Page.BUSINESS_CLIENTS
                    delivery_heading.group = "delivery"
                    if delivery_heading.pk:
                        delivery_heading.save(
                            update_fields=(
                                "page",
                                "group",
                                "section_title",
                                "section_title_en",
                                "section_description",
                                "section_description_en",
                            )
                        )
                    else:
                        delivery_heading.save()
                messages.success(
                    request,
                    "Business client payment and delivery saved."
                    if request.LANGUAGE_CODE == "en"
                    else "Разделы оплаты и доставки сохранены.",
                )
                return redirect(
                    f"{request.path}?page={SitePageSection.Page.BUSINESS_CLIENTS}"
                )
        elif (
            request.method == "POST"
            and request.POST.get("action") == "save_business_clients_calculator"
            and selected_page == SitePageSection.Page.BUSINESS_CLIENTS
        ):
            business_clients_calculator_form = BusinessClientsCalculatorForm(
                request.POST,
                request.FILES,
                instance=business_clients_calculator_instance,
                prefix="calculator",
            )
            if business_clients_calculator_form.is_valid():
                calculator = business_clients_calculator_form.save(commit=False)
                calculator.page = SitePageSection.Page.BUSINESS_CLIENTS
                calculator.group = "calculator"
                calculator.save()
                messages.success(
                    request,
                    "Business client calculator saved."
                    if request.LANGUAGE_CODE == "en"
                    else "Раздел калькулятора заказа сохранён.",
                )
                return redirect(
                    f"{request.path}?page={SitePageSection.Page.BUSINESS_CLIENTS}"
                )
        elif (
            request.method == "POST"
            and request.POST.get("action") == "save_contact_details"
            and selected_page == SiteContentBlock.Page.ALL
        ):
            contact_details_form = ContactDetailsForm(
                request.POST,
                contacts=contact_details_queryset,
            )
            if contact_details_form.is_valid():
                with transaction.atomic():
                    contact_details_form.save()
                messages.success(
                    request,
                    "Contact details saved."
                    if request.LANGUAGE_CODE == "en"
                    else "Контактные данные сохранены.",
                )
                return redirect(
                    f"{request.path}?page={SiteContentBlock.Page.ALL}"
                )
        elif (
            request.method == "POST"
            and request.POST.get("action") == "save_business_clients_contacts"
            and selected_page == SiteContentBlock.Page.ALL
        ):
            business_clients_contact_form = ContactDetailsForm(
                request.POST,
                contacts=business_clients_contacts_queryset,
                page=SitePageSection.Page.BUSINESS_CLIENTS,
                group="contacts",
            )
            if business_clients_contact_form.is_valid():
                with transaction.atomic():
                    business_clients_contact_form.save()
                messages.success(
                    request,
                    "Corporate client contacts saved."
                    if request.LANGUAGE_CODE == "en"
                    else "Контакты для корпоративных клиентов сохранены.",
                )
                return redirect(f"{request.path}?page={SiteContentBlock.Page.ALL}")
        else:
            if selected_page == SiteContentBlock.Page.HOME:
                slide_queryset = HomeHeroSlide.objects.all()
                slide_initial = HOME_HERO_SLIDE_DEFAULTS[slide_queryset.count() :]
                SlideFormSet = modelformset_factory(
                    HomeHeroSlide,
                    form=HomeHeroSlideForm,
                    formset=HomeHeroSlideBaseFormSet,
                    extra=max(0, len(HOME_HERO_SLIDE_DEFAULTS) - slide_queryset.count()),
                )
                slide_formset = SlideFormSet(
                    queryset=slide_queryset,
                    initial=slide_initial,
                    prefix="slides",
                )
            elif selected_page in SitePageContent.Page.values:
                content_form = SitePageContentForm(
                    instance=page_content,
                    page=selected_page,
                )

    if selected_page == SitePageSection.Page.HOME and home_about_form is None:
        home_about_form = HomeAboutSectionForm(
            instance=home_about_instance,
            secondary_instance=home_about_secondary,
        )
    if (
        selected_page == SitePageSection.Page.CONTACTS
        and contact_requisites_form is None
    ):
        contact_requisites_form = ContactRequisitesForm(
            instance=contact_requisites_instance,
            prefix="contact-requisites",
        )
    if selected_page == SitePageSection.Page.ABOUT and about_story_form is None:
        about_story_form = AboutStorySectionForm(instance=about_story_instance)
    if selected_page == SitePageSection.Page.DELIVERY:
        if delivery_methods_heading_form is None:
            delivery_methods_heading_form = DeliverySectionHeadingForm(
                instance=delivery_methods_heading_instance,
                prefix="delivery-methods-heading",
            )
        if delivery_methods_formset is None:
            DeliveryMethodsFormSet = modelformset_factory(
                SitePageSection,
                form=DeliveryMethodsCardForm,
                extra=0,
            )
            delivery_methods_formset = DeliveryMethodsFormSet(
                queryset=delivery_methods_queryset,
                prefix="delivery-methods",
            )
        if delivery_pickup_heading_form is None:
            delivery_pickup_heading_form = DeliveryPickupHeadingForm(
                instance=delivery_pickup_heading_instance,
                prefix="delivery-pickup-heading",
            )
        if delivery_pickup_formset is None:
            DeliveryPickupFormSet = modelformset_factory(
                SitePageSection,
                form=DeliveryPickupDetailForm,
                extra=0,
            )
            delivery_pickup_formset = DeliveryPickupFormSet(
                queryset=delivery_pickup_items_queryset,
                prefix="delivery-pickup",
            )
        if delivery_help_heading_form is None:
            delivery_help_heading_form = DeliverySectionHeadingForm(
                instance=delivery_help_heading_instance,
                prefix="delivery-help-heading",
            )
        if delivery_help_formset is None:
            DeliveryHelpFormSet = modelformset_factory(
                SitePageSection,
                form=DeliveryHelpCardForm,
                extra=0,
            )
            delivery_help_formset = DeliveryHelpFormSet(
                queryset=delivery_help_queryset,
                prefix="delivery-help",
            )
    if selected_page == SitePageSection.Page.FAQ and faq_questions_formset is None:
        FAQQuestionsFormSet = modelformset_factory(
            SitePageSection,
            form=FAQQuestionForm,
            extra=1,
            can_delete=True,
        )
        faq_questions_formset = FAQQuestionsFormSet(
            queryset=faq_questions_queryset,
            initial=[{"display_order": faq_questions_queryset.count() + 1}],
            prefix="faq-questions",
        )
    if selected_page == SitePageSection.Page.PACKAGING:
        PackagingFormSet = modelformset_factory(
            SitePageSection,
            form=PackagingCardForm,
            extra=0,
        )
        if packaging_options_heading_form is None:
            packaging_options_heading_form = BusinessClientsSectionTitleForm(
                instance=packaging_options_heading_instance,
                prefix="packaging-options-heading",
            )
        if packaging_options_formset is None:
            packaging_options_formset = PackagingFormSet(
                queryset=packaging_options_queryset,
                prefix="packaging-options",
            )
        if packaging_extras_heading_form is None:
            packaging_extras_heading_form = BusinessClientsSectionTitleForm(
                instance=packaging_extras_heading_instance,
                prefix="packaging-extras-heading",
            )
        if packaging_extras_formset is None:
            packaging_extras_formset = PackagingFormSet(
                queryset=packaging_extras_queryset,
                prefix="packaging-extras",
            )
    if selected_page == SitePageSection.Page.PARTNERSHIP:
        if partnership_directions_heading_form is None:
            partnership_directions_heading_form = (
                BusinessClientsSectionHeadingForm(
                    instance=partnership_directions_heading_instance,
                    prefix="partnership-directions-heading",
                )
            )
        if partnership_directions_formset is None:
            PartnershipDirectionsFormSet = modelformset_factory(
                SitePageSection,
                form=PartnershipDirectionForm,
                extra=0,
            )
            partnership_directions_formset = PartnershipDirectionsFormSet(
                queryset=partnership_directions_queryset,
                prefix="partnership-directions",
            )
        if partnership_success_heading_form is None:
            partnership_success_heading_form = BusinessClientsSectionHeadingForm(
                instance=partnership_success_heading_instance,
                prefix="partnership-success-heading",
            )
        if partnership_success_formset is None:
            PartnershipSuccessFormSet = modelformset_factory(
                SitePageSection,
                form=PartnershipSuccessForm,
                extra=0,
            )
            partnership_success_formset = PartnershipSuccessFormSet(
                queryset=partnership_success_queryset,
                prefix="partnership-success",
            )
    if selected_page == SitePageSection.Page.BUSINESS_CLIENTS:
        if business_clients_steps_heading_form is None:
            business_clients_steps_heading_form = BusinessClientsSectionHeadingForm(
                instance=business_clients_steps_heading_instance,
                prefix="steps-heading",
            )
        if business_clients_steps_formset is None:
            BusinessClientsStepsFormSet = modelformset_factory(
                SitePageSection,
                form=BusinessClientsCardForm,
                extra=0,
            )
            business_clients_steps_formset = BusinessClientsStepsFormSet(
                queryset=business_clients_steps_queryset,
                prefix="steps",
            )
        if business_clients_payment_heading_form is None:
            business_clients_payment_heading_form = BusinessClientsPaymentHeadingForm(
                instance=business_clients_payment_heading_instance,
                prefix="payment-heading",
            )
        if business_clients_payment_formset is None:
            BusinessClientsPricingFormSet = modelformset_factory(
                SitePageSection,
                form=BusinessClientsCardForm,
                extra=0,
            )
            business_clients_payment_formset = BusinessClientsPricingFormSet(
                queryset=business_clients_payment_queryset,
                prefix="payment",
            )
        if business_clients_delivery_heading_form is None:
            business_clients_delivery_heading_form = (
                BusinessClientsSectionTitleForm(
                    instance=business_clients_delivery_heading_instance,
                    prefix="delivery-heading",
                )
            )
        if business_clients_delivery_formset is None:
            BusinessClientsDeliveryFormSet = modelformset_factory(
                SitePageSection,
                form=BusinessClientsCardForm,
                extra=0,
            )
            business_clients_delivery_formset = BusinessClientsDeliveryFormSet(
                queryset=business_clients_delivery_queryset,
                prefix="delivery",
            )
        if business_clients_calculator_form is None:
            business_clients_calculator_form = BusinessClientsCalculatorForm(
                instance=business_clients_calculator_instance,
                prefix="calculator",
            )

    if selected_page == SitePageSection.Page.ABOUT:
        if about_promises_formset is None:
            AboutPromisesFormSet = modelformset_factory(
                SitePageSection,
                form=AboutPromiseForm,
                extra=0,
            )
            about_promises_formset = AboutPromisesFormSet(
                queryset=about_promises_queryset,
                prefix="promises",
            )
        if about_values_formset is None:
            AboutValuesFormSet = modelformset_factory(
                SitePageSection,
                form=AboutValueCardForm,
                extra=0,
            )
            about_values_formset = AboutValuesFormSet(
                queryset=about_values_queryset,
                prefix="values",
            )
        if about_values_heading_form is None:
            about_values_heading_form = AboutValuesHeadingForm(
                instance=about_values_heading_instance,
                prefix="values-heading",
            )
    if selected_page == SiteContentBlock.Page.ALL and contact_details_form is None:
        contact_details_form = ContactDetailsForm(
            contacts=contact_details_queryset,
        )
    if (
        selected_page == SiteContentBlock.Page.ALL
        and business_clients_contact_form is None
    ):
        business_clients_contact_form = ContactDetailsForm(
            contacts=business_clients_contacts_queryset,
            page=SitePageSection.Page.BUSINESS_CLIENTS,
            group="contacts",
        )

    page_form = SitePageContentForm(
        instance=page_content,
        page=selected_page if selected_page in SitePageContent.Page.values else SitePageContent.Page.CATALOG,
    ) if not block and selected_page in SitePageContent.Page.values else None
    if content_form is None:
        content_form = page_form

    return render(
        request,
        "core/site_content_manager.html",
        {
            "form": form,
            "page_form": content_form,
            "slide_formset": slide_formset,
            "home_about_form": home_about_form,
            "about_story_form": about_story_form,
            "about_promises_formset": about_promises_formset,
            "about_values_formset": about_values_formset,
            "about_values_heading_form": about_values_heading_form,
            "contact_details_form": contact_details_form,
            "contact_requisites_form": contact_requisites_form,
            "delivery_methods_heading_form": delivery_methods_heading_form,
            "delivery_methods_formset": delivery_methods_formset,
            "delivery_pickup_heading_form": delivery_pickup_heading_form,
            "delivery_pickup_formset": delivery_pickup_formset,
            "delivery_help_heading_form": delivery_help_heading_form,
            "delivery_help_formset": delivery_help_formset,
            "faq_questions_formset": faq_questions_formset,
            "packaging_options_heading_form": packaging_options_heading_form,
            "packaging_options_formset": packaging_options_formset,
            "packaging_extras_heading_form": packaging_extras_heading_form,
            "packaging_extras_formset": packaging_extras_formset,
            "business_clients_contact_form": business_clients_contact_form,
            "business_clients_steps_heading_form": business_clients_steps_heading_form,
            "business_clients_steps_formset": business_clients_steps_formset,
            "business_clients_payment_heading_form": business_clients_payment_heading_form,
            "business_clients_payment_formset": business_clients_payment_formset,
            "business_clients_delivery_heading_form": business_clients_delivery_heading_form,
            "business_clients_delivery_formset": business_clients_delivery_formset,
            "business_clients_calculator_form": business_clients_calculator_form,
            "partnership_directions_heading_form": partnership_directions_heading_form,
            "partnership_directions_formset": partnership_directions_formset,
            "partnership_success_heading_form": partnership_success_heading_form,
            "partnership_success_formset": partnership_success_formset,
            "editing_block": block,
            "selected_page": selected_page,
            "selected_page_is_dynamic": selected_page in {
                SiteContentBlock.Page.CATEGORY,
                SiteContentBlock.Page.PRODUCT,
            },
            "page_selector": SiteContentBlockForm(initial={"page": selected_page}),
        },
    )


ADMIN_SECTION_CONFIG = {
    "products": {
        "model": Product,
        "form": ProductEditorForm,
        "view_perm": "catalog.view_product",
        "add_perm": "catalog.add_product",
        "change_perm": "catalog.change_product",
        "search_fields": ("name", "name_en", "category__name"),
        "title": ("Products", "Товары"),
        "add_title": ("Add a product", "Добавить товар"),
        "kind": "product",
    },
    "categories": {
        "model": Category,
        "form": CategoryEditorForm,
        "view_perm": "catalog.view_category",
        "add_perm": "catalog.add_category",
        "change_perm": "catalog.change_category",
        "search_fields": ("name", "name_en", "slug"),
        "title": ("Categories", "Категории"),
        "add_title": ("Add a category", "Добавить категорию"),
        "kind": "category",
    },
    "filters": {
        "model": ProductFilterOption,
        "form": ProductFilterOptionEditorForm,
        "view_perm": "catalog.view_productfilteroption",
        "add_perm": "catalog.add_productfilteroption",
        "change_perm": "catalog.change_productfilteroption",
        "search_fields": ("label", "label_en", "value"),
        "title": ("Product filters", "Фильтры товаров"),
        "add_title": ("Add a filter option", "Добавить фильтр"),
        "kind": "filter",
    },
    "orders": {
        "model": Preorder,
        "view_perm": "core.view_preorder",
        "change_perm": "core.change_preorder",
        "search_fields": ("name", "email", "phone"),
        "title": ("Orders", "Заказы"),
        "kind": "order",
    },
    "customers": {
        "model": CustomerProfile,
        "view_perm": "user.view_customerprofile",
        "search_fields": (
            "user__username",
            "user__email",
            "company_name",
            "inn",
            "contact_name",
        ),
        "title": ("Customers", "Клиенты"),
        "kind": "customer",
    },
    "messages": {
        "model": FeedbackSubmission,
        "view_perm": "core.view_feedbacksubmission",
        "change_perm": "core.change_feedbacksubmission",
        "search_fields": ("name", "email", "subject", "message"),
        "title": ("Customer messages", "Обращения клиентов"),
        "kind": "message",
    },
}


@staff_member_required(login_url="accounts:login")
def admin_section(request, section, object_id=None, new=False):
    config = ADMIN_SECTION_CONFIG.get(section)
    if config is None:
        raise PermissionDenied

    user = request.user
    can_view = user.has_perm(config["view_perm"])
    can_add = bool(config.get("add_perm") and user.has_perm(config["add_perm"]))
    can_change = bool(
        config.get("change_perm") and user.has_perm(config["change_perm"])
    )
    if new and not can_add:
        raise PermissionDenied
    if not new and not can_view:
        raise PermissionDenied
    if object_id is not None and not can_change and section != "customers":
        raise PermissionDenied

    model = config["model"]
    instance = (
        get_object_or_404(model, pk=object_id)
        if object_id is not None
        else None
    )
    status_form = None
    if section in ("orders", "messages") and instance is not None:
        form_class = (
            AdminOrderStatusForm if section == "orders" else AdminFeedbackStatusForm
        )
        if request.method == "POST":
            if not can_change:
                raise PermissionDenied
            status_form = form_class(
                request.POST,
                language_code=request.LANGUAGE_CODE,
                initial={"status": instance.status},
            )
            if status_form.is_valid():
                instance.status = status_form.cleaned_data["status"]
                instance.save(update_fields=("status",))
                messages.success(
                    request,
                    "Status saved." if request.LANGUAGE_CODE == "en" else "Статус сохранён.",
                )
                return redirect("admin_section_edit", section=section, object_id=instance.pk)
        else:
            status_form = form_class(
                language_code=request.LANGUAGE_CODE,
                initial={"status": instance.status},
            )

    form_class = config.get("form")
    form = None
    if form_class and (new or instance is not None):
        if request.method == "POST":
            if not (can_add if new else can_change):
                raise PermissionDenied
            form = form_class(request.POST, request.FILES, instance=instance)
            if form.is_valid():
                saved = form.save()
                messages.success(
                    request,
                    "Changes saved." if request.LANGUAGE_CODE == "en" else "Изменения сохранены.",
                )
                if can_change:
                    return redirect(
                        "admin_section_edit",
                        section=section,
                        object_id=saved.pk,
                    )
                if can_view:
                    return redirect("admin_section", section=section)
                return redirect("admin_dashboard")
        else:
            form = form_class(instance=instance)

    items = model.objects.all()
    if section == "products":
        items = items.select_related("category")
    elif section == "customers":
        items = items.select_related("user")
    search_query = request.GET.get("q", "").strip()
    if search_query:
        from django.db.models import Q

        search = Q()
        for field in config["search_fields"]:
            search |= Q(**{f"{field}__icontains": search_query})
        items = items.filter(search)

    title_index = 0 if request.LANGUAGE_CODE == "en" else 1
    return render(
        request,
        "core/admin_section.html",
        {
            "section": section,
            "section_kind": config["kind"],
            "section_title": config["title"][title_index],
            "page_title": (
                config["add_title"][title_index]
                if new
                else str(instance) if instance is not None and form is not None
                else config["title"][title_index]
            ),
            "items": items,
            "search_query": search_query,
            "form": form,
            "status_form": status_form,
            "object": instance,
            "is_new": new,
            "can_add": can_add,
            "can_change": can_change,
            "messages": messages.get_messages(request),
        },
    )


@staff_member_required(login_url="accounts:login")
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


@staff_member_required(login_url="accounts:login")
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


def business_clients(request):
    return render(request, "core/business_clients.html")


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
