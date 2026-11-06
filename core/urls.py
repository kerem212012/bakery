from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path("admin-panel/", views.admin_dashboard, name="admin_dashboard"),
    path(
        "admin-panel/calculator/",
        views.calculator_settings,
        name="calculator_settings",
    ),
    path(
        "admin-panel/site-content/",
        views.site_content_manager,
        name="site_content_manager",
    ),
    path(
        "admin-panel/site-content/<int:block_id>/",
        views.site_content_manager,
        name="site_content_edit",
    ),
    path(
        "admin-panel/section/<slug:section>/",
        views.admin_section,
        name="admin_section",
    ),
    path(
        "admin-panel/section/<slug:section>/new/",
        views.admin_section,
        {"new": True},
        name="admin_section_new",
    ),
    path(
        "admin-panel/section/<slug:section>/<int:object_id>/",
        views.admin_section,
        name="admin_section_edit",
    ),
    path(
        "admin-panel/section/<slug:section>/<int:object_id>/delete/",
        views.admin_section_delete,
        name="admin_section_delete",
    ),
    path(
        "admin-panel/section/<slug:section>/<int:object_id>/<slug:action>/",
        views.admin_section_visibility,
        name="admin_section_visibility",
    ),
    path("manager/", views.manager_dashboard, name="manager_dashboard"),
    path(
        "manager/orders/<int:order_id>/status/",
        views.manager_update_order_status,
        name="manager_update_order_status",
    ),
    path("about/", views.about, name="about"),
    path("corporate/", views.corporate, name="corporate"),
    path("business-clients/", views.business_clients, name="business_clients"),
    path("contacts/", views.contacts, name="contacts"),
    path("delivery/", views.delivery, name="delivery"),
    path("faq/", views.faq, name="faq"),
    path("feedback/", views.feedback, name="feedback"),
    path("packaging/", views.packaging, name="packaging"),
    path("preorder/", views.home, name="preorder"),
]
