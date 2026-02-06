from django.db import migrations


def backfill_device_system(apps, schema_editor):
    Device = apps.get_model("inventory", "Device")
    MeasurementSystem = apps.get_model("inventory", "MeasurementSystem")

    qs = (
        Device.objects
        .filter(system__isnull=True, kind__in=["RADAR", "AEROLOGY", "AWS"])
        .select_related("location", "catalog_item")
    )

    cache = {}  # (location_id, kind) -> system_id

    for d in qs:
        if not d.location_id:
            continue

        key = (d.location_id, d.kind)
        sys_id = cache.get(key)

        if not sys_id:
            base_name = ""
            if getattr(d, "catalog_item_id", None) and d.catalog_item:
                base_name = (getattr(d.catalog_item, "name_mn", "") or getattr(d.catalog_item, "name", "") or "").strip()
            if not base_name:
                base_name = (d.other_name or "").strip()
            if not base_name:
                loc_name = getattr(d.location, "name", "") or f"Location#{d.location_id}"
                base_name = f"{loc_name} {d.kind}"

            sys, _ = MeasurementSystem.objects.get_or_create(
                location_id=d.location_id,
                system_type=d.kind,
                defaults={
                    "name": base_name,
                    "status": "OPERATIONAL",
                    "owner_org_id": getattr(d.location, "owner_org_id", None),
                    "note": "Auto backfill from Device.kind (RADAR/AEROLOGY/AWS)",
                },
            )
            sys_id = sys.id
            cache[key] = sys_id

        d.system_id = sys_id
        d.save(update_fields=["system"])


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0045_alter_measurementsystem_options_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_device_system, migrations.RunPython.noop),
    ]
