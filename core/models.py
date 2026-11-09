from django.core.validators import FileExtensionValidator
from django.conf import settings
from django.db import models
from django.utils.translation import get_language

from .calculator import default_calculator_pricing
from .storage import PrivateMediaStorage


def preorder_attachment_path(instance, filename):
    return f"preorders/{instance.preorder_id}/{filename}"


def preorder_contract_path(instance, filename):
    import uuid

    return f"order-contracts/{instance.preorder_id}/{uuid.uuid4().hex}.pdf"


def localized_content(instance, field_name):
    language = (get_language() or "").startswith("en")
    field = f"{field_name}_en" if language else field_name
    fallback = field_name if language else f"{field_name}_en"
    return getattr(instance, field) or getattr(instance, fallback)


class Preorder(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новая"
        CONTACTED = "contacted", "Подтверждена"
        PRODUCTION = "production", "В производстве"
        SHIPPING = "shipping", "В пути"
        COMPLETED = "completed", "Доставлена"
        CANCELLED = "cancelled", "Отменена"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Ожидает оплаты"
        PAID = "paid", "Оплачено"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="preorders",
        null=True,
        blank=True,
        verbose_name="Пользователь",
    )
    name = models.CharField("Имя", max_length=120)
    email = models.EmailField("Электронная почта")
    phone = models.CharField("Телефон", max_length=32)
    delivery_date = models.DateField("Дата доставки", null=True, blank=True)
    address = models.CharField("Адрес доставки", max_length=300, blank=True)
    comment = models.TextField("Комментарий", blank=True)
    configuration = models.JSONField("Параметры заказа")
    unit_price = models.DecimalField("Стоимость 1 шт.", max_digits=10, decimal_places=2)
    discount_percent = models.PositiveSmallIntegerField("Скидка, %")
    delivery_cost = models.DecimalField("Стоимость доставки", max_digits=10, decimal_places=2)
    total_price = models.DecimalField("Итого", max_digits=12, decimal_places=2)
    status = models.CharField(
        "Статус",
        max_length=12,
        choices=Status.choices,
        default=Status.NEW,
    )
    payment_status = models.CharField(
        "Статус оплаты",
        max_length=12,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    consent_given = models.BooleanField("Согласие на обработку данных")

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "предзаказ"
        verbose_name_plural = "предзаказы"

    def __str__(self):
        return f"Предзаказ #{self.pk} — {self.name}"


class PreorderAttachment(models.Model):
    preorder = models.ForeignKey(
        Preorder,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="Предзаказ",
    )
    file = models.FileField(
        "Файл",
        upload_to=preorder_attachment_path,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp", "pdf"])],
    )
    uploaded_at = models.DateTimeField("Загружено", auto_now_add=True)

    class Meta:
        verbose_name = "вложение предзаказа"
        verbose_name_plural = "вложения предзаказа"

    def __str__(self):
        return self.file.name


class PreorderContract(models.Model):
    preorder = models.OneToOneField(
        Preorder,
        on_delete=models.CASCADE,
        related_name="contract",
        verbose_name="Заказ",
    )
    file = models.FileField(
        "Договор",
        upload_to=preorder_contract_path,
        storage=PrivateMediaStorage(),
        validators=[FileExtensionValidator(["pdf"])],
    )
    uploaded_at = models.DateTimeField("Загружено", auto_now=True)

    class Meta:
        verbose_name = "договор заказа"
        verbose_name_plural = "договоры заказов"

    def __str__(self):
        return f"Договор заказа #{self.preorder_id}"


class FeedbackSubmission(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новое"
        IN_PROGRESS = "in_progress", "В работе"
        RESOLVED = "resolved", "Решено"

    class Source(models.TextChoices):
        CONTACT = "contact", "Контактная панель"
        FEEDBACK = "feedback", "Страница обратной связи"
        PARTNERSHIP = "partnership", "Партнёрство"
        BUSINESS_CLIENTS = "business_clients", "Корпоративным клиентам"
        OTHER = "other", "Другое"

    name = models.CharField("Имя", max_length=120)
    email = models.EmailField("Электронная почта")
    phone = models.CharField("Телефон", max_length=32, blank=True)
    subject = models.CharField("Тема", max_length=160)
    message = models.TextField("Сообщение", max_length=5000)
    consent_given = models.BooleanField("Согласие на обработку данных")
    source = models.CharField(
        "Источник",
        max_length=24,
        choices=Source.choices,
        default=Source.OTHER,
    )
    status = models.CharField(
        "Статус",
        max_length=16,
        choices=Status.choices,
        default=Status.NEW,
    )
    is_hidden = models.BooleanField("Скрыто", default=False)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "обращение обратной связи"
        verbose_name_plural = "обращения обратной связи"

    def __str__(self):
        return f"Обращение #{self.pk} — {self.subject}"


class SiteContentBlock(models.Model):
    class Page(models.TextChoices):
        ALL = "all", "Все страницы"
        HOME = "home", "Главная"
        ABOUT = "about", "О нас"
        BUSINESS_CLIENTS = "business_clients", "Корпоративным клиентам"
        PARTNERSHIP = "corporate", "Сотрудничество"
        CONTACTS = "contacts", "Контакты"
        DELIVERY = "delivery", "Доставка"
        FAQ = "faq", "Вопросы и ответы"
        FEEDBACK = "feedback", "Обратная связь"
        PACKAGING = "packaging", "Упаковка"
        CATALOG = "catalog", "Каталог"
        CATEGORIES = "categories", "Категории"
        CATEGORY = "category", "Страница категории"
        PRODUCT = "product", "Страница товара"

    page = models.CharField(
        "Страница сайта",
        max_length=24,
        choices=Page.choices,
        default=Page.HOME,
    )
    title = models.CharField("Заголовок", max_length=180, blank=True)
    title_en = models.CharField("Заголовок на английском", max_length=180, blank=True)
    description = models.TextField("Описание", blank=True)
    description_en = models.TextField("Описание на английском", blank=True)
    image = models.ImageField(
        "Фото сайта",
        upload_to="site-content/",
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
        help_text="Это редакционный контент страницы сайта, не фотография товара.",
    )
    display_order = models.PositiveIntegerField("Порядок отображения", default=0)
    is_active = models.BooleanField("Опубликовано", default=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        ordering = ("display_order", "pk")
        verbose_name = "блок контента сайта"
        verbose_name_plural = "контент сайта"

    def __str__(self):
        return self.title or self.get_page_display()

    @property
    def localized_title(self):
        if (get_language() or "").startswith("en") and self.title_en:
            return self.title_en
        return self.title

    @property
    def localized_description(self):
        if (get_language() or "").startswith("en") and self.description_en:
            return self.description_en
        return self.description


class SitePageContent(models.Model):
    class Page(models.TextChoices):
        ABOUT = "about", "О нас"
        BUSINESS_CLIENTS = "business_clients", "Корпоративным клиентам"
        PARTNERSHIP = "corporate", "Сотрудничество"
        CONTACTS = "contacts", "Контакты"
        DELIVERY = "delivery", "Доставка"
        FAQ = "faq", "Вопросы и ответы"
        FEEDBACK = "feedback", "Обратная связь"
        PACKAGING = "packaging", "Упаковка"
        CATALOG = "catalog", "Каталог"
        CATEGORIES = "categories", "Категории"

    page = models.CharField(
        "Страница сайта",
        max_length=24,
        choices=Page.choices,
        unique=True,
    )
    eyebrow = models.CharField("Надзаголовок", max_length=180, blank=True)
    eyebrow_en = models.CharField("Надзаголовок на английском", max_length=180, blank=True)
    title = models.CharField("Заголовок", max_length=180, blank=True)
    title_en = models.CharField("Заголовок на английском", max_length=180, blank=True)
    subtitle = models.TextField("Подзаголовок", blank=True)
    subtitle_en = models.TextField("Подзаголовок на английском", blank=True)
    description = models.TextField("Описание", blank=True)
    description_en = models.TextField("Описание на английском", blank=True)
    button_text = models.CharField("Текст кнопки", max_length=120, blank=True)
    button_text_en = models.CharField("Текст кнопки на английском", max_length=120, blank=True)
    button_url = models.CharField("Ссылка кнопки", max_length=500, blank=True)
    image = models.ImageField(
        "Фото верхнего блока",
        upload_to="site-pages/",
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
    )
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "контент страницы сайта"
        verbose_name_plural = "контент страниц сайта"

    def __str__(self):
        return self.get_page_display()

    @property
    def localized_eyebrow(self):
        return localized_content(self, "eyebrow")

    @property
    def localized_title(self):
        return localized_content(self, "title")

    @property
    def localized_subtitle(self):
        return localized_content(self, "subtitle")

    @property
    def localized_description(self):
        return localized_content(self, "description")

    @property
    def localized_button_text(self):
        return localized_content(self, "button_text")


class SitePageSection(models.Model):
    class Page(models.TextChoices):
        HOME = "home", "Главная"
        ABOUT = "about", "О нас"
        BUSINESS_CLIENTS = "business_clients", "Корпоративным клиентам"
        PARTNERSHIP = "corporate", "Сотрудничество"
        CONTACTS = "contacts", "Контакты"
        DELIVERY = "delivery", "Доставка"
        FAQ = "faq", "Вопросы и ответы"
        FEEDBACK = "feedback", "Обратная связь"
        PACKAGING = "packaging", "Упаковка"
        CATALOG = "catalog", "Каталог"
        CATEGORIES = "categories", "Категории"

    page = models.CharField("Страница сайта", max_length=24, choices=Page.choices)
    group = models.CharField("Группа контента", max_length=32)
    section_eyebrow = models.CharField("Надзаголовок раздела", max_length=180, blank=True)
    section_eyebrow_en = models.CharField(
        "Надзаголовок раздела на английском", max_length=180, blank=True
    )
    section_title = models.CharField("Заголовок раздела", max_length=180, blank=True)
    section_title_en = models.CharField(
        "Заголовок раздела на английском", max_length=180, blank=True
    )
    section_description = models.TextField("Описание раздела", blank=True)
    section_description_en = models.TextField(
        "Описание раздела на английском", blank=True
    )
    title = models.CharField("Заголовок", max_length=180, blank=True)
    title_en = models.CharField("Заголовок на английском", max_length=180, blank=True)
    description = models.TextField("Текст", blank=True)
    description_en = models.TextField("Текст на английском", blank=True)
    value = models.CharField("Значение", max_length=120, blank=True)
    value_en = models.CharField("Значение на английском", max_length=120, blank=True)
    url = models.CharField("Ссылка", max_length=500, blank=True)
    image = models.ImageField(
        "Изображение",
        upload_to="site-pages/sections/",
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
    )
    image_alt = models.CharField("Описание изображения", max_length=180, blank=True)
    image_alt_en = models.CharField(
        "Описание изображения на английском", max_length=180, blank=True
    )
    display_order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Показывать", default=True)

    class Meta:
        ordering = ("page", "group", "display_order", "pk")
        verbose_name = "элемент контента страницы"
        verbose_name_plural = "элементы контента страниц"

    def __str__(self):
        return self.title or f"{self.get_page_display()} — {self.group}"

    @property
    def localized_title(self):
        return localized_content(self, "title")

    @property
    def localized_section_title(self):
        return localized_content(self, "section_title")

    @property
    def localized_section_eyebrow(self):
        return localized_content(self, "section_eyebrow")

    @property
    def localized_section_description(self):
        return localized_content(self, "section_description")

    @property
    def localized_description(self):
        return localized_content(self, "description")

    @property
    def localized_value(self):
        return localized_content(self, "value")

    @property
    def localized_image_alt(self):
        return localized_content(self, "image_alt")


class HomeHeroSlide(models.Model):
    eyebrow = models.CharField("Надзаголовок", max_length=180, blank=True)
    eyebrow_en = models.CharField("Надзаголовок на английском", max_length=180, blank=True)
    title = models.CharField("Заголовок", max_length=180, blank=True)
    title_en = models.CharField("Заголовок на английском", max_length=180, blank=True)
    description = models.TextField("Описание", blank=True)
    description_en = models.TextField("Описание на английском", blank=True)
    button_text = models.CharField("Текст кнопки", max_length=120, blank=True)
    button_text_en = models.CharField("Текст кнопки на английском", max_length=120, blank=True)
    button_url = models.CharField("Ссылка кнопки", max_length=500, blank=True)
    image = models.ImageField(
        "Фото баннера",
        upload_to="site-pages/home/",
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
    )
    display_order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Показывать", default=True)

    class Meta:
        ordering = ("display_order", "pk")
        verbose_name = "баннер главной страницы"
        verbose_name_plural = "баннеры главной страницы"

    def __str__(self):
        return self.title or self.get_button_text_display()

    def get_button_text_display(self):
        return self.button_text or self.button_text_en or f"Баннер {self.pk or ''}"

    @property
    def localized_eyebrow(self):
        return localized_content(self, "eyebrow")

    @property
    def localized_title(self):
        return localized_content(self, "title")

    @property
    def localized_description(self):
        return localized_content(self, "description")

    @property
    def localized_button_text(self):
        return localized_content(self, "button_text")


class CalculatorSettings(models.Model):
    pricing = models.JSONField("Правила расчёта", default=default_calculator_pricing)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "настройка калькулятора"
        verbose_name_plural = "настройки калькулятора"

    def __str__(self):
        return "Настройки калькулятора"
