from django.contrib import admin

from .models import Category, Product, ProductFilterOption


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "display_order", "is_active")
    list_editable = ("display_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "description", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_featured", "is_active", "display_order")
    list_editable = ("is_featured", "is_active", "display_order")
    list_filter = ("category", "is_featured", "is_active")
    search_fields = ("name", "description", "slug", "category__name")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("category",)
    filter_horizontal = ("filter_options",)


@admin.register(ProductFilterOption)
class ProductFilterOptionAdmin(admin.ModelAdmin):
    list_display = ("label", "filter_type", "value", "display_order", "is_active")
    list_editable = ("display_order", "is_active")
    list_filter = ("filter_type", "is_active")
    search_fields = ("label", "value")
