from __future__ import annotations
import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from inventory.models import Aimag, SumDuureg, Location


class Command(BaseCommand):
    help = "Link/create AWS Locations and set parent_location to matched METEO(WEATHER) Locations using mapping CSV."

    def add_arguments(self, parser):
        parser.add_argument("--mapping", required=True, help="Path to aws_to_meteo_mapping.csv")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--max-distance-m", type=float, default=2000.0)
        parser.add_argument("--update-aws-coords", action="store_true")

    def handle(self, *args, **opts):
        p = Path(opts["mapping"])
        if not p.exists():
            raise CommandError(f"File not found: {p}")

        dry = bool(opts["dry_run"])
        max_dist = float(opts["max_distance_m"])
        upd = bool(opts["update_aws_coords"])

        rows = list(csv.DictReader(p.open("r", encoding="utf-8-sig", newline="")))

        linked = created = updated = skipped = missing = 0

        @transaction.atomic
        def run():
            nonlocal linked, created, updated, skipped, missing

            for r in rows:
                dist = float(r["distance_m"]) if (r.get("distance_m") or "").strip() else 0.0
                if dist > max_dist:
                    skipped += 1
                    continue

                aimag = Aimag.objects.filter(name__iexact=r["meteo_aimag"]).first()
                if not aimag:
                    missing += 1
                    continue

                sum_obj = SumDuureg.objects.filter(
                    aimag_ref=aimag, name__iexact=r["meteo_sum"]
                ).first()

                meteo = Location.objects.filter(
                    aimag_ref=aimag,
                    sum_ref=sum_obj,
                    name__iexact=r["meteo_station_name"],
                    location_type="WEATHER",
                ).first()
                if not meteo:
                    missing += 1
                    continue

                aws = Location.objects.filter(
                    aimag_ref=aimag,
                    sum_ref=sum_obj,
                    name__iexact=r["aws_station_name"],
                    location_type="AWS",
                ).first()

                if not aws:
                    if dry:
                        created += 1
                        continue
                    aws = Location.objects.create(
                        name=r["aws_station_name"],
                        location_type="AWS",
                        aimag_ref=aimag,
                        sum_ref=sum_obj,
                        latitude=float(r["aws_lat"]),
                        longitude=float(r["aws_lon"]),
                    )
                    created += 1
                else:
                    if upd and not dry:
                        aws.latitude = float(r["aws_lat"])
                        aws.longitude = float(r["aws_lon"])
                        aws.save()
                        updated += 1

                if dry:
                    linked += 1
                else:
                    aws.parent_location = meteo
                    aws.save()
                    linked += 1

        run()

        self.stdout.write(self.style.SUCCESS(
            f"mode={'DRY' if dry else 'APPLY'} linked={linked} created={created} updated={updated} skipped_far={skipped} missing={missing}"
        ))

        if dry:
            # rollback
            raise Exception("DRY-RUN finished (rollback)")
