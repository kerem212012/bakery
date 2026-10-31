from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path("admin-panel/", views.admin_dashboard, name="admin_dashboard"),
    path("manager/", views.manager_dashboard, name="manager_dashboard"),
    path(
        "manager/orders/<int:order_id>/status/",
        views.manager_update_order_status,
        name="manager_update_order_status",
    ),
    path("about/", views.about, name="about"),
    path("corporate/", views.corporate, name="corporate"),
    path("contacts/", views.contacts, name="contacts"),
    path("delivery/", views.delivery, name="delivery"),
    path("faq/", views.faq, name="faq"),
    path("feedback/", views.feedback, name="feedback"),
    path("packaging/", views.packaging, name="packaging"),
    path("preorder/", views.home, name="preorder"),
]
