from django.db import models
from django.utils.text import slugify
from django.utils.translation import get_language


class SluggedModel(models.Model):
    name = models.CharField(max_length=160)
    name_en = models.CharField(max_length=160, blank=True)
    slug = models.SlugField(max_length=180, unique=True, blank=True, allow_unicode=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name, allow_unicode=True) or "item"
            self.slug = base_slug
            suffix = 2
            while type(self).objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{suffix}"
                suffix += 1
        super().save(*args, **kwargs)

    @property
    def localized_name(self):
        if get_language() == "en" and self.name_en:
            return self.name_en
        return self.name


class Category(SluggedModel):
    description = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("display_order", "name")
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    @property
    def localized_description(self):
        if get_language() == "en" and self.description_en:
            return self.description_en
        return self.description


class Product(SluggedModel):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    description = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    filter_options = models.ManyToManyField(
        "ProductFilterOption",
        related_name="products",
        blank=True,
    )

    class Meta:
        ordering = ("display_order", "name")

    def __str__(self):
        return self.name

    @property
    def localized_description(self):
        if get_language() == "en" and self.description_en:
            return self.description_en
        return self.description


class ProductFilterOption(models.Model):
    class FilterType(models.TextChoices):
        SIZE = "size", "Размер"
        COATING = "coating", "Покрытие"
        DOUGH = "dough", "Вид теста"
        COLOR = "color", "Цвет"
        OCCASION = "occasion", "Повод"
        PACKAGING = "packaging", "Упаковка"

    filter_type = models.CharField(max_length=16, choices=FilterType.choices)
    value = models.SlugField(max_length=80)
    label = models.CharField(max_length=100)
    label_en = models.CharField(max_length=100, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ("display_order", "label")
        constraints = [
            models.UniqueConstraint(
                fields=("filter_type", "value"),
                name="unique_product_filter_option",
            )
        ]
        verbose_name = "параметр фильтра товара"
        verbose_name_plural = "параметры фильтров товаров"

    def __str__(self):
        label = self.label_en if get_language() == "en" and self.label_en else self.label
        return f"{self.get_filter_type_display()}: {label}"

    @property
    def localized_label(self):
        if get_language() == "en" and self.label_en:
            return self.label_en
        return self.label
