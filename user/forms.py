from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserCreationForm,
)
from django.utils.text import slugify
from django.utils import timezone
from django.utils.translation import get_language

from .models import CustomerDeliveryAddress, CustomerProfile


User = get_user_model()


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="Электронная почта",
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )
    password = forms.CharField(
        label="Пароль",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if get_language() == "en":
            self.fields["username"].label = "Email"
            self.fields["password"].label = "Password"
        else:
            self.fields["username"].label = "Электронная почта"
            self.fields["password"].label = "Пароль"

    def clean(self):
        email = self.cleaned_data.get("username")
        if email:
            matching_usernames = list(
                User.objects.filter(email__iexact=email).values_list(
                    "username", flat=True
                )[:2]
            )
            if len(matching_usernames) == 1:
                self.cleaned_data["username"] = matching_usernames[0]
        return super().clean()


class RegistrationForm(UserCreationForm):
    agreement_accepted = forms.BooleanField(
        required=True,
        error_messages={
            "required": "Необходимо принять пользовательское соглашение."
        },
    )
    personal_data_consent = forms.BooleanField(
        required=True,
        error_messages={
            "required": "Необходимо дать согласие на обработку персональных данных."
        },
    )
    inn = forms.RegexField(
        label="ИНН",
        regex=r"^\d{10}(?:\d{2})?$",
        max_length=12,
        required=True,
        error_messages={"invalid": "Введите 10 или 12 цифр."},
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
    )
    kpp = forms.RegexField(
        label="КПП",
        regex=r"^\d{9}$",
        max_length=9,
        required=False,
        error_messages={"invalid": "Введите 9 цифр."},
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
    )
    phone = forms.CharField(
        label="Телефон",
        max_length=32,
        required=True,
        widget=forms.TextInput(attrs={"type": "tel", "autocomplete": "tel"}),
    )
    password1 = forms.CharField(
        label="Пароль",
        strip=False,
        widget=forms.PasswordInput,
        help_text="Используйте не менее 8 символов и не выбирайте слишком простой пароль.",
    )
    password2 = forms.CharField(
        label="Повторите пароль",
        strip=False,
        widget=forms.PasswordInput,
        help_text="Введите пароль ещё раз для подтверждения.",
    )
    email = forms.EmailField(label="Электронная почта")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "last_name", "email")
        labels = {
            "first_name": "Имя",
            "last_name": "Фамилия",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(
            (
                "first_name",
                "last_name",
                "email",
                "inn",
                "kpp",
                "phone",
                "password1",
                "password2",
                "agreement_accepted",
                "personal_data_consent",
            )
        )
        if get_language() == "en":
            labels = {
                "first_name": "First name",
                "last_name": "Last name",
                "email": "Email",
                "password1": "Password",
                "password2": "Confirm password",
                "inn": "Tax ID",
                "kpp": "Registration code",
                "phone": "Phone",
                "agreement_accepted": "I accept the User Agreement",
                "personal_data_consent": "I consent to the processing of my personal data",
            }
            for field_name, label in labels.items():
                self.fields[field_name].label = label
            self.fields["inn"].error_messages["invalid"] = "Enter 10 or 12 digits."
            self.fields["kpp"].error_messages["invalid"] = "Enter 9 digits."
            self.fields["agreement_accepted"].error_messages["required"] = (
                "You must accept the User Agreement."
            )
            self.fields["personal_data_consent"].error_messages["required"] = (
                "You must consent to the processing of your personal data."
            )
            self.fields["password1"].help_text = (
                "Use at least 8 characters and avoid a commonly used password."
            )
            self.fields["password2"].help_text = "Enter your password again to confirm."

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            message = (
                "An account with this email already exists."
                if get_language() == "en"
                else "Аккаунт с такой почтой уже существует."
            )
            raise forms.ValidationError(message)
        return email

    def clean(self):
        cleaned_data = super().clean()
        for field_name in ("inn", "phone"):
            if not cleaned_data.get(field_name, "").strip():
                message = (
                    "This field is required for business accounts."
                    if get_language() == "en"
                    else "Обязательное поле для юридического лица."
                )
                self.add_error(field_name, message)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        username_base = slugify(user.email.partition("@")[0])[:140] or "customer"
        username = username_base
        suffix = 2
        while User.objects.filter(username=username).exists():
            username = f"{username_base[: 150 - len(str(suffix)) - 1]}-{suffix}"
            suffix += 1
        user.username = username
        if commit:
            user.save()
            self.save_m2m()
            accepted_at = timezone.now()
            CustomerProfile.objects.create(
                user=user,
                customer_type=CustomerProfile.CustomerType.LEGAL_ENTITY,
                inn=self.cleaned_data.get("inn", "").strip(),
                kpp=self.cleaned_data.get("kpp", "").strip(),
                phone=self.cleaned_data.get("phone", "").strip(),
                terms_accepted_at=accepted_at,
                personal_data_consent_at=accepted_at,
            )
        return user


class AccountProfileForm(forms.ModelForm):
    phone = forms.CharField(
        label="Телефон",
        max_length=32,
        required=False,
        widget=forms.TextInput(attrs={"type": "tel", "autocomplete": "tel"}),
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
        labels = {
            "first_name": "Имя",
            "last_name": "Фамилия",
            "email": "Электронная почта",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if get_language() == "en":
            self.fields["first_name"].label = "First name"
            self.fields["last_name"].label = "Last name"
            self.fields["email"].label = "Email"
            self.fields["phone"].label = "Phone"
        if self.instance.pk:
            self.initial.setdefault(
                "phone",
                CustomerProfile.objects.filter(user=self.instance)
                .values_list("phone", flat=True)
                .first()
                or "",
            )
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            message = (
                "An account with this email already exists."
                if get_language() == "en"
                else "Аккаунт с такой почтой уже существует."
            )
            raise forms.ValidationError(message)
        return email

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            CustomerProfile.objects.update_or_create(
                user=user,
                defaults={"phone": self.cleaned_data["phone"].strip()},
            )
        return user


class AccountPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        english = get_language() == "en"
        labels = {
            "old_password": "Current password" if english else "Текущий пароль",
            "new_password1": "New password" if english else "Новый пароль",
            "new_password2": (
                "Confirm new password" if english else "Повторите новый пароль"
            ),
        }
        autocomplete_values = {
            "old_password": "current-password",
            "new_password1": "new-password",
            "new_password2": "new-password",
        }
        for field_name, label in labels.items():
            self.fields[field_name].label = label
            self.fields[field_name].widget.attrs["autocomplete"] = (
                autocomplete_values[field_name]
            )


class DeliveryAddressForm(forms.ModelForm):
    class Meta:
        model = CustomerDeliveryAddress
        fields = ("delivery_address",)
        labels = {"delivery_address": "Адрес доставки"}
        widgets = {
            "delivery_address": forms.Textarea(
                attrs={
                    "rows": 3,
                    "autocomplete": "street-address",
                    "placeholder": "Город, улица, дом, квартира и удобное время",
                }
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if get_language() == "en":
            self.fields["delivery_address"].label = "Delivery address"
            self.fields["delivery_address"].widget.attrs["placeholder"] = (
                "City, street, building, apartment, and preferred delivery time"
            )

    def clean_delivery_address(self):
        address = self.cleaned_data["delivery_address"].strip()
        existing_addresses = CustomerDeliveryAddress.objects.filter(
            profile=self.instance.profile,
            delivery_address=address,
        )
        if self.instance.pk:
            existing_addresses = existing_addresses.exclude(pk=self.instance.pk)
        if existing_addresses.exists():
            message = (
                "This delivery address is already saved."
                if get_language() == "en"
                else "Этот адрес доставки уже сохранён."
            )
            raise forms.ValidationError(message)
        return address
