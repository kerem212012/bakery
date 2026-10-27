from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import CustomerProfile


User = get_user_model()


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Логин",
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}),
    )
    password = forms.CharField(
        label="Пароль",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Логин"
        self.fields["password"].label = "Пароль"


class RegistrationForm(UserCreationForm):
    customer_type = forms.ChoiceField(
        label="Тип клиента",
        choices=CustomerProfile.CustomerType.choices,
        initial=CustomerProfile.CustomerType.INDIVIDUAL,
        widget=forms.RadioSelect,
    )
    company_name = forms.CharField(label="Название организации", max_length=200, required=False)
    inn = forms.RegexField(
        label="ИНН",
        regex=r"^\d{10}(?:\d{2})?$",
        max_length=12,
        required=False,
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
    legal_address = forms.CharField(
        label="Юридический адрес",
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "autocomplete": "street-address"}),
    )
    contact_name = forms.CharField(label="Контактное лицо", max_length=200, required=False)
    phone = forms.CharField(
        label="Телефон",
        max_length=32,
        required=False,
        widget=forms.TextInput(attrs={"type": "tel", "autocomplete": "tel"}),
    )
    username = forms.CharField(
        label="Логин",
        help_text="До 150 символов: буквы, цифры и символы @ . + - _.",
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
        fields = ("username", "first_name", "last_name", "email")
        labels = {
            "username": "Логин",
            "first_name": "Имя",
            "last_name": "Фамилия",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(
            (
                "customer_type",
                "username",
                "first_name",
                "last_name",
                "email",
                "password1",
                "password2",
                "company_name",
                "inn",
                "kpp",
                "legal_address",
                "contact_name",
                "phone",
            )
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Аккаунт с такой почтой уже существует.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("customer_type") == CustomerProfile.CustomerType.LEGAL_ENTITY:
            for field_name in (
                "company_name",
                "inn",
                "kpp",
                "legal_address",
                "contact_name",
                "phone",
            ):
                if not cleaned_data.get(field_name, "").strip():
                    self.add_error(field_name, "Обязательное поле для юридического лица.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            self.save_m2m()
            CustomerProfile.objects.create(
                user=user,
                customer_type=self.cleaned_data["customer_type"],
                company_name=self.cleaned_data.get("company_name", "").strip(),
                inn=self.cleaned_data.get("inn", "").strip(),
                kpp=self.cleaned_data.get("kpp", "").strip(),
                legal_address=self.cleaned_data.get("legal_address", "").strip(),
                contact_name=self.cleaned_data.get("contact_name", "").strip(),
                phone=self.cleaned_data.get("phone", "").strip(),
            )
        return user


class AccountProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
        labels = {
            "first_name": "Имя",
            "last_name": "Фамилия",
            "email": "Электронная почта",
        }
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Аккаунт с такой почтой уже существует.")
        return email
