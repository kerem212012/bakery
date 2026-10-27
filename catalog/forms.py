from django import forms

from .models import Category


class CatalogFilterForm(forms.Form):
    query = forms.CharField(required=False, max_length=100)
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.none(),
        required=False,
    )
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

    def clean(self):
        cleaned_data = super().clean()
        min_price = cleaned_data.get("min_price")
        max_price = cleaned_data.get("max_price")
        if min_price is not None and max_price is not None and min_price > max_price:
            self.add_error("max_price", "Укажите верхнюю границу не меньше нижней.")
        return cleaned_data
