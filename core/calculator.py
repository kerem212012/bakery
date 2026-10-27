from decimal import Decimal, ROUND_HALF_UP


BASE_UNIT_PRICE = Decimal("98")
SIZE_MULTIPLIERS = {
    "3": Decimal("0.55"),
    "5": Decimal("1"),
    "7": Decimal("1.4"),
    "10": Decimal("1.9"),
    "12": Decimal("2.4"),
    "15": Decimal("3"),
}
FLAVOR_ADDITIONS = {
    "classic": Decimal("0"),
    "chocolate": Decimal("15"),
    "honey": Decimal("10"),
    "cinnamon": Decimal("8"),
}
COATING_ADDITIONS = {
    "icing": Decimal("0"),
    "painting": Decimal("15"),
    "partial": Decimal("8"),
    "none": Decimal("-15"),
}
PACKAGING_ADDITIONS = {
    "ribbon": Decimal("0"),
    "box": Decimal("35"),
    "premium": Decimal("80"),
    "none": Decimal("-15"),
}
DELIVERY_COSTS = {
    "moscow": Decimal("700"),
    "outside": Decimal("1200"),
    "pickup": Decimal("0"),
}
DISCOUNT_TIERS = ((100, 20), (50, 15), (20, 10))
LEAD_TIME_DAYS = 3

FLAVOR_CHOICES = (
    ("classic", "Имбирный пряник (классика)"),
    ("chocolate", "Шоколадный"),
    ("honey", "Медовый"),
    ("cinnamon", "С корицей"),
)
SIZE_CHOICES = tuple((str(size), str(size)) for size in (3, 5, 7, 10, 12, 15))
SHAPE_CHOICES = (
    ("heart", "Сердце"),
    ("circle", "Круг"),
    ("star", "Звезда"),
    ("square", "Квадрат"),
    ("flower", "Цветок"),
    ("gingerbread", "Пряник"),
)
COATING_CHOICES = (
    ("icing", "Пищевая печать на глазури"),
    ("painting", "Роспись на айсинге"),
    ("partial", "Частичное покрытие"),
    ("none", "Без покрытия"),
)
PACKAGING_CHOICES = (
    ("ribbon", "Пакет с лентой"),
    ("box", "Коробка классическая"),
    ("premium", "Премиальная коробка"),
    ("none", "Без упаковки"),
)
DELIVERY_CHOICES = (
    ("moscow", "Доставка по Москве (в пределах МКАД)"),
    ("outside", "Доставка за пределы МКАД"),
    ("pickup", "Самовывоз"),
)
PAYMENT_CHOICES = (
    ("organization", "От организации, 100% предоплата"),
    ("invoice", "Оплата по счёту"),
    ("card", "Банковской картой"),
)

CALCULATOR_OPTIONS = {
    "flavors": tuple(
        {"value": value, "label": label, "extra": FLAVOR_ADDITIONS[value]}
        for value, label in FLAVOR_CHOICES
    ),
    "sizes": tuple(
        {"value": value, "label": label, "multiplier": SIZE_MULTIPLIERS[value]}
        for value, label in SIZE_CHOICES
    ),
    "shapes": tuple({"value": value, "label": label} for value, label in SHAPE_CHOICES),
    "coatings": tuple(
        {"value": value, "label": label, "extra": COATING_ADDITIONS[value]}
        for value, label in COATING_CHOICES
    ),
    "packaging": tuple(
        {"value": value, "label": label, "extra": PACKAGING_ADDITIONS[value]}
        for value, label in PACKAGING_CHOICES
    ),
    "deliveries": tuple(
        {"value": value, "label": label, "cost": DELIVERY_COSTS[value]}
        for value, label in DELIVERY_CHOICES
    ),
    "payments": tuple({"value": value, "label": label} for value, label in PAYMENT_CHOICES),
}


def calculate_quote(configuration):
    quantity = int(configuration["quantity"])
    unit_price = (
        BASE_UNIT_PRICE * SIZE_MULTIPLIERS[configuration["size"]]
        + FLAVOR_ADDITIONS[configuration["flavor"]]
        + COATING_ADDITIONS[configuration["coating"]]
        + PACKAGING_ADDITIONS[configuration["packaging"]]
    ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    discount_percent = next(
        (discount for threshold, discount in DISCOUNT_TIERS if quantity >= threshold),
        0,
    )
    delivery_cost = DELIVERY_COSTS[configuration["delivery"]]
    total_price = (
        unit_price * quantity * (Decimal("100") - discount_percent) / Decimal("100")
        + delivery_cost
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {
        "unit_price": unit_price,
        "discount_percent": discount_percent,
        "delivery_cost": delivery_cost,
        "lead_time_days": LEAD_TIME_DAYS,
        "total_price": total_price,
    }
