from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Product, ProductFilterOption


admin.site.site_header = "Вкусно Да Сладко — управление сайтом"
admin.site.site_title = "Управление сайтом"
admin.site.index_title = "Управление каталогом и заказами"


class ProductInline(admin.TabularInline):
    model = Product
    fields = (
        "name",
        "name_en",
        "price",
        "image",
        "is_active",
        "is_featured",
        "display_order",
    )
    extra = 0
    show_change_link = True


@admin.action(description="Опубликовать выбранные товары")
def activate_products(modeladmin, request, queryset):
    queryset.update(is_active=True)


@admin.action(description="Снять выбранные товары с публикации")
def deactivate_products(modeladmin, request, queryset):
    queryset.update(is_active=False)


@admin.action(description="Добавить выбранные товары в популярные")
def feature_products(modeladmin, request, queryset):
    queryset.update(is_featured=True)


@admin.action(description="Убрать выбранные товары из популярных")
def unfeature_products(modeladmin, request, queryset):
    queryset.update(is_featured=False)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "name_en", "image_preview", "slug", "display_order", "is_active")
    list_editable = ("display_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "name_en", "description", "description_en", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = (ProductInline,)
    readonly_fields = ("image_preview",)
    ordering = ("display_order", "name")
    list_per_page = 25
    fieldsets = (
        (
            "Основная информация",
            {
                "fields": (
                    ("name", "name_en"),
                    "slug",
                    ("description", "description_en"),
                    "image",
                    "image_preview",
                    "image_url",
                )
            },
        ),
        ("Публикация", {"fields": (("display_order", "is_active"),)}),
    )

    @admin.display(description="Фото")
    def image_preview(self, obj):
        if not obj or not obj.display_image_url:
            return "Фото не загружено"
        return format_html(
            '<img src="{}" alt="" style="max-width: 120px; max-height: 90px; object-fit: cover;">',
            obj.display_image_url,
        )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "name_en",
        "category",
        "price",
        "image_preview",
        "is_featured",
        "is_active",
        "display_order",
    )
    list_editable = ("is_featured", "is_active", "display_order")
    list_filter = ("category", "is_featured", "is_active")
    list_select_related = ("category",)
    search_fields = (
        "name",
        "name_en",
        "description",
        "description_en",
        "slug",
        "category__name",
        "category__name_en",
    )
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("category",)
    filter_horizontal = ("filter_options",)
    list_per_page = 50
    save_on_top = True
    readonly_fields = ("image_preview",)
    actions = (
        activate_products,
        deactivate_products,
        feature_products,
        unfeature_products,
    )
    fieldsets = (
        (
            "Основная информация",
            {
                "fields": (
                    ("name", "name_en"),
                    "slug",
                    "category",
                    "description",
                    "description_en",
                    "price",
                    "image",
                    "image_preview",
                    "image_url",
                )
            },
        ),
        (
            "Каталог и публикация",
            {
                "fields": (
                    "filter_options",
                    ("is_active", "is_featured"),
                    "display_order",
                )
            },
        ),
    )

    @admin.display(description="Фото")
    def image_preview(self, obj):
        if not obj or not obj.display_image_url:
            return "Фото не загружено"
        return format_html(
            '<img src="{}" alt="" style="max-width: 160px; max-height: 120px; object-fit: cover;">',
            obj.display_image_url,
        )


@admin.register(ProductFilterOption)
class ProductFilterOptionAdmin(admin.ModelAdmin):
    list_display = (
        "label",
        "label_en",
        "filter_type",
        "value",
        "display_order",
        "is_active",
    )
    list_editable = ("display_order", "is_active")
    list_filter = ("filter_type", "is_active")
    search_fields = (
        "label",
        "label_en",
        "description",
        "description_en",
        "value",
    )
    list_per_page = 50
    def get_fieldsets(self, request, obj=None):
        fields = [
            ("filter_type", "value"),
            ("label", "label_en"),
        ]
        if obj is None or obj.filter_type in {
            ProductFilterOption.FilterType.COATING,
            ProductFilterOption.FilterType.DOUGH,
        }:
            fields.append(("description", "description_en"))
        return (
            ("Параметр каталога", {"fields": tuple(fields)}),
            ("Отображение", {"fields": (("is_active", "display_order"),)}),
        )
