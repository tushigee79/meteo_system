from __future__ import annotations

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from inventory.models import Aimag, SumDuureg, Location


class Command(BaseCommand):
    help = "Import canonical locations from semicolon CSV (aimag_name;sum_name;location_type;name;lat;lon;...)"

    def add_arguments(self, parser):
        parser.add_argument("--csv", required=True)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--update-coords", action="store_true")

    def handle(self, *args, **opts):
        p = Path(opts["csv"])
        if not p.exists():
            raise CommandError(f"File not found: {p}")

        dry = bool(opts["dry_run"])
        update = bool(opts["update_coords"])

        with p.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            rows = list(reader)

        created = updated = skipped = missing_ref = 0

        @transaction.atomic
        def run():
            nonlocal created, updated, skipped, missing_ref

            for r in rows:
                aimag_name = (r.get("aimag_name") or "").strip()
                sum_name = (r.get("sum_name") or "").strip()
                loc_type = (r.get("location_type") or "").strip().upper()
                name = (r.get("name") or "").strip()

                if not (aimag_name and loc_type and name):
                    skipped += 1
                    continue

                aimag = Aimag.objects.filter(name__iexact=aimag_name).first()
                if not aimag:
                    missing_ref += 1
                    continue

                sum_obj = None
                if sum_name:
                    sum_obj = SumDuureg.objects.filter(aimag_ref=aimag, name__iexact=sum_name).first()

                lat = float((r.get("lat") or "").strip())
                lon = float((r.get("lon") or "").strip())

                obj = Location.objects.filter(
                    aimag_ref=aimag,
                    sum_ref=sum_obj,
                    location_type=loc_type,
                    name__iexact=name,
                ).first()

                if obj:
                    if update:
                        if dry:
                            updated += 1
                        else:
                            obj.latitude = lat
                            obj.longitude = lon
                            obj.save()
                            updated += 1
                    else:
                        skipped += 1
                    continue

                if dry:
                    created += 1
                    continue

                Location.objects.create(
                    name=name,
                    location_type=loc_type,
                    aimag_ref=aimag,
                    sum_ref=sum_obj,
                    latitude=lat,
                    longitude=lon,
                )
                created += 1

        run()

        self.stdout.write(self.style.SUCCESS(
            f"Import OK | created={created} updated={updated} skipped={skipped} missing_ref={missing_ref} | mode={'DRY' if dry else 'APPLY'}"
        ))

        if dry:
            raise Exception("DRY-RUN rollback")
