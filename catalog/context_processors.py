def cart_item_count(request):
    cart = request.session.get("cart", {})
    if not isinstance(cart, dict):
        return {"cart_item_count": 0}

    total = 0
    for item in cart.values():
        if isinstance(item, dict):
            try:
                total += max(0, int(item.get("quantity", 0)))
            except (TypeError, ValueError):
                continue
    return {"cart_item_count": total}
