from django.utils import timezone
from django.db import transaction

from inventory.models import WorkflowStatus, Location, Device, MaintenanceService, ControlAdjustment


def _first_or_create_minimal(Model, **preferred):
    obj = Model.objects.first()
    if obj:
        return obj

    data = dict(preferred)

    for f in Model._meta.fields:
        if f.primary_key:
            continue
        name = f.name
        if name in data:
            continue
        if f.has_default():
            continue
        if getattr(f, "null", False):
            continue

        # Relations
        if f.is_relation and getattr(f, "many_to_one", False):
            Rel = f.remote_field.model
            rel_obj = Rel.objects.first()
            if not rel_obj:
                # minimal create for related
                rel_obj = _first_or_create_minimal(Rel)
            data[name] = rel_obj
            continue

        it = f.get_internal_type()
        if it in ("CharField", "TextField", "SlugField"):
            data[name] = f"{Model.__name__}-{name}"
        elif it in ("IntegerField", "BigIntegerField", "SmallIntegerField", "PositiveIntegerField", "PositiveSmallIntegerField"):
            data[name] = 1
        elif it in ("FloatField", "DecimalField"):
            data[name] = 0
        elif it == "BooleanField":
            data[name] = False
        elif it == "DateTimeField":
            data[name] = timezone.now()
        elif it == "DateField":
            data[name] = timezone.now().date()
        else:
            data[name] = f"{Model.__name__}-{name}"

    return Model.objects.create(**data)


@transaction.atomic
def seed_pending(n=2):
    loc = _first_or_create_minimal(
        Location,
        name="TEST Location",
        latitude=47.9,
        longitude=106.9,
    )

    dev = Device.objects.first()
    if not dev:
        dev = _first_or_create_minimal(
            Device,
            name="TEST Device",
            location=loc,
            serial_number=f"TEST-SN-{timezone.now().strftime('%H%M%S')}",
        )
    else:
        if getattr(dev, "location_id", None) is None:
            dev.location = loc
            dev.save()

    created = {"maint": 0, "control": 0}

    for i in range(n):
        m = MaintenanceService.objects.create(
            device=dev,
            workflow_status=WorkflowStatus.SUBMITTED,
            date=timezone.now().date(),
            note=f"TEST maint pending {i+1}",
        )
        created["maint"] += 1

    for i in range(n):
        c = ControlAdjustment.objects.create(
            device=dev,
            workflow_status=WorkflowStatus.SUBMITTED,
            date=timezone.now().date(),
            note=f"TEST control pending {i+1}",
        )
        created["control"] += 1

    return loc, dev, created


if __name__ == "__main__":
    loc, dev, created = seed_pending(n=2)
    print("OK seeded:", created, "location_id=", loc.id, "device_id=", dev.id)
