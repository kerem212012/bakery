from .models import (
    HomeHeroSlide,
    SiteContentBlock,
    SitePageContent,
    SitePageSection,
)


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
        return {
            "site_content_blocks": (),
            "site_page_content": None,
            "site_home_hero_slides": (),
            "site_home_hero_configured": False,
            "site_page_sections": {},
            "site_footer_contacts": (),
        }

    page = PAGE_BY_VIEW_NAME.get(match.view_name)
    pages = (
        (SiteContentBlock.Page.ALL, page)
        if page is not None
        else (SiteContentBlock.Page.ALL,)
    )
    page_sections = {}
    if page in SitePageSection.Page.values:
        for section in SitePageSection.objects.filter(
            page=page,
            is_active=True,
        ):
            page_sections.setdefault(section.group, []).append(section)
    return {
        "site_content_blocks": SiteContentBlock.objects.filter(
            is_active=True,
            page__in=pages,
        ),
        "site_page_content": (
            SitePageContent.objects.filter(page=page).first()
            if page in SitePageContent.Page.values
            else None
        ),
        "site_home_hero_slides": (
            HomeHeroSlide.objects.filter(is_active=True)
            if page == SiteContentBlock.Page.HOME
            else ()
        ),
        "site_home_hero_configured": (
            HomeHeroSlide.objects.exists()
            if page == SiteContentBlock.Page.HOME
            else False
        ),
        "site_page_sections": page_sections,
        "site_footer_contacts": SitePageSection.objects.filter(
            page=SitePageSection.Page.CONTACTS,
            group="details",
            is_active=True,
        ).order_by("display_order", "pk"),
    }
