from django import forms
from django.utils.translation import get_language

from .models import Category, Product, ProductFilterOption


class ProductEditorForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = (
            "name",
            "name_en",
            "category",
            "description",
            "description_en",
            "price",
            "image",
            "image_url",
            "filter_options",
            "display_order",
            "is_active",
            "is_featured",
        )
        widgets = {
            "name": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "name_en": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "category": forms.Select(attrs={"class": "site-content-form-control"}),
            "description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 4}
            ),
            "description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 4}
            ),
            "price": forms.NumberInput(
                attrs={"class": "site-content-form-control", "min": "0", "step": "0.01"}
            ),
            "image": forms.ClearableFileInput(
                attrs={"class": "site-content-form-control"}
            ),
            "image_url": forms.URLInput(
                attrs={"class": "site-content-form-control"}
            ),
            "filter_options": forms.SelectMultiple(
                attrs={"class": "site-content-form-control"}
            ),
            "display_order": forms.NumberInput(
                attrs={"class": "site-content-form-control", "min": 0}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "site-content-form-checkbox"}
            ),
            "is_featured": forms.CheckboxInput(
                attrs={"class": "site-content-form-checkbox"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        english = get_language() == "en"
        labels = {
            "name": "Name (Russian)" if english else "Название",
            "name_en": "Name (English)" if english else "Название на английском",
            "category": "Category" if english else "Категория",
            "description": "Description (Russian)" if english else "Описание",
            "description_en": "Description (English)" if english else "Описание на английском",
            "price": "Price" if english else "Цена",
            "image": "Product photo" if english else "Фото товара",
            "image_url": "Photo URL (optional)" if english else "Ссылка на фото (необязательно)",
            "filter_options": "Filter options" if english else "Параметры фильтров",
            "display_order": "Display order" if english else "Порядок отображения",
            "is_active": "Published" if english else "Опубликован",
            "is_featured": "Featured" if english else "Популярный товар",
        }
        for field_name, label in labels.items():
            self.fields[field_name].label = label
        self.fields["category"].queryset = Category.objects.all()
        self.fields["category"].label_from_instance = lambda category: category.localized_name
        self.fields["filter_options"].queryset = ProductFilterOption.objects.all()
        self.fields["filter_options"].required = False
        self.fields["image"].widget.attrs["accept"] = "image/jpeg,image/png,image/webp"


class CategoryEditorForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = (
            "name",
            "name_en",
            "description",
            "description_en",
            "image",
            "image_url",
            "display_order",
            "is_active",
        )
        widgets = {
            "name": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "name_en": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "description": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 4}
            ),
            "description_en": forms.Textarea(
                attrs={"class": "site-content-form-control", "rows": 4}
            ),
            "image": forms.ClearableFileInput(
                attrs={"class": "site-content-form-control"}
            ),
            "image_url": forms.URLInput(
                attrs={"class": "site-content-form-control"}
            ),
            "display_order": forms.NumberInput(
                attrs={"class": "site-content-form-control", "min": 0}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "site-content-form-checkbox"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        english = get_language() == "en"
        labels = {
            "name": "Name (Russian)" if english else "Название",
            "name_en": "Name (English)" if english else "Название на английском",
            "description": "Description (Russian)" if english else "Описание",
            "description_en": "Description (English)" if english else "Описание на английском",
            "image": "Category photo" if english else "Фото категории",
            "image_url": "Photo URL (optional)" if english else "Ссылка на фото (необязательно)",
            "display_order": "Display order" if english else "Порядок отображения",
            "is_active": "Published" if english else "Опубликована",
        }
        for field_name, label in labels.items():
            self.fields[field_name].label = label
        self.fields["image"].widget.attrs["accept"] = "image/jpeg,image/png,image/webp"


class ProductFilterOptionEditorForm(forms.ModelForm):
    class Meta:
        model = ProductFilterOption
        fields = (
            "filter_type",
            "value",
            "label",
            "label_en",
            "display_order",
            "is_active",
        )
        widgets = {
            "filter_type": forms.Select(
                attrs={"class": "site-content-form-control"}
            ),
            "value": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "label": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "label_en": forms.TextInput(attrs={"class": "site-content-form-control"}),
            "display_order": forms.NumberInput(
                attrs={"class": "site-content-form-control", "min": 0}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "site-content-form-checkbox"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        english = get_language() == "en"
        labels = {
            "filter_type": "Filter type" if english else "Тип фильтра",
            "value": "Code" if english else "Код",
            "label": "Name (Russian)" if english else "Название",
            "label_en": "Name (English)" if english else "Название на английском",
            "display_order": "Display order" if english else "Порядок отображения",
            "is_active": "Published" if english else "Опубликовано",
        }
        for field_name, label in labels.items():
            self.fields[field_name].label = label


class CatalogFilterForm(forms.Form):
    query = forms.CharField(required=False, max_length=100)
    search_mode = forms.ChoiceField(
        required=False,
        choices=(("all", "Везде"), ("name", "По названию")),
        initial="all",
    )
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.none(),
        required=False,
    )
    sizes = forms.MultipleChoiceField(required=False)
    coatings = forms.MultipleChoiceField(required=False)
    doughs = forms.MultipleChoiceField(required=False)
    colors = forms.MultipleChoiceField(required=False)
    occasions = forms.MultipleChoiceField(required=False)
    packaging = forms.MultipleChoiceField(required=False)
    min_price = forms.DecimalField(required=False, min_value=0)
    max_price = forms.DecimalField(required=False, min_value=0)
    sort = forms.ChoiceField(
        required=False,
        choices=(
            ("popular", "По популярности"),
            ("price_asc", "Сначала недорогие"),
            ("price_desc", "Сначала дорогие"),
            ("name", "По названию"),
        ),
        initial="popular",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categories"].queryset = Category.objects.filter(is_active=True)
        options = ProductFilterOption.objects.filter(is_active=True)
        for field_name, filter_type in (
            ("sizes", ProductFilterOption.FilterType.SIZE),
            ("coatings", ProductFilterOption.FilterType.COATING),
            ("doughs", ProductFilterOption.FilterType.DOUGH),
            ("colors", ProductFilterOption.FilterType.COLOR),
            ("occasions", ProductFilterOption.FilterType.OCCASION),
            ("packaging", ProductFilterOption.FilterType.PACKAGING),
        ):
            self.fields[field_name].choices = tuple(
                (option.value, option.localized_label)
                for option in options.filter(filter_type=filter_type)
            )
        if get_language() == "en":
            self.fields["search_mode"].choices = (
                ("all", "Everywhere"),
                ("name", "By name"),
            )
            self.fields["sort"].choices = (
                ("popular", "Most popular"),
                ("price_asc", "Price: low to high"),
                ("price_desc", "Price: high to low"),
                ("name", "Name"),
            )

    def clean(self):
        cleaned_data = super().clean()
        min_price = cleaned_data.get("min_price")
        max_price = cleaned_data.get("max_price")
        if min_price is not None and max_price is not None and min_price > max_price:
            message = (
                "The upper limit must be greater than or equal to the lower limit."
                if get_language() == "en"
                else "Укажите верхнюю границу не меньше нижней."
            )
            self.add_error("max_price", message)
        return cleaned_data
