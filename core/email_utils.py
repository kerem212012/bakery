from django.conf import settings
from django.core.mail import send_mail


def send_order_confirmation_email(preorder, language_code=None):
    language_code = language_code or "ru"
    configuration = preorder.configuration if isinstance(preorder.configuration, dict) else {}
    items = configuration.get("items")
    item_lines = []
    if isinstance(items, list):
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("product_name") or f"Item {index}"
            quantity = item.get("quantity", 1)
            item_lines.append(f"- {name} × {quantity}")
    if not item_lines:
        item_lines.append(f"- {configuration.get('product_name', 'Custom order')}")

    order_summary = "\n".join(item_lines)
    if language_code.startswith("en"):
        subject = f"Order #{preorder.pk} received"
        message = (
            f"Hello {preorder.name},\n\n"
            f"We have received your order #{preorder.pk}.\n\n"
            f"Order details:\n{order_summary}\n\n"
            f"Phone: {preorder.phone}\n"
            f"Delivery date: {preorder.delivery_date or 'To be confirmed'}\n"
            f"Address: {preorder.address or 'Not specified'}\n"
            f"Total: {preorder.total_price} \n\n"
            "We will contact you shortly to confirm the details."
        )
    else:
        subject = f"Заказ №{preorder.pk} принят"
        message = (
            f"Здравствуйте, {preorder.name}!\n\n"
            f"Мы получили ваш заказ №{preorder.pk}.\n\n"
            f"Состав заказа:\n{order_summary}\n\n"
            f"Телефон: {preorder.phone}\n"
            f"Дата доставки: {preorder.delivery_date or 'Уточняется'}\n"
            f"Адрес: {preorder.address or 'Не указан'}\n"
            f"Итого: {preorder.total_price} \n\n"
            "Мы скоро свяжемся с вами для подтверждения деталей."
        )

    recipients = [preorder.email]
    admin_email = getattr(settings, "ORDER_NOTIFICATION_EMAIL", None) or settings.DEFAULT_FROM_EMAIL
    if admin_email and admin_email not in recipients:
        recipients.append(admin_email)

    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=True)
