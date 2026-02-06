from django.db import migrations, models
import uuid


def _backfill_qr_tokens(apps, schema_editor):
    Device = apps.get_model("inventory", "Device")

    qs = Device.objects.filter(qr_token__isnull=True).values_list("id", flat=True)
    for pk in qs:
        Device.objects.filter(pk=pk, qr_token__isnull=True).update(qr_token=uuid.uuid4())


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0028_alter_device_options"),
    ]

    operations = [
        # 1) Түр nullable, unique биш байдлаар нэмнэ
        migrations.AddField(
            model_name="device",
            name="qr_token",
            field=models.UUIDField(
                null=True,
                blank=True,
                editable=False,
                db_index=True,
                verbose_name="QR токен",
            ),
        ),

        # 2) Existing мөрүүдэд UUID тараана
        migrations.RunPython(_backfill_qr_tokens, migrations.RunPython.noop),

        # 3) Unique + default болгож constraint тавина
        migrations.AlterField(
            model_name="device",
            name="qr_token",
            field=models.UUIDField(
                default=uuid.uuid4,
                unique=True,
                editable=False,
                db_index=True,
                verbose_name="QR токен",
            ),
            preserve_default=False,
        ),
    ]
