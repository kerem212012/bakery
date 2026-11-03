from django.contrib import admin

from .models import (
    FeedbackSubmission,
    HomeHeroSlide,
    Preorder,
    PreorderAttachment,
    SiteContentBlock,
    SitePageContent,
)


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


@admin.register(SitePageContent)
class SitePageContentAdmin(admin.ModelAdmin):
    list_display = ("page", "title", "title_en", "updated_at")
    list_filter = ("page",)
    search_fields = ("title", "title_en", "subtitle", "subtitle_en")
    readonly_fields = ("updated_at",)


@admin.register(HomeHeroSlide)
class HomeHeroSlideAdmin(admin.ModelAdmin):
    list_display = ("title", "title_en", "display_order", "is_active")
    list_editable = ("display_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("eyebrow", "eyebrow_en", "title", "title_en")


@admin.register(SiteContentBlock)
class SiteContentBlockAdmin(admin.ModelAdmin):
    list_display = ("title", "page", "display_order", "is_active")
    list_editable = ("display_order", "is_active")
    list_filter = ("page", "is_active")
    search_fields = ("title", "title_en", "description", "description_en")
