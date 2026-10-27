from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.category_list, name="category_list"),
    path("categories/", views.category_overview, name="categories"),
    path("cart/", views.cart, name="cart"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<str:item_id>/", views.update_cart_item, name="update_cart_item"),
    path("cart/remove/<str:item_id>/", views.remove_cart_item, name="remove_cart_item"),
    path("cart/clear/", views.clear_cart, name="clear_cart"),
    path("favorites/toggle/<int:product_id>/", views.toggle_favorite, name="toggle_favorite"),
    path("<str:category_slug>/<str:product_slug>/", views.product_detail, name="product_detail"),
    path("<str:slug>/", views.category_detail, name="category_detail"),
]
