from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def attach_orders_to_matching_accounts(apps, schema_editor):
    Preorder = apps.get_model("core", "Preorder")
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    database = schema_editor.connection.alias

    for preorder in Preorder.objects.using(database).filter(user__isnull=True).iterator():
        matching_users = User.objects.using(database).filter(email__iexact=preorder.email)
        if matching_users.count() == 1:
            preorder.user_id = matching_users.values_list("pk", flat=True).get()
            preorder.save(update_fields=("user",), using=database)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_feedbacksubmission"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="preorder",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="preorders",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Пользователь",
            ),
        ),
        migrations.RunPython(
            attach_orders_to_matching_accounts,
            migrations.RunPython.noop,
        ),
    ]
