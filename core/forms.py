from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError

from .calculator import (
    COATING_CHOICES,
    DELIVERY_CHOICES,
    FLAVOR_CHOICES,
    PACKAGING_CHOICES,
    PAYMENT_CHOICES,
    SHAPE_CHOICES,
    SIZE_CHOICES,
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
            raise ValidationError(f"Можно загрузить не более {MAX_ATTACHMENT_COUNT} файлов.")
        cleaned_files = []
        for uploaded_file in files:
            cleaned_file = super().clean(uploaded_file, initial)
            extension = Path(cleaned_file.name).suffix.lower()
            if extension not in ALLOWED_ATTACHMENT_EXTENSIONS:
                raise ValidationError("Допустимы изображения JPG, PNG, WEBP и документы PDF.")
            if cleaned_file.size > MAX_ATTACHMENT_SIZE:
                raise ValidationError("Размер каждого файла не должен превышать 10 МБ.")
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
        self.fields["name"].widget.attrs["placeholder"] = "Как к вам обращаться"
        self.fields["flavor"].initial = "classic"
        self.fields["quantity"].initial = 100
        self.fields["size"].initial = "5"
        self.fields["shape"].initial = "heart"
        self.fields["coating"].initial = "icing"
        self.fields["packaging"].initial = "ribbon"
        self.fields["delivery"].initial = "moscow"
        self.fields["payment"].initial = "organization"

    def clean(self):
        cleaned_data = super().clean()
        if (
            cleaned_data.get("delivery") != "pickup"
            and not cleaned_data.get("address")
        ):
            self.add_error("address", "Укажите адрес доставки.")
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
