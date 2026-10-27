from django.core.validators import FileExtensionValidator
from django.db import models


def preorder_attachment_path(instance, filename):
    return f"preorders/{instance.preorder_id}/{filename}"


class Preorder(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новая"
        CONTACTED = "contacted", "Связались"
        COMPLETED = "completed", "Выполнена"
        CANCELLED = "cancelled", "Отменена"

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
