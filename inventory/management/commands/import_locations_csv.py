from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from typing import Optional, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from inventory.models import Aimag, SumDuureg, Location


def norm(s: str) -> str:
    return (s or "").strip()


def model_has_field(model_cls, field_name: str) -> bool:
    try:
        model_cls._meta.get_field(field_name)
        return True
    except Exception:
        return False


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # meters
    r = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


@dataclass
class Row:
    aimag_name: str
    sum_name: str
    location_type: str
    name: str
    lat: float
    lon: float
    elevation_m: Optional[float]
    notes: str


class Command(BaseCommand):
    help = "Import Location rows from exact CSV: aimag_name;sum_name;location_type;name;lat;lon;elevation_m;notes"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)

        parser.add_argument("--mode", choices=["UPSERT", "REPLACE"], default="UPSERT")
        parser.add_argument(
            "--replace-type",
            dest="replace_type",
            default=None,
            help="When mode=REPLACE: WEATHER or HYDRO etc.",
        )

        parser.add_argument("--create-aimag", action="store_true", default=False)
        parser.add_argument("--create-sum", action="store_true", default=False)

        parser.add_argument(
            "--near-meters",
            type=float,
            default=0.0,
            help="Warn/block near-duplicate points within meters",
        )
        parser.add_argument(
            "--strict-near",
            action="store_true",
            default=False,
            help="If set, near-duplicate raises error (default: warn)",
        )

        parser.add_argument("--dry-run", action="store_true", default=False)

    def _read_rows(self, path: str) -> list[Row]:
        try:
            f = open(path, "r", encoding="utf-8-sig", newline="")
        except OSError as e:
            raise CommandError(f"Cannot open CSV: {path}. {e}")

        with f:
            reader = csv.DictReader(f, delimiter=";")
            required = {"aimag_name", "sum_name", "location_type", "name", "lat", "lon"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise CommandError(f"Missing required columns: {sorted(missing)}. Found={reader.fieldnames}")

            rows: list[Row] = []
            for i, r in enumerate(reader, start=2):
                aimag = norm(r.get("aimag_name", ""))
                summ = norm(r.get("sum_name", ""))
                ltype = norm(r.get("location_type", "")).upper()
                name = norm(r.get("name", ""))

                lat_s = norm(r.get("lat", ""))
                lon_s = norm(r.get("lon", ""))
                elev_s = norm(r.get("elevation_m", ""))
                notes = norm(r.get("notes", ""))

                if not (aimag and summ and ltype and name and lat_s and lon_s):
                    continue

                try:
                    lat = float(lat_s)
                    lon = float(lon_s)
                except ValueError:
                    raise CommandError(f"Bad lat/lon at line {i}: lat={lat_s}, lon={lon_s}")

                elev: Optional[float] = None
                if elev_s:
                    try:
                        elev = float(elev_s)
                    except ValueError:
                        elev = None

                rows.append(
                    Row(
                        aimag_name=aimag,
                        sum_name=summ,
                        location_type=ltype,
                        name=name,
                        lat=lat,
                        lon=lon,
                        elevation_m=elev,
                        notes=notes,
                    )
                )

            return rows

    def _get_or_create_aimag(self, name: str, create: bool) -> Aimag:
        obj = Aimag.objects.filter(name=name).first()
        if obj:
            return obj
        if not create:
            raise CommandError(f"Aimag not found: '{name}'. Use --create-aimag")
        return Aimag.objects.create(name=name)

    def _get_or_create_sum(self, aimag: Aimag, name: str, create: bool) -> SumDuureg:
        obj = SumDuureg.objects.filter(aimag_ref=aimag, name=name).first()
        if obj:
            return obj
        if not create:
            raise CommandError(f"Sum not found: '{name}' (aimag='{aimag.name}'). Use --create-sum")
        return SumDuureg.objects.create(aimag_ref=aimag, name=name)

    def _near_check(self, row: Row, near_m: float) -> Tuple[bool, Optional[Location], float]:
        if near_m <= 0:
            return (False, None, 0.0)

        # quick bbox filter (~1 deg lat ~111km)
        dlat = near_m / 111000.0
        dlon = near_m / (111000.0 * max(0.2, math.cos(math.radians(row.lat))))

        qs = Location.objects.filter(
            location_type=row.location_type,
            latitude__gte=row.lat - dlat,
            latitude__lte=row.lat + dlat,
            longitude__gte=row.lon - dlon,
            longitude__lte=row.lon + dlon,
        )

        best: Optional[Location] = None
        best_d = 1e18
        for loc in qs.iterator():
            try:
                d = haversine_m(row.lat, row.lon, float(loc.latitude), float(loc.longitude))
            except Exception:
                continue
            if d < best_d:
                best_d = d
                best = loc

        if best and best_d <= near_m:
            return (True, best, float(best_d))
        return (False, None, float(best_d if best else 0.0))

    @transaction.atomic
    def handle(self, *args, **opts):
        csv_path: str = opts["csv_path"]
        mode: str = opts["mode"]
        replace_type: Optional[str] = opts.get("replace_type")
        create_aimag: bool = opts["create_aimag"]
        create_sum: bool = opts["create_sum"]
        near_m: float = float(opts["near_meters"] or 0.0)
        strict_near: bool = bool(opts["strict_near"])
        dry_run: bool = bool(opts["dry_run"])

        rows = self._read_rows(csv_path)
        if not rows:
            self.stdout.write(self.style.WARNING("No valid rows found."))
            return

        if mode == "REPLACE":
            if not replace_type:
                raise CommandError("mode=REPLACE requires --replace-type (e.g. WEATHER or HYDRO)")
            replace_type = replace_type.strip().upper()
            if not dry_run:
                deleted, _ = Location.objects.filter(location_type=replace_type).delete()
                self.stdout.write(self.style.WARNING(f"REPLACE: deleted {deleted} Location rows with type={replace_type}"))
            else:
                self.stdout.write(self.style.WARNING(f"DRY-RUN REPLACE: would delete Location rows type={replace_type}"))

        # Optional field availability (Location model дээр бодитоор байвал л ашиглана)
        HAS_ELEV_M = model_has_field(Location, "elevation_m")
        HAS_ELEV = model_has_field(Location, "elevation")
        HAS_NOTES = model_has_field(Location, "notes")
        HAS_REMARK = model_has_field(Location, "remark")
        HAS_DESC = model_has_field(Location, "description")

        created = 0
        updated = 0

        for row in rows:
            # near-duplicate check (DB)
            is_near, found, dist = self._near_check(row, near_m)
            if is_near and found:
                msg = f"NEAR({near_m}m): '{row.name}' close to existing '{found.name}' dist={dist:.1f}m (type={row.location_type})"
                if strict_near:
                    raise CommandError(msg)
                self.stdout.write(self.style.WARNING(msg))

            aimag = self._get_or_create_aimag(row.aimag_name, create_aimag)
            summ = self._get_or_create_sum(aimag, row.sum_name, create_sum)

            # UPSERT key: (aimag_ref, sum_ref, location_type, name)
            obj = (
                Location.objects.filter(
                    aimag_ref=aimag,
                    sum_ref=summ,
                    location_type=row.location_type,
                    name=row.name,
                )
                .first()
            )

            if obj is None:
                create_kwargs = dict(
                    aimag_ref=aimag,
                    sum_ref=summ,
                    location_type=row.location_type,
                    name=row.name,
                    latitude=row.lat,
                    longitude=row.lon,
                )

                # optional fields
                if row.elevation_m is not None:
                    if HAS_ELEV_M:
                        create_kwargs["elevation_m"] = row.elevation_m
                    elif HAS_ELEV:
                        create_kwargs["elevation"] = row.elevation_m

                if row.notes:
                    if HAS_NOTES:
                        create_kwargs["notes"] = row.notes
                    elif HAS_REMARK:
                        create_kwargs["remark"] = row.notes
                    elif HAS_DESC:
                        create_kwargs["description"] = row.notes

                if not dry_run:
                    Location.objects.create(**create_kwargs)
                created += 1

            else:
                changed_fields = []

                if float(obj.latitude) != float(row.lat):
                    obj.latitude = row.lat
                    changed_fields.append("latitude")

                if float(obj.longitude) != float(row.lon):
                    obj.longitude = row.lon
                    changed_fields.append("longitude")

                # optional updates
                if row.elevation_m is not None:
                    if HAS_ELEV_M:
                        if (getattr(obj, "elevation_m", None) or None) != (row.elevation_m or None):
                            obj.elevation_m = row.elevation_m
                            changed_fields.append("elevation_m")
                    elif HAS_ELEV:
                        if (getattr(obj, "elevation", None) or None) != (row.elevation_m or None):
                            obj.elevation = row.elevation_m
                            changed_fields.append("elevation")

                if row.notes:
                    if HAS_NOTES:
                        if (getattr(obj, "notes", "") or "") != row.notes:
                            obj.notes = row.notes
                            changed_fields.append("notes")
                    elif HAS_REMARK:
                        if (getattr(obj, "remark", "") or "") != row.notes:
                            obj.remark = row.notes
                            changed_fields.append("remark")
                    elif HAS_DESC:
                        if (getattr(obj, "description", "") or "") != row.notes:
                            obj.description = row.notes
                            changed_fields.append("description")

                if changed_fields:
                    if not dry_run:
                        obj.save(update_fields=changed_fields)
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"DONE mode={mode} dry_run={dry_run} created={created} updated={updated} near_warned={'yes' if near_m>0 else 'no'}"
            )
        )
