def get_favorite_ids(request):
    favorite_ids = request.session.get("favorite_product_ids", [])
    if not isinstance(favorite_ids, list):
        return set()
    return {product_id for product_id in favorite_ids if isinstance(product_id, int)}
