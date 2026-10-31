from django import forms
from django.utils.translation import get_language

from core.calculator import (
    DELIVERY_CHOICES,
    PAYMENT_CHOICES,
    localized_choices,
)
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


def localized_cart_options(options, group):
    translations = {
        "coating": {
            "painting": "Hand-painted icing",
            "printing": "Printed icing",
            "classic": "Classic",
            "chocolate": "Chocolate",
            "none": "No coating",
        },
        "dough": {
            "classic": "Classic",
            "chocolate": "Chocolate",
            "vanilla": "Vanilla",
            "spiced": "Spiced",
        },
        "packaging": {
            "gift_box": "Gift box",
            "kraft_box": "Kraft box",
            "individual": "Custom packaging",
            "none": "No packaging",
        },
    }
    if get_language() != "en":
        return options
    return tuple(
        (value, translations[group].get(value, label))
        for value, label in options
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if get_language() == "en":
            self.fields["size"].choices = tuple(
                (size, f"{size} cm") for size in SIZE_OPTIONS
            )
        self.fields["coating"].choices = localized_cart_options(COATING_OPTIONS, "coating")
        self.fields["dough"].choices = localized_cart_options(DOUGH_OPTIONS, "dough")
        self.fields["packaging"].choices = localized_cart_options(
            PACKAGING_OPTIONS,
            "packaging",
        )


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
            message = (
                "Enter a delivery address."
                if get_language() == "en"
                else "Укажите адрес доставки."
            )
            self.add_error("address", message)
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["delivery"].choices = localized_choices(DELIVERY_CHOICES, "delivery")
        self.fields["payment"].choices = localized_choices(PAYMENT_CHOICES, "payment")
        if get_language() == "en":
            self.fields["consent_given"].error_messages["required"] = (
                "You must agree to the processing of your personal data."
            )
            self.fields["name"].widget.attrs["placeholder"] = "Your name"
            self.fields["email"].widget.attrs["placeholder"] = "Enter your email"
            self.fields["address"].widget.attrs["placeholder"] = "Address and preferred time"
            self.fields["comment"].widget.attrs["placeholder"] = "Add a comment"
