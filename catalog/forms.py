from django import forms
from django.utils.translation import get_language

from .models import Category, ProductFilterOption


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
