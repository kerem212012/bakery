from django.conf import settings
from django.db import models
from django.db.models import Q


class CustomerProfile(models.Model):
    class CustomerType(models.TextChoices):
        INDIVIDUAL = "individual", "Физическое лицо"
        LEGAL_ENTITY = "legal_entity", "Юридическое лицо"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )
    customer_type = models.CharField(
        "Тип клиента",
        max_length=20,
        choices=CustomerType.choices,
        default=CustomerType.INDIVIDUAL,
    )
    inn = models.CharField("ИНН", max_length=12, blank=True)
    kpp = models.CharField("КПП", max_length=9, blank=True)
    delivery_address = models.CharField("Адрес доставки", max_length=300, blank=True)
    phone = models.CharField("Телефон", max_length=32, blank=True)
    terms_accepted_at = models.DateTimeField(
        "Пользовательское соглашение принято",
        null=True,
        blank=True,
    )
    personal_data_consent_at = models.DateTimeField(
        "Согласие на обработку персональных данных дано",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Профиль клиента"
        verbose_name_plural = "Профили клиентов"

    def __str__(self):
        return self.user.get_username()


class CustomerDeliveryAddress(models.Model):
    profile = models.ForeignKey(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name="delivery_addresses",
        verbose_name="Профиль клиента",
    )
    delivery_address = models.CharField("Адрес доставки", max_length=300)
    is_default = models.BooleanField("Адрес по умолчанию", default=False)

    class Meta:
        ordering = ("-is_default", "pk")
        constraints = [
            models.UniqueConstraint(
                fields=("profile",),
                condition=Q(is_default=True),
                name="user_single_default_delivery_address",
            ),
            models.UniqueConstraint(
                fields=("profile", "delivery_address"),
                name="user_unique_delivery_address_per_profile",
            ),
        ]
        verbose_name = "адрес доставки клиента"
        verbose_name_plural = "адреса доставки клиентов"

    def __str__(self):
        return self.delivery_address
