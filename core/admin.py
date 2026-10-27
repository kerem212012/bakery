from django.contrib import admin

from .models import Preorder, PreorderAttachment


class PreorderAttachmentInline(admin.TabularInline):
    model = PreorderAttachment
    extra = 0
    readonly_fields = ("uploaded_at",)


@admin.register(Preorder)
class PreorderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "email",
        "phone",
        "total_price",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("name", "email", "phone")
    readonly_fields = (
        "configuration",
        "unit_price",
        "discount_percent",
        "delivery_cost",
        "total_price",
        "created_at",
    )
    inlines = (PreorderAttachmentInline,)
