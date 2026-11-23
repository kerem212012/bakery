from copy import deepcopy
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.utils.text import slugify
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
MODIFIER_GROUP_LABELS = {
    "flavors": ("Вкус", "Flavor"),
    "shapes": ("Форма", "Shape"),
    "coatings": ("Покрытие", "Coating"),
    "packaging": ("Упаковка", "Packaging"),
}

DEFAULT_CALCULATOR_PRICING = {
    "base_unit_price": "98",
    "products": [
        {
            "value": "gingerbread",
            "label": "Пряник",
            "label_en": "Gingerbread",
            "base_unit_price": "98",
        }
    ],
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


def is_coating_modifier_group(group):
    return (
        str(group.get("value", "")).strip().casefold() in {"coating", "coatings"}
        or str(group.get("label", "")).strip().casefold() == "покрытие"
        or str(group.get("label_en", "")).strip().casefold() == "coating"
    )


def normalize_calculator_pricing(pricing=None):
    source = pricing or DEFAULT_CALCULATOR_PRICING
    base_unit_price = Decimal(str(source.get("base_unit_price", BASE_UNIT_PRICE)))
    raw_products = source.get("products") or [
        {
            **DEFAULT_CALCULATOR_PRICING["products"][0],
            "base_unit_price": str(base_unit_price),
        }
    ]
    products = []
    product_sources = []
    seen_values = set()
    for index, product in enumerate(raw_products):
        if not isinstance(product, dict):
            continue
        label = str(product.get("label", "")).strip()
        if not label:
            continue
        value = str(product.get("value") or slugify(label, allow_unicode=True))
        if not value:
            value = f"product-{index + 1}"
        if value in seen_values:
            continue
        seen_values.add(value)
        products.append(
            {
                "value": value,
                "label": label,
                "label_en": str(product.get("label_en", "")).strip(),
                "base_unit_price": Decimal(
                    str(product.get("base_unit_price", base_unit_price))
                ),
                "sizes": [],
                "modifier_groups": [],
                "lead_time_rules": [],
            }
        )
        product_sources.append(product)
    if not products:
        products = [
            {
                "value": "gingerbread",
                "label": "Пряник",
                "label_en": "Gingerbread",
                "base_unit_price": base_unit_price,
                "sizes": [],
                "modifier_groups": [],
                "lead_time_rules": [],
            }
        ]
        product_sources = [{}]
    result = {
        "base_unit_price": base_unit_price,
        "products": products,
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
    option_catalog = source.get("option_catalog")
    default_catalog = _default_calculator_option_catalog(result)
    if not isinstance(option_catalog, dict):
        option_catalog = {}
    result["option_catalog"] = {}
    for group, defaults in default_catalog.items():
        raw_options = option_catalog.get(group, defaults)
        if not isinstance(raw_options, list):
            raw_options = defaults
        normalized_options = []
        seen_values = set()
        for option in raw_options:
            if not isinstance(option, dict):
                continue
            value = str(option.get("value", "")).strip()
            label = str(option.get("label", "")).strip()
            label_en = str(option.get("label_en", "")).strip()
            if not value or value in seen_values or not (label or label_en):
                continue
            seen_values.add(value)
            normalized_options.append(
                {
                    "value": value,
                    "label": label or label_en,
                    "label_en": label_en or label,
                    "extra": Decimal(str(option.get("extra", 0))),
                    "active": bool(option.get("active", True)),
                }
            )
        result["option_catalog"][group] = normalized_options
    for group, pricing_key in (
        ("flavors", "flavor_additions"),
        ("coatings", "coating_additions"),
        ("packaging", "packaging_additions"),
    ):
        for option in result["option_catalog"][group]:
            result[pricing_key][option["value"]] = option["extra"]
    for product, source_product in zip(products, product_sources):
        raw_sizes = source_product.get("sizes")
        if not isinstance(raw_sizes, list) or not raw_sizes:
            raw_sizes = [
                {
                    "value": value,
                    "label": f"{value} cm",
                    "base_price": product["base_unit_price"] * multiplier,
                }
                for value, multiplier in result["size_multipliers"].items()
            ]
        seen_sizes = set()
        for size in raw_sizes:
            if not isinstance(size, dict):
                continue
            value = str(size.get("value", "")).strip()
            label = str(size.get("label", "")).strip() or f"{value} cm"
            if not value or value in seen_sizes:
                continue
            try:
                price = Decimal(str(size.get("base_price", 0)))
            except (InvalidOperation, TypeError, ValueError):
                continue
            if price < 0:
                continue
            seen_sizes.add(value)
            product["sizes"].append(
                {"value": value, "label": label, "base_price": price}
            )

        raw_groups = source_product.get("modifier_groups")
        if not isinstance(raw_groups, list) or not raw_groups:
            raw_groups = [
                {
                    "value": group,
                    "label": MODIFIER_GROUP_LABELS[group][0],
                    "label_en": MODIFIER_GROUP_LABELS[group][1],
                    "options": [
                        {
                            "value": option["value"],
                            "label": option["label"],
                            "label_en": option["label_en"],
                            "amount": option["extra"],
                            "amount_type": "fixed",
                            "active": option["active"],
                        }
                        for option in result["option_catalog"].get(group, [])
                    ],
                }
                for group in ("flavors", "shapes", "coatings", "packaging")
            ]
        seen_groups = set()
        for group in raw_groups:
            if not isinstance(group, dict):
                continue
            group_value = str(group.get("value", "")).strip()
            label = str(group.get("label", "")).strip()
            label_en = str(group.get("label_en", "")).strip()
            if not group_value or group_value in seen_groups or not (label or label_en):
                continue
            seen_groups.add(group_value)
            options_list = []
            seen_options = set()
            for option in group.get("options", []):
                if not isinstance(option, dict):
                    continue
                option_value = str(option.get("value", "")).strip()
                option_label = str(option.get("label", "")).strip()
                option_label_en = str(option.get("label_en", "")).strip()
                if (
                    not option_value
                    or option_value in seen_options
                    or not (option_label or option_label_en)
                ):
                    continue
                amount_type = (
                    "percent" if option.get("amount_type") == "percent" else "fixed"
                )
                seen_options.add(option_value)
                options_list.append(
                    {
                        "value": option_value,
                        "label": option_label or option_label_en,
                        "label_en": option_label_en or option_label,
                        "amount": Decimal(str(option.get("amount", option.get("extra", 0)))),
                        "amount_type": amount_type,
                        "active": bool(option.get("active", True)),
                    }
                )
            if options_list:
                product["modifier_groups"].append(
                    {
                        "value": group_value,
                        "label": label or label_en,
                        "label_en": label_en or label,
                        "options": options_list,
                    }
                )
        raw_lead_time_rules = source_product.get("lead_time_rules", [])
        if not isinstance(raw_lead_time_rules, list):
            raw_lead_time_rules = []
        for rule in raw_lead_time_rules:
            if not isinstance(rule, dict):
                continue
            try:
                min_quantity = int(rule.get("min_quantity", 0))
                days = int(rule.get("days", 0))
            except (TypeError, ValueError):
                continue
            coating_value = str(rule.get("coating_value", "")).strip()
            if not (1 <= min_quantity <= 10000 and 1 <= days <= 365):
                continue
            if len(coating_value) > 32:
                continue
            product["lead_time_rules"].append(
                {
                    "min_quantity": min_quantity,
                    "coating_value": coating_value,
                    "days": days,
                }
            )
    payment_methods = []
    seen_payments = set()
    for payment in source.get("payment_methods", []):
        if not isinstance(payment, dict):
            continue
        value = str(payment.get("value", "")).strip()
        label = str(payment.get("label", "")).strip()
        label_en = str(payment.get("label_en", "")).strip()
        if value and value not in seen_payments and (label or label_en):
            seen_payments.add(value)
            payment_methods.append(
                {"value": value, "label": label or label_en, "label_en": label_en or label}
            )
    if not payment_methods:
        payment_methods = [
            {"value": value, "label": label, "label_en": ENGLISH_CHOICES["payment"][value]}
            for value, label in PAYMENT_CHOICES
        ]
    tiers = source.get("discount_tiers", DISCOUNT_TIERS)
    result["discount_tiers"] = tuple(
        sorted(
            ((int(threshold), int(discount)) for threshold, discount in tiers),
            reverse=True,
        )
    )
    raw_rules = source.get("discount_rules")
    if not isinstance(raw_rules, list):
        raw_rules = []
    result["payment_methods"] = payment_methods
    result["discount_rules"] = [
        {
            "value": str(rule.get("value", f"discount-{index + 1}")),
            "label": str(rule.get("label", "")).strip(),
            "label_en": str(rule.get("label_en", "")).strip(),
            "trigger": "payment" if rule.get("trigger") == "payment" else "quantity",
            "trigger_value": str(rule.get("trigger_value", "")),
            "amount_type": "fixed" if rule.get("amount_type") == "fixed" else "percent",
            "amount": Decimal(str(rule.get("amount", 0))),
        }
        for index, rule in enumerate(raw_rules)
        if isinstance(rule, dict) and (rule.get("label") or rule.get("label_en"))
    ]
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


def _default_calculator_option_catalog(pricing):
    return {
        "flavors": [
            {
                "value": value,
                "label": label,
                "label_en": ENGLISH_CHOICES["flavor"][value],
                "extra": pricing["flavor_additions"][value],
                "active": True,
            }
            for value, label in FLAVOR_CHOICES
        ],
        "shapes": [
            {
                "value": value,
                "label": label,
                "label_en": ENGLISH_CHOICES["shape"][value],
                "extra": Decimal("0"),
                "active": True,
            }
            for value, label in SHAPE_CHOICES
        ],
        "coatings": [
            {
                "value": value,
                "label": label,
                "label_en": ENGLISH_CHOICES["coating"][value],
                "extra": pricing["coating_additions"][value],
                "active": True,
            }
            for value, label in COATING_CHOICES
        ],
        "packaging": [
            {
                "value": value,
                "label": label,
                "label_en": ENGLISH_CHOICES["packaging"][value],
                "extra": pricing["packaging_additions"][value],
                "active": True,
            }
            for value, label in PACKAGING_CHOICES
        ],
    }


def localized_calculator_options(pricing=None):
    pricing = normalize_calculator_pricing(pricing)
    english = get_language() == "en"
    products = []
    for product in pricing["products"]:
        products.append(
            {
                **product,
                "label": product["label_en"] or product["label"] if english else product["label"],
                "sizes": [
                    {
                        **size,
                        "base_price": str(size["base_price"]),
                        "multiplier": pricing["size_multipliers"].get(
                            size["value"], Decimal("1")
                        ),
                        "label": f'{size["label"]}' if english else size["label"],
                    }
                    for size in product["sizes"]
                ],
                "modifier_groups": [
                    {
                        **group,
                        "label_ru": group["label"],
                        "label": group["label_en"] or group["label"] if english else group["label"],
                        "options": [
                            {
                                **option,
                                "label_ru": option["label"],
                                "label": option["label_en"] or option["label"] if english else option["label"],
                                "amount": str(option["amount"]),
                            }
                            for option in group["options"]
                            if option.get("active", True)
                        ],
                    }
                    for group in product["modifier_groups"]
                ],
            }
        )
    options = {
        "products": tuple(products),
        "flavors": tuple(
            {
                **option,
                "label_ru": option["label"],
                "label": (
                    option["label_en"]
                    if get_language() == "en"
                    else option["label"]
                ),
            }
            for option in pricing["option_catalog"]["flavors"]
            if option["active"]
        ),
        "sizes": tuple(
            {
                "value": size["value"],
                "label": size["label"],
                "base_price": size["base_price"],
                "multiplier": pricing["size_multipliers"].get(
                    size["value"], Decimal("1")
                ),
            }
            for size in products[0]["sizes"]
        ),
        "shapes": tuple(
            {
                **option,
                "label_ru": option["label"],
                "label": (
                    option["label_en"]
                    if get_language() == "en"
                    else option["label"]
                ),
            }
            for option in pricing["option_catalog"]["shapes"]
            if option["active"]
        ),
        "coatings": tuple(
            {
                **option,
                "label_ru": option["label"],
                "label": (
                    option["label_en"]
                    if get_language() == "en"
                    else option["label"]
                ),
            }
            for option in pricing["option_catalog"]["coatings"]
            if option["active"]
        ),
        "packaging": tuple(
            {
                **option,
                "label_ru": option["label"],
                "label": (
                    option["label_en"]
                    if get_language() == "en"
                    else option["label"]
                ),
            }
            for option in pricing["option_catalog"]["packaging"]
            if option["active"]
        ),
        "deliveries": tuple(
            {"value": value, "label": label, "cost": pricing["delivery_costs"][value]}
            for value, label in DELIVERY_CHOICES
        ),
        "payments": tuple(
            {
                **payment,
                "label": payment["label_en"] if english else payment["label"],
            }
            for payment in pricing["payment_methods"]
        ),
    }
    if not english:
        return options

    choice_groups = {
        "deliveries": "delivery",
        "payments": "payment",
    }
    return {
        group: tuple(
            {
                **option,
                "label": ENGLISH_CHOICES[choice_groups[group]].get(
                    option["value"], option["label"]
                ),
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
    product_value = configuration.get("product", pricing["products"][0]["value"])
    product = next(
        (item for item in pricing["products"] if item["value"] == product_value),
        None,
    )
    if product is None:
        raise ValueError(f"Unknown calculator product: {product_value}")
    selected_size = next(
        (size for size in product["sizes"] if size["value"] == str(configuration["size"])),
        None,
    )
    if selected_size is None:
        raise ValueError(f'Unknown calculator size for {product_value}: {configuration["size"]}')
    base_price = selected_size["base_price"]
    modifiers = configuration.get("modifiers")
    if not isinstance(modifiers, dict):
        modifiers = {
            group: configuration.get(legacy_field, "")
            for group, legacy_field in (
                ("flavors", "flavor"),
                ("shapes", "shape"),
                ("coatings", "coating"),
                ("packaging", "packaging"),
            )
        }
    unit_price = base_price
    selected_modifier_values = {}
    for group in product["modifier_groups"]:
        option_value = modifiers.get(group["value"])
        if not option_value:
            legacy_value = modifiers.get(
                {"flavors": "flavor", "shapes": "shape", "coatings": "coating", "packaging": "packaging"}.get(group["value"], "")
            )
            option_value = legacy_value or (group["options"][0]["value"] if group["options"] else "")
        option = next(
            (item for item in group["options"] if item["value"] == option_value),
            None,
        )
        if option is None:
            raise ValueError(f'Unknown calculator option for {group["value"]}: {option_value}')
        selected_modifier_values[group["value"]] = option_value
        if option["amount_type"] == "percent":
            unit_price += base_price * option["amount"] / Decimal("100")
        else:
            unit_price += option["amount"]
    unit_price = unit_price.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    coating_group = next(
        (
            group
            for group in product["modifier_groups"]
            if is_coating_modifier_group(group)
        ),
        None,
    )
    selected_coating = (
        selected_modifier_values.get(coating_group["value"], "")
        if coating_group
        else ""
    )
    applicable_lead_time_rules = [
        rule
        for rule in product["lead_time_rules"]
        if rule["coating_value"] == selected_coating
        and quantity >= rule["min_quantity"]
    ]
    lead_time_days = (
        max(
            applicable_lead_time_rules,
            key=lambda rule: rule["min_quantity"],
        )["days"]
        if applicable_lead_time_rules
        else pricing["lead_time_days"]
    )
    payment_value = configuration.get("payment", "")
    payment_methods = {method["value"] for method in pricing["payment_methods"]}
    if payment_value and payment_value not in payment_methods:
        raise ValueError(f"Unknown calculator payment method: {payment_value}")
    matched_rules = [
        rule
        for rule in pricing["discount_rules"]
        if (
            rule["trigger"] == "payment"
            and rule["trigger_value"] == payment_value
        )
        or (
            rule["trigger"] == "quantity"
            and rule["trigger_value"].isdigit()
            and quantity >= int(rule["trigger_value"])
        )
    ]
    legacy_quantity_percent = next(
        (
            Decimal(discount)
            for threshold, discount in pricing["discount_tiers"]
            if quantity >= threshold
        ),
        Decimal("0"),
    )
    quantity_percent = max(
        [legacy_quantity_percent] + [
            rule["amount"]
            for rule in matched_rules
            if rule["trigger"] == "quantity" and rule["amount_type"] == "percent"
        ],
    )
    payment_percent = sum(
        (
            rule["amount"]
            for rule in matched_rules
            if rule["trigger"] == "payment" and rule["amount_type"] == "percent"
        ),
        Decimal("0"),
    )
    discount_percent = min(quantity_percent + payment_percent, Decimal("100"))
    delivery_cost = pricing["delivery_costs"][configuration["delivery"]]
    subtotal = unit_price * quantity
    discount_amount = subtotal * discount_percent / Decimal("100")
    discount_amount += sum(
        (
            rule["amount"]
            for rule in matched_rules
            if rule["amount_type"] == "fixed"
        ),
        Decimal("0"),
    )
    discount_amount = min(discount_amount, subtotal)
    total_price = (subtotal - discount_amount + delivery_cost).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return {
        "unit_price": unit_price,
        "discount_percent": int(discount_percent),
        "discount_amount": discount_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "delivery_cost": delivery_cost,
        "lead_time_days": lead_time_days,
        "total_price": total_price,
    }
