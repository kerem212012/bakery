from django.contrib import admin

from .models import FeedbackSubmission, Preorder, PreorderAttachment


class PreorderAttachmentInline(admin.TabularInline):
    model = PreorderAttachment
    extra = 0
    readonly_fields = ("uploaded_at",)


@admin.register(Preorder)
class PreorderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "name",
        "email",
        "phone",
        "total_price",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("name", "email", "phone", "user__username")
    date_hierarchy = "created_at"
    list_select_related = ("user",)
    list_per_page = 50
    save_on_top = True
    readonly_fields = (
        "configuration",
        "unit_price",
        "discount_percent",
        "delivery_cost",
        "total_price",
        "created_at",
    )
    inlines = (PreorderAttachmentInline,)


@admin.register(FeedbackSubmission)
class FeedbackSubmissionAdmin(admin.ModelAdmin):
    list_display = ("subject", "name", "email", "status", "created_at")
    list_filter = ("status", "created_at")
    list_editable = ("status",)
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = ("name", "email", "subject", "message", "consent_given", "created_at")
