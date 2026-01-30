# inventory/migrations/0030_device_qr_security.py
from django.db import migrations, models
from django.utils import timezone
from datetime import timedelta


def _backfill_expiry(apps, schema_editor):
    Device = apps.get_model("inventory", "Device")
    now = timezone.now()
    # set expiry for nulls
    Device.objects.filter(qr_expires_at__isnull=True).update(qr_expires_at=now + timedelta(days=365))


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0029_device_qr_token_alter_device_kind"),
    ]

    operations = [
        migrations.AddField(
            model_name="device",
            name="qr_expires_at",
            field=models.DateTimeField(null=True, blank=True, db_index=True, verbose_name="QR хүчинтэй хугацаа"),
        ),
        migrations.AddField(
            model_name="device",
            name="qr_revoked_at",
            field=models.DateTimeField(null=True, blank=True, db_index=True, verbose_name="QR хүчингүй болгосон огноо"),
        ),
        migrations.RunPython(_backfill_expiry, migrations.RunPython.noop),
    ]
