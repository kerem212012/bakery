from .models import SiteContentBlock


PAGE_BY_VIEW_NAME = {
    "home": SiteContentBlock.Page.HOME,
    "preorder": SiteContentBlock.Page.HOME,
    "about": SiteContentBlock.Page.ABOUT,
    "business_clients": SiteContentBlock.Page.BUSINESS_CLIENTS,
    "corporate": SiteContentBlock.Page.PARTNERSHIP,
    "contacts": SiteContentBlock.Page.CONTACTS,
    "delivery": SiteContentBlock.Page.DELIVERY,
    "faq": SiteContentBlock.Page.FAQ,
    "feedback": SiteContentBlock.Page.FEEDBACK,
    "packaging": SiteContentBlock.Page.PACKAGING,
    "catalog:category_list": SiteContentBlock.Page.CATALOG,
    "catalog:categories": SiteContentBlock.Page.CATEGORIES,
    "catalog:category_detail": SiteContentBlock.Page.CATEGORY,
    "catalog:product_detail": SiteContentBlock.Page.PRODUCT,
}

PRIVATE_VIEW_NAMES = {
    "admin_dashboard",
    "site_content_manager",
    "site_content_edit",
    "manager_dashboard",
    "manager_update_order_status",
}


def site_content_blocks(request):
    match = getattr(request, "resolver_match", None)
    if not match or match.view_name in PRIVATE_VIEW_NAMES:
        return {"site_content_blocks": ()}

    page = PAGE_BY_VIEW_NAME.get(match.view_name)
    pages = (
        (SiteContentBlock.Page.ALL, page)
        if page is not None
        else (SiteContentBlock.Page.ALL,)
    )
    return {
        "site_content_blocks": SiteContentBlock.objects.filter(
            is_active=True,
            page__in=pages,
        )
    }
