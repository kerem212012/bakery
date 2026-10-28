from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path("about/", views.about, name="about"),
    path("corporate/", views.corporate, name="corporate"),
    path("delivery/", views.delivery, name="delivery"),
    path("packaging/", views.packaging, name="packaging"),
    path("preorder/", views.home, name="preorder"),
]
