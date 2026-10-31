from django.contrib import admin

from .models import Category, Product, ProductFilterOption


admin.site.site_header = "Лукоморье — управление сайтом"
admin.site.site_title = "Управление сайтом"
admin.site.index_title = "Управление каталогом и заказами"


class ProductInline(admin.TabularInline):
    model = Product
    fields = (
        "name",
        "name_en",
        "price",
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
    list_display = ("name", "name_en", "slug", "display_order", "is_active")
    list_editable = ("display_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "name_en", "description", "description_en", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = (ProductInline,)
    ordering = ("display_order", "name")
    list_per_page = 25


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "name_en",
        "category",
        "price",
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


@admin.register(ProductFilterOption)
class ProductFilterOptionAdmin(admin.ModelAdmin):
    list_display = ("label", "label_en", "filter_type", "value", "display_order", "is_active")
    list_editable = ("display_order", "is_active")
    list_filter = ("filter_type", "is_active")
    search_fields = ("label", "label_en", "value")
    list_per_page = 50
    fieldsets = (
        (
            "Параметр каталога",
            {"fields": (("filter_type", "value"), ("label", "label_en"))},
        ),
        ("Отображение", {"fields": (("is_active", "display_order"),)}),
    )
