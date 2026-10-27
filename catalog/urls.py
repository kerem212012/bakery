from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.category_list, name="category_list"),
    path("favorites/toggle/<int:product_id>/", views.toggle_favorite, name="toggle_favorite"),
    path("<str:category_slug>/<str:product_slug>/", views.product_detail, name="product_detail"),
    path("<str:slug>/", views.category_detail, name="category_detail"),
]
