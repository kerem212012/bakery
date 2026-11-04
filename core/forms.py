from pathlib import Path

from django import forms
from django.forms import BaseModelFormSet
from django.core.exceptions import ValidationError
from django.utils.translation import get_language

from .calculator import (
    COATING_CHOICES,
    DELIVERY_CHOICES,
    FLAVOR_CHOICES,
    PACKAGING_CHOICES,
    PAYMENT_CHOICES,
    SHAPE_CHOICES,
    SIZE_CHOICES,
    localized_choices,
)
from .models import (
    FeedbackSubmission,
    HomeHeroSlide,
    Preorder,
    SiteContentBlock,
    SitePageContent,
    SitePageSection,
)

MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024
MAX_ATTACHMENT_COUNT = 5

SITE_PAGE_CONTENT_DEFAULTS = {
    SitePageContent.Page.ABOUT: {
        "eyebrow": "История Лукоморья",
        "eyebrow_en": "The story of Lukomorye",
        "title": "О нас",
        "title_en": "About us",
        "subtitle": "Лукоморье — идеи, воплощённые в деталях.",
        "subtitle_en": "Lukomorye — ideas, crafted in every detail.",
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
        "title": "Партнёрство с Лукоморье",
        "title_en": "Partner with Lukomorye",
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
    flavor = forms.ChoiceField(choices=FLAVOR_CHOICES)
    quantity = forms.IntegerField(min_value=1, max_value=10000, initial=100)
    size = forms.ChoiceField(choices=SIZE_CHOICES)
    shape = forms.ChoiceField(choices=SHAPE_CHOICES)
    coating = forms.ChoiceField(choices=COATING_CHOICES)
    packaging = forms.ChoiceField(choices=PACKAGING_CHOICES)
    delivery = forms.ChoiceField(choices=DELIVERY_CHOICES)
    payment = forms.ChoiceField(choices=PAYMENT_CHOICES)
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, group in (
            ("flavor", "flavor"),
            ("shape", "shape"),
            ("coating", "coating"),
            ("packaging", "packaging"),
            ("delivery", "delivery"),
            ("payment", "payment"),
        ):
            self.fields[field_name].choices = localized_choices(
                self.fields[field_name].choices,
                group,
            )
        self.fields["name"].widget.attrs["placeholder"] = "Как к вам обращаться"
        self.fields["flavor"].initial = "classic"
        self.fields["quantity"].initial = 100
        self.fields["size"].initial = "5"
        self.fields["shape"].initial = "heart"
        self.fields["coating"].initial = "icing"
        self.fields["packaging"].initial = "ribbon"
        self.fields["delivery"].initial = "moscow"
        self.fields["payment"].initial = "organization"
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
            "value": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 2}
            ),
            "value_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 2}
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
        }


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
            "eyebrow",
            "eyebrow_en",
            "title",
            "title_en",
            "description",
            "description_en",
            "image",
            "display_order",
            "is_active",
        )
        widgets = {
            "eyebrow": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "eyebrow_en": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "title": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "title_en": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 4}
            ),
            "description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 4}
            ),
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
                "eyebrow": "Small heading (Russian)",
                "eyebrow_en": "Small heading (English)",
                "title": "Heading (Russian)",
                "title_en": "Heading (English)",
                "description": "Description (Russian)",
                "description_en": "Description (English)",
                "image": "Banner photo",
                "is_active": "Show this slide",
            }
            for field_name, label in labels.items():
                self.fields[field_name].label = label

            self.fields["image"].help_text = (
                "Leave empty to keep the current banner photo."
            )
        self.fields["image"].widget.attrs["accept"] = "image/jpeg,image/png,image/webp"


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
            "url": forms.TextInput(attrs={"class": "site-content-form-control"}),
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
        if self.instance.pk:
            self.initial["display_order"] = self.instance.display_order + 1
        if (get_language() or "").startswith("en"):
            self.fields["display_order"].label = "Display order"
        else:
            self.fields["display_order"].label = "Порядок отображения"

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
