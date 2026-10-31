from django.conf import settings
from django.db import models


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
    company_name = models.CharField("Организация", max_length=200, blank=True)
    inn = models.CharField("ИНН", max_length=12, blank=True)
    kpp = models.CharField("КПП", max_length=9, blank=True)
    legal_address = models.CharField("Юридический адрес", max_length=500, blank=True)
    delivery_address = models.CharField("Адрес доставки", max_length=300, blank=True)
    contact_name = models.CharField("Контактное лицо", max_length=200, blank=True)
    phone = models.CharField("Телефон", max_length=32, blank=True)

    class Meta:
        verbose_name = "Профиль клиента"
        verbose_name_plural = "Профили клиентов"

    def __str__(self):
        if self.customer_type == self.CustomerType.LEGAL_ENTITY:
            return self.company_name or self.user.get_username()
        return self.user.get_username()
