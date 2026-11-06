from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP

from django.utils.translation import get_language


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

DEFAULT_CALCULATOR_PRICING = {
    "base_unit_price": "98",
    "size_multipliers": {key: str(value) for key, value in SIZE_MULTIPLIERS.items()},
    "flavor_additions": {key: str(value) for key, value in FLAVOR_ADDITIONS.items()},
    "coating_additions": {key: str(value) for key, value in COATING_ADDITIONS.items()},
    "packaging_additions": {key: str(value) for key, value in PACKAGING_ADDITIONS.items()},
    "delivery_costs": {key: str(value) for key, value in DELIVERY_COSTS.items()},
    "discount_tiers": [list(tier) for tier in DISCOUNT_TIERS],
    "lead_time_days": LEAD_TIME_DAYS,
}


def default_calculator_pricing():
    return deepcopy(DEFAULT_CALCULATOR_PRICING)


def normalize_calculator_pricing(pricing=None):
    source = pricing or DEFAULT_CALCULATOR_PRICING
    result = {
        "base_unit_price": Decimal(str(source.get("base_unit_price", BASE_UNIT_PRICE))),
        "lead_time_days": int(source.get("lead_time_days", LEAD_TIME_DAYS)),
    }
    for key, defaults in (
        ("size_multipliers", SIZE_MULTIPLIERS),
        ("flavor_additions", FLAVOR_ADDITIONS),
        ("coating_additions", COATING_ADDITIONS),
        ("packaging_additions", PACKAGING_ADDITIONS),
        ("delivery_costs", DELIVERY_COSTS),
    ):
        values = source.get(key, {})
        result[key] = {
            option: Decimal(str(values.get(option, default)))
            for option, default in defaults.items()
        }
    tiers = source.get("discount_tiers", DISCOUNT_TIERS)
    result["discount_tiers"] = tuple(
        sorted(
            ((int(threshold), int(discount)) for threshold, discount in tiers),
            reverse=True,
        )
    )
    return result

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
    ("organization_half", "От организации, 50% предоплата"),
    ("card", "Картой по ссылке, 100% предоплата"),
    ("card_half", "Картой по ссылке, 50% предоплата"),
    ("card_delivery", "Картой по ссылке при получении (только для заказов менее 5000 ₽)"),
    ("invoice", "Оплата по счёту"),
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

ENGLISH_CHOICES = {
    "flavor": {
        "classic": "Classic gingerbread",
        "chocolate": "Chocolate",
        "honey": "Honey",
        "cinnamon": "Cinnamon",
    },
    "shape": {
        "heart": "Heart",
        "circle": "Circle",
        "star": "Star",
        "square": "Square",
        "flower": "Flower",
        "gingerbread": "Gingerbread person",
    },
    "coating": {
        "icing": "Printed icing",
        "painting": "Hand-painted icing",
        "partial": "Partial coating",
        "none": "No coating",
    },
    "packaging": {
        "ribbon": "Bag with ribbon",
        "box": "Classic box",
        "premium": "Premium box",
        "none": "No packaging",
    },
    "delivery": {
        "moscow": "Delivery within the Moscow Ring Road",
        "outside": "Delivery outside the Moscow Ring Road",
        "pickup": "Pickup",
    },
    "payment": {
        "organization": "Business payment, 100% prepayment",
        "organization_half": "Business payment, 50% prepayment",
        "card": "Card via payment link, 100% prepayment",
        "card_half": "Card via payment link, 50% prepayment",
        "card_delivery": "Card via payment link on delivery (orders under RUB 5,000 only)",
        "invoice": "Invoice",
    },
}


def localized_calculator_options(pricing=None):
    pricing = normalize_calculator_pricing(pricing)
    options = {
        "flavors": tuple(
            {"value": value, "label": label, "extra": pricing["flavor_additions"][value]}
            for value, label in FLAVOR_CHOICES
        ),
        "sizes": tuple(
            {"value": value, "label": label, "multiplier": pricing["size_multipliers"][value]}
            for value, label in SIZE_CHOICES
        ),
        "shapes": tuple({"value": value, "label": label} for value, label in SHAPE_CHOICES),
        "coatings": tuple(
            {"value": value, "label": label, "extra": pricing["coating_additions"][value]}
            for value, label in COATING_CHOICES
        ),
        "packaging": tuple(
            {"value": value, "label": label, "extra": pricing["packaging_additions"][value]}
            for value, label in PACKAGING_CHOICES
        ),
        "deliveries": tuple(
            {"value": value, "label": label, "cost": pricing["delivery_costs"][value]}
            for value, label in DELIVERY_CHOICES
        ),
        "payments": tuple({"value": value, "label": label} for value, label in PAYMENT_CHOICES),
    }
    if get_language() != "en":
        return options

    choice_groups = {
        "flavors": "flavor",
        "shapes": "shape",
        "coatings": "coating",
        "packaging": "packaging",
        "deliveries": "delivery",
        "payments": "payment",
    }
    return {
        group: tuple(
            {
                **option,
                "label": ENGLISH_CHOICES[choice_groups[group]][option["value"]],
            }
            if group in choice_groups
            else option
            for option in options[group]
        )
        for group in options
    }


def localized_choices(choices, group):
    translations = ENGLISH_CHOICES.get(group, {})
    if get_language() != "en":
        return choices
    return tuple((value, translations.get(value, label)) for value, label in choices)


def calculate_quote(configuration, pricing=None):
    pricing = normalize_calculator_pricing(pricing)
    quantity = int(configuration["quantity"])
    unit_price = (
        pricing["base_unit_price"] * pricing["size_multipliers"][configuration["size"]]
        + pricing["flavor_additions"][configuration["flavor"]]
        + pricing["coating_additions"][configuration["coating"]]
        + pricing["packaging_additions"][configuration["packaging"]]
    ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    discount_percent = next(
        (
            discount
            for threshold, discount in pricing["discount_tiers"]
            if quantity >= threshold
        ),
        0,
    )
    delivery_cost = pricing["delivery_costs"][configuration["delivery"]]
    total_price = (
        unit_price * quantity * (Decimal("100") - discount_percent) / Decimal("100")
        + delivery_cost
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {
        "unit_price": unit_price,
        "discount_percent": discount_percent,
        "delivery_cost": delivery_cost,
        "lead_time_days": pricing["lead_time_days"],
        "total_price": total_price,
    }
