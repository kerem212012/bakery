import core.storage
import core.models
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_feedbacksubmission_phone"),
    ]

    operations = [
        migrations.AddField(
            model_name="preorder",
            name="payment_status",
            field=models.CharField(
                choices=[("pending", "Ожидает оплаты"), ("paid", "Оплачено")],
                default="pending",
                max_length=12,
                verbose_name="Статус оплаты",
            ),
        ),
        migrations.CreateModel(
            name="PreorderContract",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "file",
                    models.FileField(
                        upload_to=core.models.preorder_contract_path,
                        storage=core.storage.PrivateMediaStorage(),
                        validators=[django.core.validators.FileExtensionValidator(["pdf"])],
                        verbose_name="Договор",
                    ),
                ),
                (
                    "uploaded_at",
                    models.DateTimeField(auto_now=True, verbose_name="Загружено"),
                ),
                (
                    "preorder",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="contract",
                        to="core.preorder",
                        verbose_name="Заказ",
                    ),
                ),
            ],
            options={
                "verbose_name": "договор заказа",
                "verbose_name_plural": "договоры заказов",
            },
        ),
    ]