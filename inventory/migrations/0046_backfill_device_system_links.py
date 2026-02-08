from django.db import migrations

def backfill_device_system(apps, schema_editor):
    # 🔒 SQLite дээр бол backfill хийхгүй (schema таарахгүй)
    if schema_editor.connection.vendor == "sqlite":
        return

    Device = apps.get_model("inventory", "Device")
    InstrumentCatalog = apps.get_model("inventory", "InstrumentCatalog")

    # --- доорх код чинь өмнөх хэвээр ---
    qs = Device.objects.filter(system__isnull=True).select_related("instrument")
    for d in qs:
        if d.instrument_id:
            try:
                ic = InstrumentCatalog.objects.get(id=d.instrument_id)
                d.system_id = ic.kind
                d.save(update_fields=["system"])
            except InstrumentCatalog.DoesNotExist:
                pass


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0045_alter_measurementsystem_options_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_device_system, migrations.RunPython.noop),
    ]
