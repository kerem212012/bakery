from pathlib import Path

from django import forms
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

MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024
MAX_ATTACHMENT_COUNT = 5
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
