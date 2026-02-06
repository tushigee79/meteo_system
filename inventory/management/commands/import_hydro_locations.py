from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from typing import Optional, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from inventory.models import Aimag, SumDuureg, Location


# -----------------------------
# Utilities
# -----------------------------
def _norm(s: str) -> str:
    return (s or "").strip()

def _to_float(s: str) -> Optional[float]:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in meters."""
    r = 6371000.0
    p = math.pi / 180.0
    dlat = (lat2 - lat1) * p
    dlon = (lon2 - lon1) * p
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin(dlon / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def set_if_field(obj, field: str, value) -> None:
    if hasattr(obj, field) and value is not None:
        setattr(obj, field, value)

def get_field_name(*candidates: str) -> Optional[str]:
    """Return first Location field that exists among candidates."""
    for f in candidates:
        if hasattr(Location, f) or hasattr(Location(), f):
            return f
    return None


@dataclass
class Row:
    aimag_name: str
    sum_name: str
    location_type: str
    hydro_feature: str
    name: str
    lat: float
    lon: float
    elevation_m: Optional[float]


class Command(BaseCommand):
    help = "Import hydro guard locations into БҮРТГЭЛ (Aimag/SumDuureg/Location)."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to hydro_locations.csv (UTF-8, ; delimited)")
        parser.add_argument("--dry-run", action="store_true", help="Validate only, do not write DB")
        parser.add_argument("--near-meters", type=float, default=80.0, help="Near-duplicate distance threshold (meters)")
        parser.add_argument("--create-aimag", action="store_true", help="Create missing Aimag by name")
        parser.add_argument("--create-sum", action="store_true", help="Create missing SumDuureg by name (requires Aimag)")
        parser.add_argument("--update-existing", action="store_true", help="If exact-match exists, update coordinates/elevation/notes")

    def handle(self, *args, **opts):
        path = opts["csv_path"]
        dry = bool(opts["dry_run"])
        near_m = float(opts["near_meters"])
        create_aimag = bool(opts["create_aimag"])
        create_sum = bool(opts["create_sum"])
        update_existing = bool(opts["update_existing"])

        # Detect your Location lat/lon fields (support common variants)
        lat_field = get_field_name("lat", "latitude")
        lon_field = get_field_name("lon", "longitude")
        if not lat_field or not lon_field:
            raise CommandError("Location model must have lat/lon fields (lat/latitude and lon/longitude).")

        # Optional fields
        elev_field = get_field_name("elevation_m", "elevation", "ground_asl", "altitude_m")
        notes_field = "notes" if hasattr(Location(), "notes") else ("description" if hasattr(Location(), "description") else None)
        type_field = "location_type" if hasattr(Location(), "location_type") else None

        rows: list[Row] = []
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            need_cols = {"aimag_name", "sum_name", "location_type", "hydro_feature", "name", "lat", "lon"}
            missing = need_cols - set(reader.fieldnames or [])
            if missing:
                raise CommandError(f"Missing columns: {sorted(missing)}. Found: {reader.fieldnames}")

            for i, r in enumerate(reader, start=2):
                aimag_name = _norm(r.get("aimag_name", ""))
                sum_name = _norm(r.get("sum_name", ""))
                location_type = _norm(r.get("location_type", "")).upper()
                hydro_feature = _norm(r.get("hydro_feature", "")).upper()
                name = _norm(r.get("name", ""))

                lat = _to_float(r.get("lat", ""))
                lon = _to_float(r.get("lon", ""))
                elev = _to_float(r.get("elevation_m", ""))

                if not aimag_name or not sum_name or not location_type or not hydro_feature or not name:
                    raise CommandError(f"Row {i}: empty required value (aimag/sum/type/feature/name).")
                if lat is None or lon is None:
                    raise CommandError(f"Row {i}: invalid lat/lon.")
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    raise CommandError(f"Row {i}: lat/lon out of range: {lat}, {lon}")

                rows.append(Row(
                    aimag_name=aimag_name,
                    sum_name=sum_name,
                    location_type=location_type,
                    hydro_feature=hydro_feature,
                    name=name,
                    lat=lat,
                    lon=lon,
                    elevation_m=elev,
                ))

        # -----------------------------
        # Validation: duplicates within file
        # -----------------------------
        key_seen = {}
        for idx, row in enumerate(rows):
            k = (row.aimag_name.lower(), row.sum_name.lower(), row.location_type, row.hydro_feature, row.name.lower())
            if k in key_seen:
                raise CommandError(f"Duplicate row in CSV: #{idx+1} duplicates #{key_seen[k]+1} (same aimag/sum/type/feature/name)")
            key_seen[k] = idx

        # Near-duplicate check (within file)
        for a in range(len(rows)):
            for b in range(a + 1, len(rows)):
                if rows[a].aimag_name == rows[b].aimag_name and rows[a].sum_name == rows[b].sum_name:
                    d = haversine_m(rows[a].lat, rows[a].lon, rows[b].lat, rows[b].lon)
                    if d <= near_m and rows[a].name != rows[b].name:
                        raise CommandError(
                            f"Near-duplicate in CSV (<= {near_m}m): "
                            f"'{rows[a].name}' vs '{rows[b].name}' at {d:.1f}m "
                            f"(Aimag={rows[a].aimag_name}, Sum={rows[a].sum_name})"
                        )

        created_loc = 0
        updated_loc = 0

        @transaction.atomic
        def do_import():
            nonlocal created_loc, updated_loc

            for row in rows:
                aimag = Aimag.objects.filter(name=row.aimag_name).first()
                if not aimag:
                    if not create_aimag:
                        raise CommandError(f"Aimag not found: '{row.aimag_name}'. Use --create-aimag.")
                    aimag = Aimag.objects.create(name=row.aimag_name)

                sum_qs = SumDuureg.objects.filter(name=row.sum_name, aimag_ref=aimag)
                sum_obj = sum_qs.first()
                if not sum_obj:
                    if not create_sum:
                        raise CommandError(f"Sum/Duureg not found: '{row.sum_name}' (Aimag='{row.aimag_name}'). Use --create-sum.")
                    sum_obj = SumDuureg.objects.create(name=row.sum_name, aimag_ref=aimag)

                # Exact match candidate: same sum + name (and location_type if available)
                q = Q(name=row.name) & Q(sum_ref=sum_obj)
                if type_field:
                    q &= Q(**{type_field: row.location_type})
                existing = Location.objects.filter(q).first()

                # DB near-duplicate check (within sum): any point within near_m
                # (limit candidate set by sum_ref)
                candidates = Location.objects.filter(sum_ref=sum_obj)
                for c in candidates:
                    c_lat = getattr(c, lat_field, None)
                    c_lon = getattr(c, lon_field, None)
                    if c_lat is None or c_lon is None:
                        continue
                    dist = haversine_m(row.lat, row.lon, float(c_lat), float(c_lon))
                    if dist <= near_m and (existing is None or c.pk != existing.pk):
                        # Allow if same name (re-import) else block
                        if _norm(getattr(c, "name", "")).lower() != row.name.lower():
                            raise CommandError(
                                f"DB near-duplicate (<= {near_m}m) in {row.aimag_name}/{row.sum_name}: "
                                f"'{row.name}' near '{c.name}' at {dist:.1f}m"
                            )

                if existing:
                    if update_existing:
                        setattr(existing, lat_field, row.lat)
                        setattr(existing, lon_field, row.lon)
                        set_if_field(existing, "aimag_ref", aimag)
                        set_if_field(existing, "sum_ref", sum_obj)
                        if type_field:
                            setattr(existing, type_field, row.location_type)
                        if elev_field and row.elevation_m is not None:
                            setattr(existing, elev_field, row.elevation_m)
                        # store hydro_feature in notes/description if field exists
                        if notes_field:
                            old = getattr(existing, notes_field) or ""
                            tag = f"[HYDRO_FEATURE={row.hydro_feature}]"
                            if tag not in old:
                                setattr(existing, notes_field, (old + "\n" + tag).strip())
                        existing.save()
                        updated_loc += 1
                    # else: skip silently
                    continue

                loc = Location()
                loc.name = row.name
                set_if_field(loc, "aimag_ref", aimag)
                set_if_field(loc, "sum_ref", sum_obj)
                if type_field:
                    setattr(loc, type_field, row.location_type)
                setattr(loc, lat_field, row.lat)
                setattr(loc, lon_field, row.lon)
                if elev_field and row.elevation_m is not None:
                    setattr(loc, elev_field, row.elevation_m)
                if notes_field:
                    setattr(loc, notes_field, f"[HYDRO_FEATURE={row.hydro_feature}]")
                loc.save()
                created_loc += 1

        if dry:
            self.stdout.write(self.style.SUCCESS(f"DRY-RUN OK: rows={len(rows)}, near_m={near_m}"))
            return

        do_import()
        self.stdout.write(self.style.SUCCESS(
            f"IMPORT DONE: rows={len(rows)}, created={created_loc}, updated={updated_loc}, near_m={near_m}"
        ))
