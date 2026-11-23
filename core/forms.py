from pathlib import Path
import json
from decimal import Decimal, InvalidOperation

from django import forms
from django.forms import BaseModelFormSet
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import get_language

from .calculator import (
    COATING_CHOICES,
    DELIVERY_CHOICES,
    FLAVOR_CHOICES,
    PACKAGING_CHOICES,
    PAYMENT_CHOICES,
    SHAPE_CHOICES,
    SIZE_CHOICES,
    is_coating_modifier_group,
    normalize_calculator_pricing,
    localized_choices,
    localized_calculator_options,
)
from .models import (
    FeedbackSubmission,
    HomeHeroSlide,
    Preorder,
    SiteContentBlock,
    SiteFavicon,
    SitePageContent,
    SitePageSection,
)

MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024
MAX_ATTACHMENT_COUNT = 5

SITE_PAGE_CONTENT_DEFAULTS = {
    SitePageContent.Page.ABOUT: {
        "eyebrow": "История «Вкусно Да Сладко»",
        "eyebrow_en": "The story of Vkusno Da Sladko",
        "title": "О нас",
        "title_en": "About us",
        "subtitle": "Вкусно Да Сладко — кондитерские изделия, созданные с вниманием к деталям.",
        "subtitle_en": "Vkusno Da Sladko — confectionery made with care in every detail.",
        "description": "Мы создаём кондитерские изделия, которые превращают идеи в сладкие истории. Для нас важно не просто испечь пряник, а вложить в него смысл, эстетику и внимание к каждой детали.",
        "description_en": "We create confectionery that turns ideas into sweet stories. For us, it is about more than baking gingerbread: every piece carries meaning, beauty, and care in every detail.",
    },
    SitePageContent.Page.BUSINESS_CLIENTS: {
        "eyebrow": "Главная / Корпоративным клиентам",
        "eyebrow_en": "Home / Business clients",
        "title": "Корпоративным клиентам",
        "title_en": "Corporate clients",
        "subtitle": "Индивидуальные решения для вашего бизнеса",
        "subtitle_en": "Individual solutions for your business",
        "description": "Создаём кондитерские изделия, которые подчёркивают ценность вашей компании и оставляют приятные впечатления у сотрудников, партнёров и клиентов.",
        "description_en": "We create confectionery items that highlight the value of your company and leave pleasant impressions on your colleagues, partners, and clients.",
    },
    SitePageContent.Page.PARTNERSHIP: {
        "eyebrow": "Главная / Партнёрство",
        "eyebrow_en": "Home / Partnership",
        "title": "Партнёрство с «Вкусно Да Сладко»",
        "title_en": "Partner with Vkusno Da Sladko",
        "subtitle": "Открыты к сотрудничеству и новым возможностям",
        "subtitle_en": "Open to collaboration and new opportunities",
        "description": "Мы ценим интерес к нашему бренду и всегда открыты к сотрудничеству. Заполните форму, и наш менеджер свяжется с вами для обсуждения перспектив партнёрства.",
        "description_en": "We value your interest in our brand and welcome new partnerships. Get in touch, and our manager will discuss the opportunities with you.",
    },
    SitePageContent.Page.CONTACTS: {
        "title": "Контакты",
        "title_en": "Contact",
        "description": "Мы всегда на связи и рады ответить на ваши вопросы, помочь с выбором и обсудить заказ.",
        "description_en": "We are always happy to answer your questions, help you choose, and discuss your order.",
    },
    SitePageContent.Page.DELIVERY: {
        "title": "Доставка и самовывоз",
        "title_en": "Delivery and pickup",
        "description": "Доставляем заказы по всей России и предлагаем удобный самовывоз в Москве.",
        "description_en": "We deliver across Russia and offer convenient pickup in Moscow.",
    },
    SitePageContent.Page.FAQ: {
        "title": "ЧАСТЫЕ ВОПРОСЫ",
        "title_en": "FREQUENTLY ASKED QUESTIONS",
    },
    SitePageContent.Page.FEEDBACK: {
        "eyebrow": "Мы на связи",
        "eyebrow_en": "We're here to help",
        "title": "Обратная связь",
        "title_en": "Feedback",
        "description": "Есть вопрос или идея? Напишите нам — мы внимательно прочитаем ваше сообщение и ответим по электронной почте.",
        "description_en": "Have a question or an idea? Send us a message. We will read it carefully and reply by email.",
    },
    SitePageContent.Page.PACKAGING: {
        "title": "Варианты упаковки",
        "title_en": "Packaging options",
        "description": "Подбираем упаковку под ваш повод, формат заказа и фирменный стиль.",
        "description_en": "We choose packaging to suit your occasion, order, and brand style.",
    },
    SitePageContent.Page.CATALOG: {
        "title": "Каталог",
        "title_en": "Catalog",
    },
    SitePageContent.Page.CATEGORIES: {
        "eyebrow": "Каталог подарков",
        "eyebrow_en": "Gift catalog",
        "title": "Все категории",
        "title_en": "All categories",
        "description": "Выберите категорию, чтобы посмотреть подходящие подарки.",
        "description_en": "Choose a category to explore suitable gifts.",
    },
}
SITE_PAGE_EDITABLE_FIELDS = {
    SitePageContent.Page.ABOUT: (
        "eyebrow", "eyebrow_en", "title", "title_en", "subtitle", "subtitle_en",
        "description", "description_en", "image",
    ),
    SitePageContent.Page.BUSINESS_CLIENTS: (
        "eyebrow", "eyebrow_en", "title", "title_en", "subtitle", "subtitle_en",
        "description", "description_en", "image",
    ),
    SitePageContent.Page.PARTNERSHIP: (
        "eyebrow", "eyebrow_en", "title", "title_en", "subtitle", "subtitle_en",
        "description", "description_en", "image",
    ),
    SitePageContent.Page.CONTACTS: (
        "title", "title_en", "description", "description_en", "image",
    ),
    SitePageContent.Page.DELIVERY: (
        "title", "title_en", "description", "description_en", "image",
    ),
    SitePageContent.Page.FAQ: ("title", "title_en"),
    SitePageContent.Page.FEEDBACK: (
        "eyebrow", "eyebrow_en", "title", "title_en", "description",
        "description_en", "image",
    ),
    SitePageContent.Page.PACKAGING: (
        "title", "title_en", "description", "description_en", "image",
    ),
    SitePageContent.Page.CATALOG: ("title", "title_en", "description", "description_en"),
    SitePageContent.Page.CATEGORIES: (
        "eyebrow", "eyebrow_en", "title", "title_en",
        "description", "description_en",
    ),
}

HOME_HERO_SLIDE_DEFAULTS = (
    {
        "eyebrow": "Авторские решения для вашего бизнеса",
        "eyebrow_en": "Made for your business",
        "title": "Подарки, созданные с душой",
        "title_en": "Gifts, made with heart",
        "description": "Продуманные до мелочей наборы, которые говорят о главном и запоминаются надолго.",
        "description_en": "Thoughtfully curated sets that say what matters and leave a lasting impression.",
        "display_order": 0,
        "is_active": True,
    },
    {
        "eyebrow": "Маленький повод для радости",
        "eyebrow_en": "A little reason to celebrate",
        "title": "Тёплые моменты в каждой детали",
        "title_en": "Warm moments in every detail",
        "description": "Сладкие комплименты и красивые подарки для важных встреч и добрых слов.",
        "description_en": "Sweet treats and thoughtful gifts for meaningful meetings and kind words.",
        "display_order": 1,
        "is_active": True,
    },
    {
        "eyebrow": "Для команды и партнёров",
        "eyebrow_en": "For your team and partners",
        "title": "Внимание, которое объединяет",
        "title_en": "Gifts that bring people together",
        "description": "Создаём корпоративные наборы с заботой о вашем бренде и каждом получателе.",
        "description_en": "We create corporate gift sets with care for your brand and every recipient.",
        "display_order": 2,
        "is_active": True,
    },
)

ALLOWED_ATTACHMENT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            return []
        files = data if isinstance(data, (list, tuple)) else [data]
        if len(files) > MAX_ATTACHMENT_COUNT:
            message = (
                f"You can upload no more than {MAX_ATTACHMENT_COUNT} files."
                if get_language() == "en"
                else f"Можно загрузить не более {MAX_ATTACHMENT_COUNT} файлов."
            )
            raise ValidationError(message)
        cleaned_files = []
        for uploaded_file in files:
            cleaned_file = super().clean(uploaded_file, initial)
            extension = Path(cleaned_file.name).suffix.lower()
            if extension not in ALLOWED_ATTACHMENT_EXTENSIONS:
                message = (
                    "Allowed file types are JPG, PNG, WEBP, and PDF."
                    if get_language() == "en"
                    else "Допустимы изображения JPG, PNG, WEBP и документы PDF."
                )
                raise ValidationError(message)
            if cleaned_file.size > MAX_ATTACHMENT_SIZE:
                message = (
                    "Each file must be no larger than 10 MB."
                    if get_language() == "en"
                    else "Размер каждого файла не должен превышать 10 МБ."
                )
                raise ValidationError(message)
            cleaned_files.append(cleaned_file)
        return cleaned_files


class PreorderForm(forms.Form):
    product = forms.ChoiceField(required=False)
    flavor = forms.ChoiceField(choices=FLAVOR_CHOICES, required=False)
    quantity = forms.IntegerField(min_value=1, max_value=10000, initial=100)
    size = forms.ChoiceField(choices=SIZE_CHOICES)
    shape = forms.ChoiceField(choices=SHAPE_CHOICES, required=False)
    coating = forms.ChoiceField(choices=COATING_CHOICES, required=False)
    packaging = forms.ChoiceField(choices=PACKAGING_CHOICES, required=False)
    delivery = forms.ChoiceField(choices=DELIVERY_CHOICES)
    payment = forms.ChoiceField(choices=PAYMENT_CHOICES)
    modifiers = forms.CharField(required=False, widget=forms.HiddenInput())
    name = forms.CharField(max_length=120)
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "Введите email"})
    )
    phone = forms.CharField(
        max_length=32,
        widget=forms.TextInput(attrs={"type": "tel", "placeholder": "+7 (000) 000-00-00"}),
    )
    delivery_date = forms.DateField(
        required=False,
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    address = forms.CharField(
        max_length=300,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Адрес, временной интервал"}),
    )
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 3, "placeholder": "Напишите комментарий"}
        ),
    )
    attachments = MultipleFileField(required=False)
    consent_given = forms.BooleanField(
        required=True,
        error_messages={"required": "Необходимо дать согласие на обработку данных."},
    )

    def __init__(
        self,
        *args,
        product_choices=None,
        option_choices=None,
        pricing=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        option_choices = option_choices or {}
        if product_choices is not None:
            self.fields["product"].choices = product_choices
        self.fields["product"].initial = (
            self.fields["product"].choices[0][0]
            if self.fields["product"].choices
            else ""
        )
        self.pricing = normalize_calculator_pricing(pricing)
        selected_product_value = (
            self.data.get("product")
            if self.is_bound
            else self.fields["product"].initial
        )
        selected_product = next(
            (
                product
                for product in self.pricing["products"]
                if product["value"] == selected_product_value
            ),
            self.pricing["products"][0],
        )
        self.fields["size"].choices = tuple(
            (size["value"], size["label"])
            for size in selected_product["sizes"]
        )
        self.fields["size"].initial = (
            self.fields["size"].choices[0][0]
            if self.fields["size"].choices
            else ""
        )
        self.fields["payment"].choices = tuple(
            (method["value"], method["label_en"] if get_language() == "en" else method["label"])
            for method in self.pricing["payment_methods"]
        )
        self.fields["payment"].initial = (
            self.fields["payment"].choices[0][0]
            if self.fields["payment"].choices
            else ""
        )
        for field_name, group, option_group in (
            ("flavor", "flavor", "flavors"),
            ("shape", "shape", "shapes"),
            ("coating", "coating", "coatings"),
            ("packaging", "packaging", "packaging"),
            ("delivery", "delivery", None),
            ("payment", "payment", None),
        ):
            if option_group in option_choices:
                self.fields[field_name].choices = option_choices[option_group]
                if self.fields[field_name].choices:
                    self.fields[field_name].initial = self.fields[field_name].choices[0][0]
            else:
                self.fields[field_name].choices = localized_choices(
                    self.fields[field_name].choices,
                    group,
                )
        self.fields["name"].widget.attrs["placeholder"] = "Как к вам обращаться"
        self.fields["quantity"].initial = 100
        for field_name, default, option_group in (
            ("flavor", "classic", "flavors"),
            ("shape", "heart", "shapes"),
            ("coating", "icing", "coatings"),
            ("packaging", "ribbon", "packaging"),
            ("delivery", "moscow", None),
            ("payment", "organization", None),
        ):
            if option_group not in option_choices:
                available_values = {
                    value for value, _ in self.fields[field_name].choices
                }
                self.fields[field_name].initial = (
                    default
                    if default in available_values
                    else next(iter(available_values), "")
                )
        if get_language() == "en":
            self.fields["consent_given"].error_messages["required"] = (
                "You must agree to the processing of your personal data."
            )
        if get_language() == "en":
            self.fields["name"].widget.attrs["placeholder"] = "Your name"
            self.fields["email"].widget.attrs["placeholder"] = "Enter your email"
            self.fields["address"].widget.attrs["placeholder"] = "Address and preferred time"
            self.fields["comment"].widget.attrs["placeholder"] = "Add a comment"

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("product") and self.fields["product"].choices:
            cleaned_data["product"] = self.fields["product"].choices[0][0]
        selected_product = next(
            (
                product
                for product in self.pricing["products"]
                if product["value"] == cleaned_data.get("product")
            ),
            None,
        )
        if selected_product:
            data = cleaned_data.get("modifiers", "")
            try:
                modifiers = json.loads(data) if data else {}
            except json.JSONDecodeError:
                modifiers = None
            if modifiers is None or not isinstance(modifiers, dict):
                self.add_error("modifiers", "Invalid modifier selection.")
            else:
                legacy_values = {
                    "flavors": cleaned_data.get("flavor"),
                    "shapes": cleaned_data.get("shape"),
                    "coatings": cleaned_data.get("coating"),
                    "packaging": cleaned_data.get("packaging"),
                }
                for group in selected_product["modifier_groups"]:
                    selected = modifiers.get(group["value"])
                    if not selected:
                        selected = legacy_values.get(group["value"])
                    if not selected and group["options"]:
                        selected = group["options"][0]["value"]
                    if selected not in {
                        option["value"] for option in group["options"]
                    }:
                        self.add_error("modifiers", "Select a valid modifier option.")
                        break
                    modifiers[group["value"]] = selected
                if set(modifiers) - {
                    group["value"] for group in selected_product["modifier_groups"]
                }:
                    self.add_error("modifiers", "Select valid modifier options.")
                cleaned_data["modifiers"] = modifiers
        if (
            cleaned_data.get("delivery") != "pickup"
            and not cleaned_data.get("address")
        ):
            message = (
                "Enter a delivery address."
                if get_language() == "en"
                else "Укажите адрес доставки."
            )
            self.add_error("address", message)
        return cleaned_data


class FeedbackForm(forms.Form):
    name = forms.CharField(
        max_length=120,
        label="Ваше имя",
        widget=forms.TextInput(attrs={"placeholder": "Как к вам обращаться"}),
    )
    email = forms.EmailField(
        label="Электронная почта",
        widget=forms.EmailInput(attrs={"placeholder": "name@example.com"}),
    )
    phone = forms.CharField(
        max_length=32,
        required=False,
        label="Телефон",
        widget=forms.TextInput(
            attrs={
                "type": "tel",
                "autocomplete": "tel",
                "placeholder": "+7 900 000-00-00",
            }
        ),
    )
    subject = forms.CharField(
        max_length=160,
        label="Тема обращения",
        widget=forms.TextInput(attrs={"placeholder": "Например, вопрос о заказе"}),
    )
    message = forms.CharField(
        max_length=5000,
        label="Сообщение",
        widget=forms.Textarea(
            attrs={"rows": 6, "placeholder": "Расскажите, чем мы можем помочь"}
        ),
    )
    consent_given = forms.BooleanField(
        required=True,
        label="Согласен(на) на обработку персональных данных",
        error_messages={"required": "Необходимо дать согласие на обработку данных."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if get_language() == "en":
            labels = {
                "name": "Your name",
                "email": "Email",
                "phone": "Phone number",
                "subject": "Subject",
                "message": "Message",
                "consent_given": "I agree to the processing of my personal data",
            }
            for field_name, label in labels.items():
                self.fields[field_name].label = label
            self.fields["name"].widget.attrs["placeholder"] = "Your name"
            self.fields["subject"].widget.attrs["placeholder"] = "For example, a question about an order"
            self.fields["message"].widget.attrs["placeholder"] = "Tell us how we can help"
            self.fields["consent_given"].error_messages["required"] = (
                "You must agree to the processing of your personal data."
            )


class SiteFaviconForm(forms.ModelForm):
    class Meta:
        model = SiteFavicon
        fields = ("image",)
        widgets = {
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "site-content-form-control",
                    "accept": "image/jpeg,image/png,image/webp",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        english = (get_language() or "").startswith("en")
        self.fields["image"].label = "Favicon image" if english else "Файл фавикона"
        self.fields["image"].help_text = (
            "Upload a square PNG, JPG, or WebP image. Clear it to use the default favicon."
            if english
            else "Загрузите квадратное изображение PNG, JPG или WebP. Очистите файл, чтобы вернуть стандартный фавикон."
        )


class SiteContentBlockForm(forms.ModelForm):
    class Meta:
        model = SiteContentBlock
        fields = (
            "page",
            "title",
            "title_en",
            "description",
            "description_en",
            "image",
            "display_order",
            "is_active",
        )
        widgets = {
            "page": forms.Select(attrs={"class": "site-content-form-control"}),
            "title": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "title_en": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 5}
            ),
            "description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 5}
            ),
            "image": forms.ClearableFileInput(
                attrs={"class": "site-content-form-control"}
            ),
            "display_order": forms.NumberInput(
                attrs={"class": "site-content-form-control", "min": 0}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "site-content-form-checkbox"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance._state.adding:
            self.initial.setdefault("page", SiteContentBlock.Page.CATALOG)
        if (get_language() or "").startswith("en"):
            self.fields["page"].label = "Website page"
            self.fields["page"].choices = [
                (value, label)
                for value, label in (
                    ("all", "All pages"),
                    ("home", "Home"),
                    ("about", "About us"),
                    ("business_clients", "Corporate clients"),
                    ("corporate", "Partnership"),
                    ("contacts", "Contacts"),
                    ("delivery", "Delivery"),
                    ("faq", "FAQ"),
                    ("feedback", "Feedback"),
                    ("packaging", "Packaging"),
                    ("catalog", "Catalog"),
                    ("categories", "Category overview"),
                    ("category", "Category page"),
                    ("product", "Product page"),
                )
            ]
            labels = {
                "title": "Heading (Russian)",
                "title_en": "Heading (English)",
                "description": "Description (Russian)",
                "description_en": "Description (English)",
                "image": "Website photo",
                "display_order": "Display order",
                "is_active": "Published",
            }
            for field_name, label in labels.items():
                self.fields[field_name].label = label
            self.fields["image"].help_text = (
                "Editorial content for your website, not a product photo."
            )
        self.fields["image"].widget.attrs["accept"] = "image/jpeg,image/png,image/webp"


class SitePageContentForm(forms.ModelForm):
    class Meta:
        model = SitePageContent
        fields = (
            "eyebrow",
            "eyebrow_en",
            "title",
            "title_en",
            "subtitle",
            "subtitle_en",
            "description",
            "description_en",
            "image",
        )
        widgets = {
            "eyebrow": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "eyebrow_en": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "title": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "title_en": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "subtitle": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "subtitle_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 5}
            ),
            "description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 5}
            ),
            "image": forms.ClearableFileInput(
                attrs={"class": "site-content-form-control"}
            ),
        }

    def __init__(self, *args, page, **kwargs):
        super().__init__(*args, **kwargs)
        allowed_fields = SITE_PAGE_EDITABLE_FIELDS[page]
        self.fields = {
            field_name: field
            for field_name, field in self.fields.items()
            if field_name in allowed_fields
        }
        if self.instance._state.adding:
            self.initial.update(SITE_PAGE_CONTENT_DEFAULTS.get(page, {}))
        if (get_language() or "").startswith("en"):
            labels = {
                "eyebrow": "Small heading (Russian)",
                "eyebrow_en": "Small heading (English)",
                "title": "Heading (Russian)",
                "title_en": "Heading (English)",
                "subtitle": "Subtitle (Russian)",
                "subtitle_en": "Subtitle (English)",
                "description": "Description (Russian)",
                "description_en": "Description (English)",
                "image": "Top section photo",
            }
            for field_name, label in labels.items():
                if field_name in self.fields:
                    self.fields[field_name].label = label
            if "image" in self.fields:
                self.fields["image"].help_text = (
                    "Leave empty to keep the current page photo."
                )

        if "image" in self.fields:
            if (get_language() or "").startswith("ru"):
                self.fields["image"].help_text = (
                    "Оставьте поле пустым, чтобы сохранить текущее фото страницы."
                )
            self.fields["image"].widget.attrs["accept"] = "image/jpeg,image/png,image/webp"


SITE_PAGE_SECTION_GROUPS = {
    SitePageSection.Page.HOME: (
        ("popular", "Популярные товары"),
        ("home_about", "О бренде"),
        ("catalog", "Каталог"),
        ("calculator", "Калькулятор"),
        ("partners", "Партнёры"),
    ),
    SitePageSection.Page.ABOUT: (
        ("promises", "Принципы"),
        ("story", "История"),
        ("stats", "Статистика"),
        ("values", "Ценности"),
    ),
    SitePageSection.Page.BUSINESS_CLIENTS: (
        ("steps", "Этапы работы"),
        ("payment", "Оплата"),
        ("delivery", "Доставка"),
        ("calculator", "Калькулятор заказа"),
        ("contacts", "Контактная информация"),
    ),
    SitePageSection.Page.PARTNERSHIP: (
        ("directions", "Направления сотрудничества"),
        ("stats", "Статистика"),
        ("summary", "Итоговый текст"),
    ),
    SitePageSection.Page.CONTACTS: (
        ("details", "Контактные данные"),
        ("requisites", "Реквизиты"),
    ),
    SitePageSection.Page.DELIVERY: (
        ("methods", "Способы доставки"),
        ("notes", "Дополнительная информация"),
        ("pickup", "Самовывоз"),
    ),
    SitePageSection.Page.FAQ: (("questions", "Вопросы и ответы"),),
    SitePageSection.Page.FEEDBACK: (("contacts", "Способы связи"),),
    SitePageSection.Page.PACKAGING: (
        ("options", "Основные варианты"),
        ("gifts", "Упаковка для наборов"),
        ("extras", "Дополнительные варианты"),
    ),
    SitePageSection.Page.CATALOG: (
        ("catalog_copy", "Текст каталога"),
        ("promos", "Рекламные карточки каталога"),
    ),
    SitePageSection.Page.CATEGORIES: (("category_copy", "Текст обзора категорий"),),
}
SITE_PAGE_SECTION_GROUP_LABELS_EN = {
    "Принципы": "Principles",
    "История": "Story",
    "Статистика": "Statistics",
    "Ценности": "Values",
    "Текстовые блоки главной": "Homepage text",
    "Популярные товары": "Popular products",
    "О бренде": "About the brand",
    "Каталог": "Catalog",
    "Калькулятор": "Calculator",
    "Партнёры": "Partners",
    "Этапы работы": "Work process",
    "Оплата": "Payment",
    "Доставка": "Delivery",
    "Калькулятор заказа": "Order calculator",
    "Контактная информация": "Contact information",
    "Направления сотрудничества": "Partnership directions",
    "Итоговый текст": "Summary",
    "Контактные данные": "Contact details",
    "Реквизиты": "Company details",
    "Способы доставки": "Delivery methods",
    "Дополнительная информация": "Additional information",
    "Самовывоз": "Pickup",
    "Вопросы и ответы": "Questions and answers",
    "Способы связи": "Contact methods",
    "Основные варианты": "Main options",
    "Упаковка для наборов": "Gift set packaging",
    "Дополнительные варианты": "Additional options",
    "Текст каталога": "Catalog text",
    "Рекламные карточки каталога": "Catalog promo cards",
    "Текст обзора категорий": "Category overview text",
}

SITE_PAGE_SECTION_VALUE_GROUPS = {
    (SitePageSection.Page.ABOUT, "stats"),
    (SitePageSection.Page.BUSINESS_CLIENTS, "contacts"),
    (SitePageSection.Page.CONTACTS, "details"),
    (SitePageSection.Page.DELIVERY, "methods"),
    (SitePageSection.Page.FEEDBACK, "contacts"),
    (SitePageSection.Page.PARTNERSHIP, "stats"),
}


class AboutStorySectionForm(forms.ModelForm):
    class Meta:
        model = SitePageSection
        fields = (
            "section_eyebrow",
            "section_eyebrow_en",
            "section_title",
            "section_title_en",
            "description",
            "description_en",
            "image",
            "image_alt",
            "image_alt_en",
            "is_active",
        )
        widgets = {
            "section_eyebrow": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "section_eyebrow_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "section_title": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "section_title_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 5}
            ),
            "description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 5}
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "site-content-form-control",
                    "accept": "image/jpeg,image/png,image/webp",
                }
            ),
            "image_alt": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "image_alt_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "site-content-form-checkbox"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if (get_language() or "").startswith("en"):
            self.fields["section_eyebrow"].label = "Small heading (Russian)"
            self.fields["section_eyebrow_en"].label = "Small heading (English)"
            self.fields["section_title"].label = "Heading (Russian)"
            self.fields["section_title_en"].label = "Heading (English)"
            self.fields["description"].label = "Story text (Russian)"
            self.fields["description_en"].label = "Story text (English)"
            self.fields["image"].label = "Image"
            self.fields["image_alt"].label = "Image description (Russian)"
            self.fields["image_alt_en"].label = "Image description (English)"
            self.fields["is_active"].label = "Published"
        else:
            self.fields["section_eyebrow"].label = "Надзаголовок (русский)"
            self.fields["section_eyebrow_en"].label = "Надзаголовок (английский)"
            self.fields["section_title"].label = "Заголовок (русский)"
            self.fields["section_title_en"].label = "Заголовок (английский)"
            self.fields["description"].label = "Текст истории (русский)"
            self.fields["description_en"].label = "Текст истории (английский)"
            self.fields["image"].label = "Изображение"
            self.fields["image_alt"].label = "Описание изображения (русский)"
            self.fields["image_alt_en"].label = "Описание изображения (английский)"
            self.fields["is_active"].label = "Опубликовано"
            self.fields["image"].help_text = "JPG, PNG или WebP."

    def save(self, commit=True):
        section = super().save(commit=False)
        section.page = SitePageSection.Page.ABOUT
        section.group = "story"
        section.display_order = 0
        if commit:
            section.save()
        return section


class AboutPromiseForm(forms.ModelForm):
    display_order = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(
            attrs={"class": "site-content-form-control", "min": 1}
        ),
    )

    class Meta:
        model = SitePageSection
        fields = (
            "title",
            "title_en",
            "description",
            "description_en",
            "display_order",
            "is_active",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "title_en": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "site-content-form-checkbox"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.initial["is_active"] = False
        if not self.is_bound and self.instance.pk:
            self.initial["display_order"] = self.instance.display_order + 1
        if (get_language() or "").startswith("en"):
            labels = {
                "title": "Title (Russian)",
                "title_en": "Title (English)",
                "description": "Description (Russian)",
                "description_en": "Description (English)",
                "display_order": "Display order",
                "is_active": "Published",
            }
        else:
            labels = {
                "title": "Заголовок (русский)",
                "title_en": "Заголовок (английский)",
                "description": "Описание (русский)",
                "description_en": "Описание (английский)",
                "display_order": "Порядок",
                "is_active": "Опубликовано",
            }
        for field_name, label in labels.items():
            self.fields[field_name].label = label

    def save(self, commit=True):
        promise = super().save(commit=False)
        promise.display_order -= 1
        if commit:
            promise.save()
        return promise


class AboutStatForm(forms.ModelForm):
    display_order = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(
            attrs={"class": "site-content-form-control", "min": 1}
        ),
    )

    class Meta:
        model = SitePageSection
        fields = (
            "value",
            "value_en",
            "description",
            "description_en",
            "display_order",
            "is_active",
        )
        widgets = {
            "value": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "value_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "description": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "description_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "site-content-form-checkbox"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.initial["is_active"] = False
        if not self.is_bound and self.instance.pk:
            self.initial["display_order"] = self.instance.display_order + 1
        if (get_language() or "").startswith("en"):
            labels = {
                "value": "Metric (Russian)",
                "value_en": "Metric (English)",
                "description": "Description (Russian)",
                "description_en": "Description (English)",
                "display_order": "Display order",
                "is_active": "Published",
            }
        else:
            labels = {
                "value": "Показатель (русский)",
                "value_en": "Показатель (английский)",
                "description": "Описание (русский)",
                "description_en": "Описание (английский)",
                "display_order": "Порядок",
                "is_active": "Показывать",
            }
        for field_name, label in labels.items():
            self.fields[field_name].label = label

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("is_active") and not (
            cleaned_data.get("value") or cleaned_data.get("value_en")
        ):
            self.add_error(
                "value",
                "Enter a metric in at least one language."
                if (get_language() or "").startswith("en")
                else "Укажите показатель хотя бы на одном языке.",
            )
        return cleaned_data

    def save(self, commit=True):
        statistic = super().save(commit=False)
        statistic.display_order -= 1
        if commit:
            statistic.save()
        return statistic


class AboutValueCardForm(forms.ModelForm):
    display_order = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(
            attrs={"class": "site-content-form-control", "min": 1}
        ),
    )

    class Meta:
        model = SitePageSection
        fields = (
            "title",
            "title_en",
            "description",
            "description_en",
            "image",
            "image_alt",
            "image_alt_en",
            "display_order",
            "is_active",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "title_en": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "site-content-form-control",
                    "accept": "image/jpeg,image/png,image/webp",
                }
            ),
            "image_alt": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "image_alt_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "site-content-form-checkbox"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.initial["is_active"] = False
        if not self.is_bound and self.instance.pk:
            self.initial["display_order"] = self.instance.display_order + 1
        if (get_language() or "").startswith("en"):
            labels = {
                "title": "Title (Russian)",
                "title_en": "Title (English)",
                "description": "Description (Russian)",
                "description_en": "Description (English)",
                "image": "Image",
                "image_alt": "Image description (Russian)",
                "image_alt_en": "Image description (English)",
                "display_order": "Display order",
                "is_active": "Published",
            }
        else:
            labels = {
                "title": "Заголовок (русский)",
                "title_en": "Заголовок (английский)",
                "description": "Описание (русский)",
                "description_en": "Описание (английский)",
                "image": "Изображение",
                "image_alt": "Описание изображения (русский)",
                "image_alt_en": "Описание изображения (английский)",
                "display_order": "Порядок",
                "is_active": "Опубликовано",
            }
            self.fields["image"].help_text = "JPG, PNG или WebP."
        for field_name, label in labels.items():
            self.fields[field_name].label = label

    def save(self, commit=True):
        value_card = super().save(commit=False)
        value_card.display_order -= 1
        if commit:
            value_card.save()
        return value_card


class AboutValuesHeadingForm(forms.Form):
    section_eyebrow = forms.CharField(
        required=False,
        label="Надзаголовок (русский)",
        widget=forms.TextInput(attrs={"class": "site-content-form-control"}),
    )
    section_eyebrow_en = forms.CharField(
        required=False,
        label="Надзаголовок (английский)",
        widget=forms.TextInput(attrs={"class": "site-content-form-control"}),
    )
    section_title = forms.CharField(
        required=False,
        label="Заголовок (русский)",
        widget=forms.TextInput(attrs={"class": "site-content-form-control"}),
    )
    section_title_en = forms.CharField(
        required=False,
        label="Заголовок (английский)",
        widget=forms.TextInput(attrs={"class": "site-content-form-control"}),
    )
    section_description = forms.CharField(
        required=False,
        label="Описание (русский)",
        widget=forms.Textarea(attrs={"class": "site-content-form-control", "rows": 3}),
    )
    section_description_en = forms.CharField(
        required=False,
        label="Описание (английский)",
        widget=forms.Textarea(attrs={"class": "site-content-form-control", "rows": 3}),
    )

    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        initial = kwargs.pop("initial", {})
        if instance:
            initial.update(
                {
                    field_name: getattr(instance, field_name)
                    for field_name in (
                        "section_eyebrow",
                        "section_eyebrow_en",
                        "section_title",
                        "section_title_en",
                        "section_description",
                        "section_description_en",
                    )
                }
            )
        super().__init__(*args, initial=initial, **kwargs)
        if (get_language() or "").startswith("en"):
            labels = {
                "section_eyebrow": "Small heading (Russian)",
                "section_eyebrow_en": "Small heading (English)",
                "section_title": "Heading (Russian)",
                "section_title_en": "Heading (English)",
                "section_description": "Introduction (Russian)",
                "section_description_en": "Introduction (English)",
            }
            for field_name, label in labels.items():
                self.fields[field_name].label = label


class ContactDetailsForm(forms.Form):
    phone_value = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "site-content-form-control"}),
    )
    phone_value_en = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "site-content-form-control"}),
    )
    phone_url = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "site-content-form-control"}),
    )
    phone_description = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "site-content-form-control"}),
    )
    phone_description_en = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "site-content-form-control"}),
    )
    email_value = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "site-content-form-control"}),
    )
    email_value_en = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "site-content-form-control"}),
    )
    email_url = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "site-content-form-control"}),
    )
    email_description = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "site-content-form-control"}),
    )
    email_description_en = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "site-content-form-control"}),
    )
    address_value = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "site-content-form-control", "rows": 2}),
    )
    address_value_en = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "site-content-form-control", "rows": 2}),
    )
    address_url = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "site-content-form-control"}),
    )
    address_description = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "site-content-form-control"}),
    )
    address_description_en = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "site-content-form-control"}),
    )

    CONTACTS = (
        ("phone", "Телефон", "Phone"),
        ("email", "E-mail", "E-mail"),
        ("address", "Адрес", "Address"),
    )

    def __init__(
        self,
        *args,
        contacts=(),
        page=SitePageSection.Page.CONTACTS,
        group="details",
        **kwargs,
    ):
        self.contacts = list(contacts)
        self.page = page
        self.group = group
        if not args and not kwargs.get("data"):
            initial = kwargs.setdefault("initial", {})
            for index, (prefix, _, _) in enumerate(self.CONTACTS):
                if index >= len(self.contacts):
                    continue
                contact = self.contacts[index]
                initial[f"{prefix}_value"] = contact.value
                initial[f"{prefix}_value_en"] = contact.value_en
                initial[f"{prefix}_url"] = contact.url
                initial[f"{prefix}_description"] = contact.description
                initial[f"{prefix}_description_en"] = contact.description_en
        super().__init__(*args, **kwargs)

        english = (get_language() or "").startswith("en")
        for prefix, russian_name, english_name in self.CONTACTS:
            name = english_name if english else russian_name
            self.fields[f"{prefix}_value"].label = f"{name} (русский)" if english else f"{name} (русский)"
            self.fields[f"{prefix}_value_en"].label = f"{name} (English)" if english else f"{name} (английский)"
            self.fields[f"{prefix}_url"].label = (
                f"{name} link" if english else f"Ссылка ({name.lower()})"
            )
            self.fields[f"{prefix}_description"].label = (
                f"{name} note (Russian)"
                if english
                else f"Подпись ({name.lower()}, русский)"
            )
            self.fields[f"{prefix}_description_en"].label = (
                f"{name} note (English)"
                if english
                else f"Подпись ({name.lower()}, английский)"
            )

    def save(self):
        contacts = []
        for index, (prefix, russian_name, english_name) in enumerate(self.CONTACTS):
            contact = (
                self.contacts[index]
                if index < len(self.contacts)
                else SitePageSection(
                    page=self.page,
                    group=self.group,
                    display_order=index,
                    is_active=True,
                )
            )
            contact.page = self.page
            contact.group = self.group
            contact.title = russian_name
            contact.title_en = english_name
            contact.value = self.cleaned_data[f"{prefix}_value"]
            contact.value_en = self.cleaned_data[f"{prefix}_value_en"]
            contact.url = self.cleaned_data[f"{prefix}_url"]
            contact.description = self.cleaned_data[f"{prefix}_description"]
            contact.description_en = self.cleaned_data[
                f"{prefix}_description_en"
            ]
            contact.save()
            contacts.append(contact)
        return contacts


class ContactRequisitesForm(forms.ModelForm):
    class Meta:
        model = SitePageSection
        fields = (
            "title",
            "title_en",
            "description",
            "description_en",
            "value",
            "value_en",
            "url",
            "is_active",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "title_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "value": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "value_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "url": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "is_active": forms.CheckboxInput(
                attrs={"class": "site-content-form-checkbox"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if (get_language() or "").startswith("en"):
            labels = {
                "title": "Section heading (Russian)",
                "title_en": "Section heading (English)",
                "description": "Description (Russian)",
                "description_en": "Description (English)",
                "value": "Button text (Russian)",
                "value_en": "Button text (English)",
                "url": "Button link",
                "is_active": "Published",
            }
            for field_name, label in labels.items():
                self.fields[field_name].label = label


class DeliveryPageFormMixin:
    english_labels = {
        "section_title": "Section heading (Russian)",
        "section_title_en": "Section heading (English)",
        "section_description": "Section introduction (Russian)",
        "section_description_en": "Section introduction (English)",
        "title": "Title (Russian)",
        "title_en": "Title (English)",
        "description": "Description (Russian)",
        "description_en": "Description (English)",
        "value": "Note (Russian)",
        "value_en": "Note (English)",
        "url": "Map or contact link",
        "image": "Image",
        "image_alt": "Image description (Russian)",
        "image_alt_en": "Image description (English)",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "is_active" in self.fields and not self.instance.pk:
            self.initial["is_active"] = False
        if (get_language() or "").startswith("en"):
            for field_name, label in self.english_labels.items():
                if field_name in self.fields:
                    self.fields[field_name].label = label


class DeliveryMethodsCardForm(DeliveryPageFormMixin, forms.ModelForm):
    class Meta:
        model = SitePageSection
        fields = (
            "title",
            "title_en",
            "description",
            "description_en",
            "value",
            "value_en",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "title_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "value": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 2}
            ),
            "value_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 2}
            ),
        }


class DeliverySectionHeadingForm(DeliveryPageFormMixin, forms.ModelForm):
    class Meta:
        model = SitePageSection
        fields = ("section_title", "section_title_en", "section_description", "section_description_en")
        widgets = {
            "section_title": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "section_title_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "section_description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 2}
            ),
            "section_description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 2}
            ),
        }


class DeliveryPickupHeadingForm(DeliveryPageFormMixin, forms.ModelForm):
    class Meta:
        model = SitePageSection
        fields = (
            "section_title",
            "section_title_en",
            "section_description",
            "section_description_en",
            "value",
            "value_en",
            "url",
        )
        widgets = {
            "section_title": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "section_title_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "section_description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 2}
            ),
            "section_description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 2}
            ),
            "value": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "value_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "url": forms.TextInput(attrs={"class": "site-content-form-control"}),
        }


class DeliveryPickupDetailForm(DeliveryPageFormMixin, forms.ModelForm):
    class Meta:
        model = SitePageSection
        fields = ("title", "title_en", "description", "description_en")
        widgets = {
            "title": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "title_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
        }


class DeliveryHelpCardForm(DeliveryPageFormMixin, forms.ModelForm):
    class Meta:
        model = SitePageSection
        fields = (
            "title",
            "title_en",
            "description",
            "description_en",
            "value",
            "value_en",
            "url",
            "image",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "title_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "value": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "value_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "url": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "site-content-form-control",
                    "accept": "image/jpeg,image/png,image/webp",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        english = (get_language() or "").startswith("en")
        self.fields["image"].label = "Icon image" if english else "Иконка"
        self.fields["image"].help_text = (
            "Leave empty to keep the current icon."
            if english
            else "Оставьте поле пустым, чтобы сохранить текущий значок."
        )


class FAQQuestionForm(forms.ModelForm):
    display_order = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(
            attrs={"class": "site-content-form-control", "min": 1}
        ),
    )

    class Meta:
        model = SitePageSection
        fields = (
            "title",
            "title_en",
            "description",
            "description_en",
            "display_order",
            "is_active",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "title_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 4}
            ),
            "description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 4}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "site-content-form-checkbox"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.initial["is_active"] = False
        if not self.is_bound and self.instance.pk:
            self.initial["display_order"] = self.instance.display_order + 1
        if (get_language() or "").startswith("en"):
            labels = {
                "title": "Question (Russian)",
                "title_en": "Question (English)",
                "description": "Answer (Russian)",
                "description_en": "Answer (English)",
                "display_order": "Display order",
                "is_active": "Published",
            }
        else:
            labels = {
                "title": "Вопрос (русский)",
                "title_en": "Вопрос (английский)",
                "description": "Ответ (русский)",
                "description_en": "Ответ (английский)",
                "display_order": "Порядок",
                "is_active": "Опубликован",
            }
        for field_name, label in labels.items():
            self.fields[field_name].label = label

    def save(self, commit=True):
        question = super().save(commit=False)
        question.display_order -= 1
        if commit:
            question.save()
        return question


class BusinessClientsSectionFormMixin:
    english_labels = {
        "section_title": "Section heading (Russian)",
        "section_title_en": "Section heading (English)",
        "section_description": "Section introduction (Russian)",
        "section_description_en": "Section introduction (English)",
        "title": "Title (Russian)",
        "title_en": "Title (English)",
        "description": "Text (Russian)",
        "description_en": "Text (English)",
        "value": "Button text (Russian)",
        "value_en": "Button text (English)",
        "url": "Button link",
        "image": "Image",
        "image_alt": "Image description (Russian)",
        "image_alt_en": "Image description (English)",
        "is_active": "Published",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if (get_language() or "").startswith("en"):
            for field_name, label in self.english_labels.items():
                if field_name in self.fields:
                    self.fields[field_name].label = label


class BusinessClientsSectionHeadingForm(
    BusinessClientsSectionFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = SitePageSection
        fields = (
            "section_title",
            "section_title_en",
            "section_description",
            "section_description_en",
        )
        widgets = {
            "section_title": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "section_title_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "section_description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 2}
            ),
            "section_description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 2}
            ),
        }


class BusinessClientsSectionTitleForm(
    BusinessClientsSectionFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = SitePageSection
        fields = ("section_title", "section_title_en")
        widgets = {
            "section_title": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "section_title_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
        }


class BusinessClientsCardForm(BusinessClientsSectionFormMixin, forms.ModelForm):
    class Meta:
        model = SitePageSection
        fields = (
            "title",
            "title_en",
            "description",
            "description_en",
            "is_active",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "title_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "site-content-form-checkbox"}
            ),
        }


class BusinessClientsPaymentHeadingForm(
    BusinessClientsSectionFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = SitePageSection
        fields = (
            "section_title",
            "section_title_en",
        )
        widgets = {
            "section_title": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "section_title_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
        }


class BusinessClientsCalculatorForm(
    BusinessClientsSectionFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = SitePageSection
        fields = (
            "title",
            "title_en",
            "description",
            "description_en",
            "image",
            "image_alt",
            "image_alt_en",
            "is_active",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "title_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "site-content-form-control",
                    "accept": "image/jpeg,image/png,image/webp",
                }
            ),
            "image_alt": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "image_alt_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "site-content-form-checkbox"}
            ),
        }


class PartnershipDirectionForm(BusinessClientsSectionFormMixin, forms.ModelForm):
    class Meta:
        model = SitePageSection
        fields = (
            "title",
            "title_en",
            "description",
            "description_en",
            "image",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "title_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "site-content-form-control",
                    "accept": "image/jpeg,image/png,image/webp",
                }
            ),
        }


class PartnershipSuccessForm(BusinessClientsSectionFormMixin, forms.ModelForm):
    class Meta:
        model = SitePageSection
        fields = ("title", "title_en", "description", "description_en")
        widgets = {
            "title": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "title_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
        }


class HomeAboutSectionForm(forms.ModelForm):
    description_2 = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "site-content-form-control", "rows": 3}),
    )
    description_2_en = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "site-content-form-control", "rows": 3}),
    )

    class Meta:
        model = SitePageSection
        fields = (
            "section_eyebrow",
            "section_eyebrow_en",
            "section_title",
            "section_title_en",
            "description",
            "description_en",
            "description_2",
            "description_2_en",
            "image",
            "image_alt",
            "image_alt_en",
            "is_active",
        )
        widgets = {
            "section_eyebrow": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "section_eyebrow_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "section_title": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "section_title_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "site-content-form-control",
                    "accept": "image/jpeg,image/png,image/webp",
                }
            ),
            "image_alt": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "image_alt_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "site-content-form-checkbox"}
            ),
        }

    def __init__(self, *args, secondary_instance=None, **kwargs):
        self.secondary_instance = secondary_instance
        super().__init__(*args, **kwargs)
        if not self.is_bound and secondary_instance:
            self.initial["description_2"] = secondary_instance.description
            self.initial["description_2_en"] = secondary_instance.description_en

        if (get_language() or "").startswith("en"):
            self.fields["section_eyebrow"].label = "Small heading (Russian)"
            self.fields["section_eyebrow_en"].label = "Small heading (English)"
            self.fields["section_title"].label = "Heading (Russian)"
            self.fields["section_title_en"].label = "Heading (English)"
            self.fields["description"].label = "First paragraph (Russian)"
            self.fields["description_en"].label = "First paragraph (English)"
            self.fields["description_2"].label = "Second paragraph (Russian)"
            self.fields["description_2_en"].label = "Second paragraph (English)"
            self.fields["image"].label = "Image"
            self.fields["image_alt"].label = "Image description (Russian)"
            self.fields["image_alt_en"].label = "Image description (English)"
            self.fields["is_active"].label = "Published"
        else:
            self.fields["section_eyebrow"].label = "Надзаголовок (русский)"
            self.fields["section_eyebrow_en"].label = "Надзаголовок (английский)"
            self.fields["section_title"].label = "Заголовок (русский)"
            self.fields["section_title_en"].label = "Заголовок (английский)"
            self.fields["description"].label = "Первый абзац (русский)"
            self.fields["description_en"].label = "Первый абзац (английский)"
            self.fields["description_2"].label = "Второй абзац (русский)"
            self.fields["description_2_en"].label = "Второй абзац (английский)"
            self.fields["image"].label = "Изображение"
            self.fields["image_alt"].label = "Описание изображения (русский)"
            self.fields["image_alt_en"].label = "Описание изображения (английский)"
            self.fields["is_active"].label = "Опубликовано"
            self.fields["image"].help_text = "JPG, PNG или WebP."

    def save(self, commit=True):
        section = super().save(commit=False)
        section.page = SitePageSection.Page.HOME
        section.group = "home_about"
        section.display_order = 0
        if commit:
            section.save()
            description = self.cleaned_data["description_2"]
            description_en = self.cleaned_data["description_2_en"]
            if self.secondary_instance:
                secondary = self.secondary_instance
                secondary.description = description
                secondary.description_en = description_en
                secondary.is_active = section.is_active and bool(
                    description or description_en
                )
                secondary.save(
                    update_fields=("description", "description_en", "is_active")
                )
            elif description or description_en:
                SitePageSection.objects.create(
                    page=SitePageSection.Page.HOME,
                    group="home_about",
                    description=description,
                    description_en=description_en,
                    display_order=1,
                    is_active=section.is_active,
                )
        return section


class SitePageSectionForm(forms.ModelForm):
    class Meta:
        model = SitePageSection
        fields = (
            "group",
            "section_eyebrow",
            "section_eyebrow_en",
            "section_title",
            "section_title_en",
            "section_description",
            "section_description_en",
            "title",
            "title_en",
            "description",
            "description_en",
            "value",
            "value_en",
            "image",
            "image_alt",
            "image_alt_en",
            "display_order",
            "is_active",
        )
        widgets = {
            "group": forms.Select(attrs={"class": "site-content-form-control"}),
            "section_eyebrow": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "section_eyebrow_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "section_title": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "section_title_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "section_description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 2}
            ),
            "section_description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 2}
            ),
            "title": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "title_en": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "value": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "value_en": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "site-content-form-control",
                    "accept": "image/jpeg,image/png,image/webp",
                }
            ),
            "image_alt": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "image_alt_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "display_order": forms.NumberInput(
                attrs={"class": "site-content-form-control", "min": 0}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "site-content-form-checkbox"}
            ),
        }

    def __init__(self, *args, page, **kwargs):
        self.page = page
        super().__init__(*args, **kwargs)
        group_choices = SITE_PAGE_SECTION_GROUPS.get(page, ())
        if (get_language() or "").startswith("en"):
            group_choices = [
                (value, SITE_PAGE_SECTION_GROUP_LABELS_EN.get(label, label))
                for value, label in group_choices
            ]
        self.fields["group"].choices = group_choices
        group = self.data.get(
            self.add_prefix("group"),
            self.instance.group or (group_choices[0][0] if group_choices else ""),
        )
        self.value_groups = tuple(
            value
            for section_page, value in SITE_PAGE_SECTION_VALUE_GROUPS
            if section_page == page
        )
        self.show_value_fields = group in self.value_groups
        if (get_language() or "").startswith("en"):
            self.fields["group"].label = "Content group"
            self.fields["section_eyebrow"].label = "Section small heading (Russian)"
            self.fields["section_eyebrow_en"].label = "Section small heading (English)"
            self.fields["section_title"].label = "Section heading (Russian)"
            self.fields["section_title_en"].label = "Section heading (English)"
            self.fields["section_description"].label = "Section introduction (Russian)"
            self.fields["section_description_en"].label = "Section introduction (English)"
            self.fields["title"].label = "Heading (Russian)"
            self.fields["title_en"].label = "Heading (English)"
            self.fields["description"].label = "Text (Russian)"
            self.fields["description_en"].label = "Text (English)"
            value_labels = {
                "value": "Displayed value (Russian)",
                "value_en": "Displayed value (English)",
            }
            for field_name, label in value_labels.items():
                if field_name in self.fields:
                    self.fields[field_name].label = label
            self.fields["image"].label = "Image"
            self.fields["image_alt"].label = "Image description (Russian)"
            self.fields["image_alt_en"].label = "Image description (English)"
            self.fields["display_order"].label = "Display order"
            self.fields["is_active"].label = "Published"
        else:
            self.fields["image"].help_text = "JPG, PNG или WebP."

    def clean(self):
        cleaned_data = super().clean()
        group = cleaned_data.get("group")
        if (self.page, group) not in SITE_PAGE_SECTION_VALUE_GROUPS:
            cleaned_data["value"] = self.instance.value
            cleaned_data["value_en"] = self.instance.value_en
        return cleaned_data

    def save(self, commit=True):
        section = super().save(commit=False)
        section.page = self.page
        if commit:
            section.save()
        return section


class HomeHeroSlideForm(forms.ModelForm):
    class Meta:
        model = HomeHeroSlide
        fields = (
            "image",
            "display_order",
            "is_active",
        )
        widgets = {
            "image": forms.ClearableFileInput(
                attrs={"class": "site-content-form-control"}
            ),
            "display_order": forms.HiddenInput(),
            "is_active": forms.CheckboxInput(
                attrs={"class": "site-content-form-checkbox"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if (get_language() or "").startswith("en"):
            labels = {
                "image": "Banner photo",
                "is_active": "Show this slide",
            }
            for field_name, label in labels.items():
                self.fields[field_name].label = label

            self.fields["image"].help_text = (
                "Leave empty to keep the current banner photo."
            )
        self.fields["image"].widget.attrs["accept"] = "image/jpeg,image/png,image/webp"

    def has_changed(self):
        if (
            self.instance._state.adding
            and self.initial.get("is_active")
            and self.data.get(self.add_prefix("is_active"))
        ):
            return True
        return super().has_changed()


class HomeHeroSlideBaseFormSet(BaseModelFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        if not any(form.cleaned_data.get("is_active") for form in self.forms):
            message = (
                "At least one banner must be visible."
                if (get_language() or "").startswith("en")
                else "Необходимо оставить видимым хотя бы один баннер."
            )
            raise ValidationError(message)


class AdminOrderStatusForm(forms.Form):
    status = forms.ChoiceField(choices=())

    def __init__(self, *args, language_code="ru", **kwargs):
        super().__init__(*args, **kwargs)
        english = {
            "new": "New",
            "contacted": "Confirmed",
            "production": "In production",
            "shipping": "On the way",
            "completed": "Delivered",
            "cancelled": "Cancelled",
        }
        russian = dict(Preorder.Status.choices)
        labels = english if language_code == "en" else russian
        self.fields["status"].choices = tuple(
            (value, labels[value])
            for value, _ in Preorder.Status.choices
        )
        self.fields["status"].widget.attrs["class"] = "site-content-form-control"


class PackagingCardForm(BusinessClientsSectionFormMixin, forms.ModelForm):
    class Meta:
        model = SitePageSection
        fields = (
            "title",
            "title_en",
            "description",
            "description_en",
            "image",
            "image_alt",
            "image_alt_en",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "title_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "site-content-form-control",
                    "accept": "image/jpeg,image/png,image/webp",
                }
            ),
            "image_alt": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "image_alt_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
        }


class CatalogPromoCardForm(BusinessClientsSectionFormMixin, forms.ModelForm):
    CUSTOM_URL_OPTION = "__custom_url__"

    url = forms.ChoiceField(
        choices=(),
        required=False,
        widget=forms.Select(
            attrs={
                "class": "site-content-form-control",
                "data-promo-destination": "true",
                "data-custom-value": CUSTOM_URL_OPTION,
            }
        ),
    )
    custom_url = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "site-content-form-control",
                "autocomplete": "url",
            }
        ),
    )
    display_order = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(
            attrs={"class": "site-content-form-control", "min": 1}
        ),
    )

    class Meta:
        model = SitePageSection
        fields = (
            "title",
            "title_en",
            "description",
            "description_en",
            "url",
            "image",
            "display_order",
            "is_active",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "title_en": forms.TextInput(
                attrs={"class": "site-content-form-control"}
            ),
            "description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 3}
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "site-content-form-control",
                    "accept": "image/jpeg,image/png,image/webp",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "site-content-form-checkbox"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        english = (get_language() or "").startswith("en")
        page_choices = (
            ("home", "Главная", "Home"),
            ("about", "О нас", "About"),
            ("business_clients", "Корпоративным клиентам", "Business clients"),
            ("corporate", "Сотрудничество", "Partnership"),
            ("contacts", "Контакты", "Contacts"),
            ("delivery", "Доставка", "Delivery"),
            ("faq", "Вопросы и ответы", "FAQ"),
            ("feedback", "Обратная связь", "Feedback"),
            ("packaging", "Упаковка", "Packaging"),
            ("catalog:category_list", "Каталог", "Catalog"),
            ("catalog:categories", "Категории", "Categories"),
        )
        destinations = [
            (reverse(route_name), english_label if english else russian_label)
            for route_name, russian_label, english_label in page_choices
        ]
        self.fields["url"].choices = [
            ("", "Choose a page" if english else "Выберите страницу"),
            *destinations,
            (
                self.CUSTOM_URL_OPTION,
                "Custom or external URL" if english else "Своя или внешняя ссылка",
            ),
        ]
        self.fields["url"].label = (
            "Button destination" if english else "Куда ведёт кнопка"
        )
        self.fields["custom_url"].label = (
            "Custom or external URL" if english else "Своя или внешняя ссылка"
        )
        self.order_fields(
            (
                "title",
                "title_en",
                "description",
                "description_en",
                "url",
                "custom_url",
                "image",
                "display_order",
                "is_active",
            )
        )
        if self.instance.pk and not self.is_bound:
            current_url = self.instance.url
            page_urls = {value for value, _label in destinations}
            if current_url in page_urls:
                self.initial["url"] = current_url
            elif current_url:
                self.initial["url"] = self.CUSTOM_URL_OPTION
                self.initial["custom_url"] = current_url
            else:
                self.initial["url"] = ""
        if self.instance.pk:
            self.initial["display_order"] = self.instance.display_order + 1
        if english:
            self.fields["display_order"].label = "Display order"
        else:
            self.fields["display_order"].label = "Порядок отображения"

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("url") == self.CUSTOM_URL_OPTION:
            custom_url = cleaned_data.get("custom_url", "").strip()
            if custom_url:
                cleaned_data["url"] = custom_url
            else:
                self.add_error(
                    "custom_url",
                    (
                        "Enter a URL."
                        if (get_language() or "").startswith("en")
                        else "Введите ссылку."
                    ),
                )
        return cleaned_data

    def save(self, commit=True):
        promo = super().save(commit=False)
        promo.display_order -= 1
        if commit:
            promo.save()
        return promo


class AdminFeedbackStatusForm(forms.Form):
    status = forms.ChoiceField(choices=())

    def __init__(self, *args, language_code="ru", **kwargs):
        super().__init__(*args, **kwargs)
        english = {
            "new": "New",
            "in_progress": "In progress",
            "resolved": "Resolved",
        }
        labels = english if language_code == "en" else dict(FeedbackSubmission.Status.choices)
        self.fields["status"].choices = tuple(
            (value, labels[value]) for value, _ in FeedbackSubmission.Status.choices
        )
        self.fields["status"].widget.attrs["class"] = "site-content-form-control"


class CalculatorPricingForm(forms.Form):
    MAX_PRODUCTS = 30
    MAX_OPTIONS = 30
    MAX_SIZES = 30
    MAX_MODIFIER_GROUPS = 20
    MAX_DISCOUNT_RULES = 30

    def __init__(
        self,
        *args,
        pricing=None,
        product_images=None,
        option_images=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.pricing_source = pricing
        pricing = normalize_calculator_pricing(pricing)
        product_images = product_images or {}
        option_images = option_images or {}
        self.option_catalog = pricing["option_catalog"]
        options = localized_calculator_options(pricing)
        english = (get_language() or "").startswith("en")
        currency = "RUB" if english else "₽"
        self.field_groups = []
        self.product_count = self._get_product_count(pricing)
        self.fields["product_count"] = forms.IntegerField(
            required=False,
            min_value=1,
            max_value=self.MAX_PRODUCTS,
            initial=self.product_count,
            widget=forms.HiddenInput(),
        )
        self.product_groups = []
        for index in range(self.product_count):
            product = (
                pricing["products"][index]
                if index < len(pricing["products"])
                else {"label": "", "label_en": "", "base_unit_price": 0}
            )
            name = f"product_{index}_name"
            name_en = f"product_{index}_name_en"
            price_name = "base_unit_price" if index == 0 else f"product_{index}_base_price"
            original_value_name = f"product_{index}_original_value"
            image_name = f"product_{index}_image"
            original_value = product.get("value", "")
            product_image = product_images.get(original_value)
            self.fields[name] = forms.CharField(
                max_length=80,
                label="Product name" if english else "Название товара",
                initial=product["label"],
                widget=forms.TextInput(
                    attrs={"class": "site-content-form-control", "data-product-name": ""}
                ),
            )
            self.fields[name_en] = forms.CharField(
                max_length=80,
                required=False,
                label="Product name (English)" if english else "Название товара (английский)",
                initial=product.get("label_en", ""),
                widget=forms.TextInput(
                    attrs={"class": "site-content-form-control", "data-product-name-en": ""}
                ),
            )
            self._add_price_field(
                price_name,
                f"Legacy fallback base price ({currency})"
                if english
                else f"Базовая цена для старых настроек ({currency})",
                product["base_unit_price"],
                minimum=0,
                decimal_places=2,
            )
            self.fields[price_name].widget.attrs["data-product-price"] = ""
            self.fields[original_value_name] = forms.CharField(
                required=False,
                initial=original_value,
                widget=forms.HiddenInput(attrs={"data-product-original-value": ""}),
            )
            self.fields[image_name] = forms.ImageField(
                required=False,
                label="Product photo" if english else "Фото товара",
                initial=product_image.image if product_image else None,
                validators=[
                    FileExtensionValidator(["jpg", "jpeg", "png", "webp"])
                ],
                widget=forms.ClearableFileInput(
                    attrs={
                        "class": "site-content-form-control",
                        "accept": "image/jpeg,image/png,image/webp",
                        "data-product-image": "",
                    }
                ),
            )
            size_json_name = f"product_{index}_sizes_json"
            modifier_json_name = f"product_{index}_modifier_groups_json"
            lead_time_json_name = f"product_{index}_lead_time_rules_json"
            self.fields[size_json_name] = forms.JSONField(
                required=False,
                initial=json.dumps(
                    [
                        {
                            "value": size["value"],
                            "label": size["label"],
                            "base_price": str(size["base_price"]),
                        }
                        for size in product.get("sizes", [])
                    ],
                    ensure_ascii=False,
                ),
                widget=forms.HiddenInput(attrs={"data-product-sizes": ""}),
            )
            self.fields[modifier_json_name] = forms.JSONField(
                required=False,
                initial=json.dumps(
                    [
                        {
                            "value": group["value"],
                            "label": group["label"],
                            "label_en": group["label_en"],
                            "options": [
                                {
                                    "value": option["value"],
                                    "label": option["label"],
                                    "label_en": option["label_en"],
                                    "amount": str(option["amount"]),
                                    "amount_type": option["amount_type"],
                                }
                                for option in group["options"]
                            ],
                        }
                        for group in product.get("modifier_groups", [])
                    ],
                    ensure_ascii=False,
                ),
                widget=forms.HiddenInput(attrs={"data-product-modifiers": ""}),
            )
            self.fields[lead_time_json_name] = forms.JSONField(
                required=False,
                initial=json.dumps(product.get("lead_time_rules", []), ensure_ascii=False),
                widget=forms.HiddenInput(attrs={"data-product-lead-time-rules": ""}),
            )
            self.product_groups.append(
                {
                    "index": index,
                    "fields": (name, name_en, price_name, image_name),
                    "original_value": self[original_value_name],
                    "image_url": product_image.image.url if product_image else "",
                    "sizes_field": self[size_json_name],
                    "modifiers_field": self[modifier_json_name],
                    "lead_time_rules_field": self[lead_time_json_name],
                    "sizes_json": json.dumps(
                        json.loads(self.fields[size_json_name].initial),
                        ensure_ascii=False,
                    ),
                    "modifiers_json": json.dumps(
                        json.loads(self.fields[modifier_json_name].initial),
                        ensure_ascii=False,
                    ),
                    "lead_time_rules_json": json.dumps(
                        json.loads(self.fields[lead_time_json_name].initial),
                        ensure_ascii=False,
                    ),
                }
            )
        self.fields["payment_methods_json"] = forms.JSONField(
            required=False,
            initial=json.dumps(
                [
                    {
                        "value": method["value"],
                        "label": method["label"],
                        "label_en": method["label_en"],
                    }
                    for method in pricing["payment_methods"]
                ],
                ensure_ascii=False,
            ),
            widget=forms.HiddenInput(),
        )
        self.fields["discount_rules_json"] = forms.JSONField(
            required=False,
            initial=json.dumps(
                [
                    {
                        "value": rule["value"],
                        "label": rule["label"],
                        "label_en": rule["label_en"],
                        "trigger": rule["trigger"],
                        "trigger_value": rule["trigger_value"],
                        "amount_type": rule["amount_type"],
                        "amount": str(rule["amount"]),
                    }
                    for rule in pricing["discount_rules"]
                ],
                ensure_ascii=False,
            ),
            widget=forms.HiddenInput(),
        )
        self.configuration_editors = [
            {
                "key": "payment_methods",
                "field": self["payment_methods_json"],
                "items_json": self.fields["payment_methods_json"].initial,
            },
            {
                "key": "discount_rules",
                "field": self["discount_rules_json"],
                "items_json": self.fields["discount_rules_json"].initial,
            },
        ]
        for group_key, pricing_key in (
            ("sizes", "size_multipliers"),
            ("deliveries", "delivery_costs"),
        ):
            field_names = []
            for option in options[group_key]:
                value = option["value"]
                if group_key == "sizes":
                    label = (
                        f'{option["label"]} cm — multiplier'
                        if english
                        else f'{option["label"]} см — множитель'
                    )
                    minimum = 0
                    decimal_places = 3
                    name = f"size_multiplier_{value}"
                else:
                    name = f"delivery_cost_{value}"
                    label = f'{option["label"]} — cost ({currency})'
                    minimum = 0
                    decimal_places = 2
                self._add_price_field(
                    name,
                    label,
                    pricing[pricing_key].get(value, Decimal("1")),
                    minimum=minimum,
                    decimal_places=decimal_places,
                )
                field_names.append(name)
            group_labels = {
                "sizes": (
                    "Legacy fallback size multipliers",
                    "Множители размера для старых настроек",
                ),
                "deliveries": ("Delivery costs", "Стоимость доставки"),
            }
            self.field_groups.append(
                (group_labels[group_key][0 if english else 1], tuple(field_names))
            )

        image_group_titles = {
            "flavors": ("Flavor options", "Названия и фото вкусов"),
            "shapes": ("Shape options", "Названия и фото форм"),
            "coatings": ("Coating options", "Названия и фото покрытий"),
            "packaging": ("Packaging options", "Названия и фото упаковки"),
        }
        self.option_image_groups = []
        self.option_group_counts = {}
        for group_key in ("flavors", "shapes", "coatings", "packaging"):
            catalog = pricing["option_catalog"][group_key]
            active_options = [option for option in catalog if option["active"]]
            count = self._get_option_count(group_key, len(active_options))
            self.option_group_counts[group_key] = count
            count_name = f"option_{group_key}_count"
            self.fields[count_name] = forms.IntegerField(
                required=False,
                min_value=0,
                max_value=self.MAX_OPTIONS,
                initial=count,
                widget=forms.HiddenInput(
                    attrs={"data-option-count": group_key}
                ),
            )
            group_items = []
            for index in range(count):
                option = (
                    active_options[index]
                    if index < len(active_options)
                    else {
                        "value": "",
                        "label": "",
                        "label_en": "",
                        "extra": 0,
                    }
                )
                value = option["value"]
                value_name = f"option_{group_key}_{index}_value"
                label_name = f"option_{group_key}_{index}_label"
                label_en_name = f"option_{group_key}_{index}_label_en"
                extra_name = f"option_{group_key}_{index}_extra"
                image_name = f"option_image_{group_key}_{index}"
                option_image = (
                    option_images.get((group_key, value)) if value else None
                )
                label = (
                    option_image.label
                    if option_image and option_image.label
                    else option["label"]
                )
                label_en = (
                    option_image.label_en
                    if option_image and option_image.label_en
                    else option["label_en"]
                )
                option_title = label_en if english else label
                option_title = option_title or (
                    "New option" if english else "Новая опция"
                )
                self.fields[value_name] = forms.SlugField(
                    required=False,
                    max_length=32,
                    allow_unicode=True,
                    initial=value,
                    widget=forms.HiddenInput(
                        attrs={"data-option-input": "value"}
                    ),
                )
                self.fields[label_name] = forms.CharField(
                    required=False,
                    max_length=100,
                    label="Name (Russian)" if english else "Название (русский)",
                    initial=label,
                    widget=forms.TextInput(
                        attrs={
                            "class": "site-content-form-control",
                            "data-option-input": "label",
                        }
                    ),
                )
                self.fields[label_en_name] = forms.CharField(
                    required=False,
                    max_length=100,
                    label="Name (English)" if english else "Название (английский)",
                    initial=label_en,
                    widget=forms.TextInput(
                        attrs={
                            "class": "site-content-form-control",
                            "data-option-input": "label-en",
                        }
                    ),
                )
                field_names = [label_name, label_en_name]
                if group_key != "shapes":
                    self._add_price_field(
                        extra_name,
                        "Additional price (RUB)" if english else "Доплата (₽)",
                        option["extra"],
                        minimum=None,
                        decimal_places=2,
                    )
                    self.fields[extra_name].required = False
                    self.fields[extra_name].widget.attrs["data-option-input"] = "extra"
                    field_names.append(extra_name)
                self.fields[image_name] = forms.ImageField(
                    required=False,
                    label="Photo" if english else "Фото",
                    initial=(
                        option_image.image
                        if option_image and option_image.image
                        else None
                    ),
                    validators=[
                        FileExtensionValidator(["jpg", "jpeg", "png", "webp"])
                    ],
                    widget=forms.ClearableFileInput(
                        attrs={
                            "class": "site-content-form-control",
                            "accept": "image/jpeg,image/png,image/webp",
                            "data-option-input": "image",
                        }
                    ),
                )
                field_names.append(image_name)
                group_items.append(
                    {
                        "title": option_title,
                        "value_field_name": value_name,
                        "field_names": tuple(field_names),
                        "image_url": (
                            option_image.image.url
                            if option_image and option_image.image
                            else ""
                        ),
                    }
                )
            self.option_image_groups.append(
                {
                    "key": group_key,
                    "title": image_group_titles[group_key][0 if english else 1],
                    "items": group_items,
                }
            )

        tier_names = []
        for index in range(3):
            slot = index + 1
            threshold_name = f"discount_quantity_{slot}"
            percent_name = f"discount_percent_{slot}"
            tier = (
                pricing["discount_tiers"][index]
                if index < len(pricing["discount_tiers"])
                else None
            )
            self.fields[threshold_name] = forms.IntegerField(
                label=(
                    f"Tier {slot}: minimum quantity"
                    if english
                    else f"Скидка {slot}: от количества"
                ),
                required=False,
                min_value=1,
                initial=tier[0] if tier else None,
                widget=forms.NumberInput(
                    attrs={"class": "site-content-form-control", "min": 1}
                ),
            )
            self.fields[percent_name] = forms.IntegerField(
                label=(
                    f"Tier {slot}: discount (%)"
                    if english
                    else f"Скидка {slot}: размер (%)"
                ),
                required=False,
                min_value=0,
                max_value=100,
                initial=tier[1] if tier else None,
                widget=forms.NumberInput(
                    attrs={"class": "site-content-form-control", "min": 0, "max": 100}
                ),
            )
            tier_names.extend((threshold_name, percent_name))
        self.field_groups.append(
            ("Bulk discounts" if english else "Скидки за объём", tuple(tier_names))
        )

        self.fields["lead_time_days"] = forms.IntegerField(
            label=(
                "Estimated lead time (days)"
                if english
                else "Срок изготовления (дней)"
            ),
            min_value=1,
            max_value=365,
            initial=pricing["lead_time_days"],
            widget=forms.NumberInput(
                attrs={"class": "site-content-form-control", "min": 1, "max": 365}
            ),
        )
        self.field_groups.append(
            (
                "Lead time" if english else "Срок изготовления",
                ("lead_time_days",),
            )
        )

    def _get_product_count(self, pricing):
        if self.is_bound and "product_count" in self.data:
            try:
                count = int(self.data["product_count"])
            except (TypeError, ValueError):
                return 1
            return min(max(count, 1), self.MAX_PRODUCTS)
        return min(max(len(pricing["products"]), 1), self.MAX_PRODUCTS)

    def _get_option_count(self, group, initial):
        field_name = f"option_{group}_count"
        if self.is_bound and field_name in self.data:
            try:
                count = int(self.data[field_name])
            except (TypeError, ValueError):
                return initial
            return min(max(count, 0), self.MAX_OPTIONS)
        return min(max(initial, 0), self.MAX_OPTIONS)

    def _add_price_field(self, name, label, initial, *, minimum, decimal_places):
        self.fields[name] = forms.DecimalField(
            label=label,
            max_digits=10,
            decimal_places=decimal_places,
            min_value=minimum,
            initial=initial,
            widget=forms.NumberInput(
                attrs={
                    "class": "site-content-form-control",
                    "step": "0.01" if decimal_places == 2 else "0.001",
                }
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        product_count = cleaned_data.get("product_count") or self.product_count
        products = []
        normalized_products = normalize_calculator_pricing(self.pricing_source)["products"]
        seen_values = set()
        for index in range(min(product_count, self.MAX_PRODUCTS)):
            name_field = f"product_{index}_name"
            label = (cleaned_data.get(name_field) or "").strip()
            label_en = (cleaned_data.get(f"product_{index}_name_en") or "").strip()
            value = slugify(label, allow_unicode=True)
            if not value:
                value = f"product-{index + 1}"
            if value in seen_values:
                self.add_error(
                    name_field,
                    "Product names must be unique."
                    if (get_language() or "").startswith("en")
                    else "Названия товаров должны быть уникальными.",
                )
                continue
            seen_values.add(value)
            price_field = (
                "base_unit_price"
                if index == 0
                else f"product_{index}_base_price"
            )
            price = cleaned_data.get(price_field)
            if label and price is not None:
                product_data = {
                    "value": value,
                    "label": label,
                    "label_en": label_en,
                    "base_unit_price": str(price),
                }
                sizes = cleaned_data.get(f"product_{index}_sizes_json")
                groups = cleaned_data.get(f"product_{index}_modifier_groups_json")
                previous = normalized_products[index] if index < len(normalized_products) else None
                if previous is None:
                    baseline_source = {
                        **(self.pricing_source or {}),
                        "products": [
                            {
                                "value": value,
                                "label": label,
                                "label_en": label_en,
                                "base_unit_price": str(price),
                            }
                        ],
                    }
                    previous = normalize_calculator_pricing(
                        baseline_source
                    )["products"][0]
                if sizes:
                    self._validate_product_sizes(sizes, index)
                    if previous is None or sizes != [
                        {
                            "value": item["value"],
                            "label": item["label"],
                            "base_price": str(item["base_price"]),
                        }
                        for item in previous["sizes"]
                    ]:
                        product_data["sizes"] = sizes
                if groups:
                    self._validate_product_modifier_groups(groups, index)
                    if previous is None or groups != [
                        {
                            "value": item["value"],
                            "label": item["label"],
                            "label_en": item["label_en"],
                            "options": [
                                {
                                    "value": option["value"],
                                    "label": option["label"],
                                    "label_en": option["label_en"],
                                    "amount": str(option["amount"]),
                                    "amount_type": option["amount_type"],
                                }
                                for option in item["options"]
                            ],
                        }
                        for item in previous["modifier_groups"]
                    ]:
                        product_data["modifier_groups"] = groups
                lead_time_rules_field = f"product_{index}_lead_time_rules_json"
                if self.is_bound and lead_time_rules_field not in self.data:
                    lead_time_rules = previous.get("lead_time_rules", [])
                else:
                    lead_time_rules = cleaned_data.get(lead_time_rules_field) or []
                groups_for_validation = (
                    groups
                    if isinstance(groups, list) and groups
                    else previous.get("modifier_groups", [])
                )
                self._validate_product_lead_time_rules(
                    lead_time_rules,
                    groups_for_validation,
                    index,
                )
                product_data["lead_time_rules"] = lead_time_rules
                products.append(product_data)
        if products:
            cleaned_data["products"] = products
        option_catalog = {}
        option_image_inputs = {}
        for group in ("flavors", "shapes", "coatings", "packaging"):
            count_name = f"option_{group}_count"
            if self.is_bound and count_name not in self.data:
                option_catalog[group] = [
                    {**option, "extra": str(option["extra"])}
                    for option in self.option_catalog[group]
                ]
                continue
            count = cleaned_data.get(count_name)
            count = (
                count
                if count is not None
                else self.option_group_counts[group]
            )
            submitted_options = {}
            seen_labels = set()
            seen_labels_en = set()
            for index in range(min(count, self.MAX_OPTIONS)):
                value_name = f"option_{group}_{index}_value"
                label_name = f"option_{group}_{index}_label"
                label_en_name = f"option_{group}_{index}_label_en"
                extra_name = f"option_{group}_{index}_extra"
                label = (cleaned_data.get(label_name) or "").strip()
                label_en = (cleaned_data.get(label_en_name) or "").strip()
                value = (cleaned_data.get(value_name) or "").strip()
                if not value:
                    value = slugify(label or label_en, allow_unicode=True)[:32]
                if not value:
                    self.add_error(
                        label_name,
                        "Enter at least one option name."
                        if (get_language() or "").startswith("en")
                        else "Укажите хотя бы одно название опции.",
                    )
                    continue
                if not (label or label_en):
                    self.add_error(
                        label_name,
                        "Enter at least one option name."
                        if (get_language() or "").startswith("en")
                        else "Укажите хотя бы одно название опции.",
                    )
                    continue
                if value in submitted_options:
                    self.add_error(
                        label_name,
                        "Option names must be unique."
                        if (get_language() or "").startswith("en")
                        else "Названия опций должны быть уникальными.",
                    )
                    continue
                label_key = label.casefold()
                label_en_key = label_en.casefold()
                if (
                    (label_key and label_key in seen_labels)
                    or (label_en_key and label_en_key in seen_labels_en)
                ):
                    self.add_error(
                        label_name,
                        "Option names must be unique."
                        if (get_language() or "").startswith("en")
                        else "Названия опций должны быть уникальными.",
                    )
                    continue
                if label_key:
                    seen_labels.add(label_key)
                if label_en_key:
                    seen_labels_en.add(label_en_key)
                extra = (
                    cleaned_data.get(extra_name, 0)
                    if group != "shapes"
                    else 0
                )
                option = {
                    "value": value,
                    "label": label or label_en,
                    "label_en": label_en or label,
                    "extra": str(extra or 0),
                    "active": True,
                }
                submitted_options[value] = option
                option_image_inputs[(group, value)] = {
                    "image_name": f"option_image_{group}_{index}",
                    "label": option["label"],
                    "label_en": option["label_en"],
                }
            if not submitted_options:
                self.add_error(
                    None,
                    "Keep at least one option in each group."
                    if (get_language() or "").startswith("en")
                    else "В каждой группе должна остаться хотя бы одна опция.",
                )
            group_catalog = []
            for previous in self.option_catalog[group]:
                current = submitted_options.pop(previous["value"], None)
                if current is not None:
                    group_catalog.append(current)
                else:
                    archived = {
                        **previous,
                        "extra": str(previous["extra"]),
                    }
                    if archived["active"]:
                        archived["active"] = False
                    group_catalog.append(archived)
            group_catalog.extend(submitted_options.values())
            option_catalog[group] = group_catalog

        tiers = []
        for slot in range(1, 4):
            threshold_name = f"discount_quantity_{slot}"
            percent_name = f"discount_percent_{slot}"
            threshold = cleaned_data.get(threshold_name)
            percent = cleaned_data.get(percent_name)
            if (threshold is None) != (percent is None):
                message = (
                    "Enter both a quantity and a discount."
                    if (get_language() or "").startswith("en")
                    else "Укажите и количество, и размер скидки."
                )
                self.add_error(threshold_name, message)
                self.add_error(percent_name, message)
            elif threshold is not None and percent is not None:
                tiers.append((threshold, percent))
        if len({threshold for threshold, _ in tiers}) != len(tiers):
            message = (
                "Discount quantities must be unique."
                if (get_language() or "").startswith("en")
                else "Пороговые количества скидок не должны повторяться."
            )
            self.add_error(None, message)
        payment_methods = cleaned_data.get("payment_methods_json") or []
        discount_rules = cleaned_data.get("discount_rules_json") or []
        self._validate_payment_methods(payment_methods)
        self._validate_discount_rules(
            discount_rules,
            {method.get("value") for method in payment_methods if isinstance(method, dict)},
        )
        cleaned_data["pricing"] = {
            "base_unit_price": str(
                products[0]["base_unit_price"]
                if products
                else cleaned_data.get("base_unit_price", 0)
            ),
            "products": products,
            "size_multipliers": {
                value: str(cleaned_data.get(f"size_multiplier_{value}", 0))
                for value, _ in SIZE_CHOICES
            },
            "flavor_additions": {
                option["value"]: option["extra"]
                for option in option_catalog["flavors"]
            },
            "coating_additions": {
                option["value"]: option["extra"]
                for option in option_catalog["coatings"]
            },
            "packaging_additions": {
                option["value"]: option["extra"]
                for option in option_catalog["packaging"]
            },
            "delivery_costs": {
                value: str(cleaned_data.get(f"delivery_cost_{value}", 0))
                for value, _ in DELIVERY_CHOICES
            },
            "discount_tiers": [
                list(tier) for tier in sorted(tiers, reverse=True)
            ],
            "lead_time_days": cleaned_data.get("lead_time_days", 1),
            "option_catalog": option_catalog,
            "payment_methods": payment_methods,
            "discount_rules": discount_rules,
        }
        cleaned_data["option_image_inputs"] = option_image_inputs
        return cleaned_data

    def _add_configuration_error(self, field_name, message):
        self.add_error(field_name, message)

    def _validate_product_sizes(self, sizes, product_index):
        if (
            not isinstance(sizes, list)
            or not sizes
            or len(sizes) > self.MAX_SIZES
        ):
            self._add_configuration_error(
                f"product_{product_index}_sizes_json",
                "Each product must have at least one size.",
            )
            return
        values = set()
        for item in sizes:
            if not isinstance(item, dict):
                raise ValidationError("Invalid product size configuration.")
            value = str(item.get("value", "")).strip()
            label = str(item.get("label", "")).strip()
            try:
                price = Decimal(str(item.get("base_price", "")))
            except (InvalidOperation, TypeError, ValueError):
                price = Decimal("-1")
            if (
                not value
                or len(value) > 20
                or not label
                or len(label) > 80
                or value in values
                or price < 0
            ):
                self._add_configuration_error(
                    f"product_{product_index}_sizes_json",
                    "Sizes need unique values, names, and non-negative prices.",
                )
                return
            values.add(value)

    def _validate_product_modifier_groups(self, groups, product_index):
        if (
            not isinstance(groups, list)
            or not groups
            or len(groups) > self.MAX_MODIFIER_GROUPS
        ):
            self._add_configuration_error(
                f"product_{product_index}_modifier_groups_json",
                "Each product must have at least one modifier group.",
            )
            return
        group_values = set()
        for group in groups:
            if not isinstance(group, dict):
                raise ValidationError("Invalid modifier group configuration.")
            value = str(group.get("value", "")).strip()
            if (
                not value
                or len(value) > 32
                or value in group_values
                or not str(group.get("label", "")).strip()
                or len(str(group.get("label", ""))) > 100
                or not str(group.get("label_en", "")).strip()
                or len(str(group.get("label_en", ""))) > 100
            ):
                self._add_configuration_error(
                    f"product_{product_index}_modifier_groups_json",
                    "Modifier groups require unique values and names in both languages.",
                )
                return
            group_values.add(value)
            option_values = set()
            options = group.get("options")
            if (
                not isinstance(options, list)
                or not options
                or len(options) > self.MAX_OPTIONS
            ):
                self._add_configuration_error(
                    f"product_{product_index}_modifier_groups_json",
                    "Each modifier group must have at least one option.",
                )
                return
            for option in options:
                if not isinstance(option, dict):
                    raise ValidationError("Invalid modifier option configuration.")
                option_value = str(option.get("value", "")).strip()
                try:
                    amount = Decimal(str(option.get("amount", "")))
                except (InvalidOperation, TypeError, ValueError):
                    amount = Decimal("-1")
                if (
                    not option_value
                    or len(option_value) > 32
                    or option_value in option_values
                    or not str(option.get("label", "")).strip()
                    or len(str(option.get("label", ""))) > 100
                    or not str(option.get("label_en", "")).strip()
                    or len(str(option.get("label_en", ""))) > 100
                    or (
                        option.get("amount_type") == "percent"
                        and amount < 0
                    )
                    or option.get("amount_type") not in ("fixed", "percent")
                ):
                    self._add_configuration_error(
                        f"product_{product_index}_modifier_groups_json",
                        "Modifier options require unique values, names, and valid non-negative prices.",
                    )
                    return
                option_values.add(option_value)

    def _validate_product_lead_time_rules(self, rules, groups, product_index):
        field_name = f"product_{product_index}_lead_time_rules_json"
        if not isinstance(rules, list) or len(rules) > 100:
            self._add_configuration_error(
                field_name,
                "Invalid lead-time rules."
                if (get_language() or "").startswith("en")
                else "Некорректный список правил срока изготовления.",
            )
            return

        coating_groups = [
            group
            for group in groups
            if isinstance(group, dict) and is_coating_modifier_group(group)
        ]
        coating_options = set()
        if coating_groups:
            options = coating_groups[0].get("options")
            if isinstance(options, list):
                coating_options = {
                    str(option.get("value", "")).strip()
                    for option in options
                    if isinstance(option, dict)
                }
        english = (get_language() or "").startswith("en")
        seen_thresholds = set()
        for rule in rules:
            if not isinstance(rule, dict):
                self._add_configuration_error(
                    field_name,
                    "Invalid lead-time rule."
                    if english
                    else "Некорректное правило срока изготовления.",
                )
                return
            coating_value = str(rule.get("coating_value", "")).strip()
            min_quantity = self._positive_integer(rule.get("min_quantity"))
            days = self._positive_integer(rule.get("days"))
            if min_quantity is None or days is None:
                self._add_configuration_error(
                    field_name,
                    (
                        "Each lead-time rule needs a quantity and number of days."
                        if english
                        else "Для каждого правила укажите количество и срок изготовления."
                    ),
                )
                return
            threshold_key = (coating_value, min_quantity)
            if (
                not 1 <= min_quantity <= 10000
                or not 1 <= days <= 365
                or not coating_value
                or len(coating_value) > 32
                or coating_value not in coating_options
                or threshold_key in seen_thresholds
            ):
                self._add_configuration_error(
                    field_name,
                    (
                        "Lead-time rules need valid, unique quantities and coating options."
                        if english
                        else "Для правил укажите существующие варианты покрытия и уникальные пороги."
                    ),
                )
                return
            seen_thresholds.add(threshold_key)

    @staticmethod
    def _positive_integer(value):
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return None

    def _validate_payment_methods(self, methods):
        if not isinstance(methods, list) or not methods:
            self._add_configuration_error(
                "payment_methods_json",
                "At least one payment method is required.",
            )
            return
        values = set()
        for method in methods:
            if not isinstance(method, dict):
                raise ValidationError("Invalid payment method configuration.")
            value = str(method.get("value", "")).strip()
            if (
                not value
                or len(value) > 32
                or value in values
                or not str(method.get("label", "")).strip()
                or len(str(method.get("label", ""))) > 100
                or not str(method.get("label_en", "")).strip()
                or len(str(method.get("label_en", ""))) > 100
            ):
                self._add_configuration_error(
                    "payment_methods_json",
                    "Payment methods require unique values and names in both languages.",
                )
                return
            values.add(value)

    def _validate_discount_rules(self, rules, payment_values):
        if not isinstance(rules, list) or len(rules) > self.MAX_DISCOUNT_RULES:
            self._add_configuration_error("discount_rules_json", "Invalid discount rules.")
            return
        values = set()
        for rule in rules:
            if not isinstance(rule, dict):
                raise ValidationError("Invalid discount rule configuration.")
            value = str(rule.get("value", "")).strip()
            trigger = rule.get("trigger")
            trigger_value = str(rule.get("trigger_value", "")).strip()
            try:
                amount = Decimal(str(rule.get("amount", "")))
            except (InvalidOperation, TypeError, ValueError):
                amount = Decimal("-1")
            if (
                not value
                or len(value) > 32
                or value in values
                or not str(rule.get("label", "")).strip()
                or len(str(rule.get("label", ""))) > 100
                or not str(rule.get("label_en", "")).strip()
                or len(str(rule.get("label_en", ""))) > 100
                or trigger not in ("quantity", "payment")
                or not trigger_value
                or (trigger == "quantity" and not trigger_value.isdigit())
                or (
                    trigger == "payment"
                    and trigger_value not in payment_values
                )
                or rule.get("amount_type") not in ("fixed", "percent")
                or amount < 0
                or (rule.get("amount_type") == "percent" and amount > 100)
                or (
                    rule.get("amount_type") == "percent"
                    and amount != amount.to_integral_value()
                )
            ):
                self._add_configuration_error(
                    "discount_rules_json",
                    "Discount rules need a unique name, valid trigger, and non-negative amount.",
                )
                return
            values.add(value)
