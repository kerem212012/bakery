from django.contrib import admin
from django.http import HttpResponse
from openpyxl import Workbook

from .models import CustomerProfile


@admin.action(description="Выгрузить выбранных юрлиц в Excel (.xlsx)")
def export_legal_entities_xlsx(modeladmin, request, queryset):
    profiles = queryset.filter(
        customer_type=CustomerProfile.CustomerType.LEGAL_ENTITY
    ).select_related("user")
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Юридические лица"
    worksheet.append(
        (
            "Контактное лицо",
            "Телефон",
            "Организация",
            "ИНН",
            "КПП",
            "Юридический адрес",
            "Email",
            "Дата регистрации",
        )
    )
    for profile in profiles:
        values = (
            profile.contact_name,
            profile.phone,
            profile.company_name,
            profile.inn,
            profile.kpp,
            profile.legal_address,
            profile.user.email,
        )
        worksheet.append(
            [
                f"'{value}"
                if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@"))
                else value
                for value in values
            ]
        )

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions
    for column, width in {
        "A": 28,
        "B": 20,
        "C": 34,
        "D": 16,
        "E": 14,
        "F": 50,
        "G": 34,
    }.items():
        worksheet.column_dimensions[column].width = width

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="legal-entity-customers.xlsx"'
    workbook.save(response)
    return response


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "customer_type",
        "company_name",
        "inn",
        "kpp",
        "contact_name",
        "phone",
    )
    list_filter = ("customer_type",)
    search_fields = (
        "user__username",
        "user__email",
        "company_name",
        "inn",
        "kpp",
        "contact_name",
    )
    actions = (export_legal_entities_xlsx,)
