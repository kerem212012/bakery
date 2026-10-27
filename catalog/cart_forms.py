from django import forms

from core.calculator import DELIVERY_CHOICES, PAYMENT_CHOICES
from core.forms import MultipleFileField


SIZE_OPTIONS = ("6", "8", "10", "12", "15")
COATING_OPTIONS = (
    ("painting", "Роспись на айсинге"),
    ("printing", "Печать на айсинге"),
    ("classic", "Классическое"),
    ("chocolate", "Шоколадное"),
    ("none", "Без покрытия"),
)
DOUGH_OPTIONS = (
    ("classic", "Классическое"),
    ("chocolate", "Шоколадное"),
    ("vanilla", "Ванильное"),
    ("spiced", "Пряное"),
)
PACKAGING_OPTIONS = (
    ("gift_box", "Подарочная коробка"),
    ("kraft_box", "Крафт коробка"),
    ("individual", "Индивидуальная упаковка"),
    ("none", "Без упаковки"),
)


class CartItemForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=99, initial=1)
    size = forms.ChoiceField(
        choices=tuple((size, f"{size} см") for size in SIZE_OPTIONS),
        initial="8",
    )
    coating = forms.ChoiceField(choices=COATING_OPTIONS, initial="painting")
    dough = forms.ChoiceField(choices=DOUGH_OPTIONS, initial="classic")
    packaging = forms.ChoiceField(choices=PACKAGING_OPTIONS, initial="gift_box")


class CartCheckoutForm(forms.Form):
    delivery = forms.ChoiceField(choices=DELIVERY_CHOICES, initial="moscow")
    payment = forms.ChoiceField(choices=PAYMENT_CHOICES, initial="card")
    name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={"placeholder": "Как к вам обращаться"}))
    phone = forms.CharField(
        max_length=32,
        widget=forms.TextInput(attrs={"type": "tel", "placeholder": "+7 (000) 000-00-00"}),
    )
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": "Введите email"}))
    address = forms.CharField(
        max_length=300,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Адрес, временной интервал"}),
    )
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Напишите комментарий"}),
    )
    attachments = MultipleFileField(required=False)
    consent_given = forms.BooleanField(
        required=True,
        error_messages={"required": "Необходимо дать согласие на обработку данных."},
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("delivery") != "pickup" and not cleaned_data.get("address"):
            self.add_error("address", "Укажите адрес доставки.")
        return cleaned_data
