from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from inventory.models import Aimag, Location, SumDuureg


class Command(BaseCommand):
    help = "Улаанбаатарын AWS байршлуудыг 9 дүүрэгт (SumDuureg) polygon-аар онооно (sum_ref + district_name update)."

    def add_arguments(self, parser):
        parser.add_argument("--geojson", default="static/ub_districts.geojson")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument("--only-null", action="store_true")

    def handle(self, *args, **opts):
        geojson_path = Path(opts["geojson"]).resolve()
        dry = bool(opts["dry_run"])
        limit = int(opts["limit"] or 0)
        only_null = bool(opts["only_null"])

        try:
            from shapely.geometry import shape, Point
        except Exception as e:
            raise SystemExit("❌ shapely суусан байх ёстой. pip install shapely\n" + str(e))

        if not geojson_path.exists():
            raise SystemExit(f"❌ GeoJSON олдсонгүй: {geojson_path}")

        data = json.loads(geojson_path.read_text(encoding="utf-8"))
        feats = data.get("features") or []
        if not feats:
            raise SystemExit("❌ GeoJSON дээр features алга байна.")

        # ✅ Танай GeoJSON: properties дээр name_mn гэж байна
        districts = []
        for f in feats:
            props = f.get("properties") or {}
            dname = (props.get("name_mn") or "").strip()
            if not dname:
                continue
            geom = shape(f["geometry"])
            districts.append((dname, geom))

        if not districts:
            sample = (feats[0].get("properties") or {})
            raise SystemExit(f"❌ GeoJSON-оос district нэр олдсонгүй. sample keys={list(sample.keys())}")

        ub = Aimag.objects.get(name="Улаанбаатар")
        sum_map = {s.name.strip(): s for s in SumDuureg.objects.filter(aimag_ref=ub)}

        qs = Location.objects.filter(location_type="AWS", aimag_ref=ub)
        if only_null:
            qs = qs.filter(sum_ref__isnull=True)
        if limit > 0:
            qs = qs.order_by("id")[:limit]

        updated = 0
        not_found = 0
        no_point = 0

        @transaction.atomic
        def run():
            nonlocal updated, not_found, no_point

            for loc in qs.select_related("sum_ref"):
                if loc.latitude is None or loc.longitude is None:
                    no_point += 1
                    continue

                p = Point(float(loc.longitude), float(loc.latitude))

                hit = None
                for dname, poly in districts:
                    if poly.covers(p):
                        hit = dname
                        break

                if not hit:
                    not_found += 1
                    continue

                s = sum_map.get(hit)
                if not s:
                    not_found += 1
                    continue

                if dry:
                    updated += 1
                    continue

                loc.sum_ref = s
                if hasattr(loc, "district_name"):
                    loc.district_name = s.name
                    loc.save(update_fields=["sum_ref", "district_name"])
                else:
                    loc.save(update_fields=["sum_ref"])
                updated += 1

        run()

        self.stdout.write(self.style.SUCCESS(
            f"mode={'DRY' if dry else 'APPLY'} updated={updated} not_found={not_found} no_point={no_point} total={qs.count()}"
        ))
