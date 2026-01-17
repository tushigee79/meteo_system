import os
import sys
import csv
from pathlib import Path

# =========================================================
# Ensure project root is on PYTHONPATH and Django is setup
# =========================================================
BASE_DIR = Path(__file__).resolve().parent.parent  # D:\meteo_system
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meteo_config.settings")

import django  # noqa: E402
django.setup()  # noqa: E402

from inventory.models import Aimag, Location  # noqa: E402

# =========================================================
# Config
# =========================================================
DATA_DIR = BASE_DIR / "import_data"  # D:\meteo_system\import_data

FILES = [
    ("Meteo.csv", "METEO"),
    ("HYDRO.csv", "HYDRO"),
    ("AWS.csv", "AWS"),
]

# =========================================================
# Helpers
# =========================================================
def norm(s) -> str:
    return (s or "").strip()

def get_col(row: dict, *keys):
    # Normal keys
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]
    # BOM header cases
    for k in keys:
        for rk in row.keys():
            if rk.replace("\ufeff", "").strip() == k and row[rk] not in (None, ""):
                return row[rk]
    return None

def get_or_create_aimag(name: str) -> Aimag:
    name = norm(name)
    obj, _ = Aimag.objects.get_or_create(name=name)
    return obj

def to_float(x):
    try:
        return float(str(x).strip())
    except Exception:
        return None

def to_int(x):
    try:
        return int(float(str(x).strip()))
    except Exception:
        return None

# =========================================================
# Importer
# =========================================================
def import_file(filename: str, location_type: str):
    path = DATA_DIR / filename
    print(f"\n📂 Importing {filename} as {location_type}")
    if not path.exists():
        print(f"❌ File not found: {path}")
        return

    # utf-8-sig -> BOM автоматаар арилгана
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        added = 0
        updated = 0
        skipped = 0

        for row in reader:
            aimag_name = get_col(row, "aimag")
            name = get_col(row, "station_nam", "station_name", "name")
            wmo_index = get_col(row, "index", "wmo_index")
            lat = get_col(row, "lat", "latitude")
            lon = get_col(row, "lon", "longitude")
            hhh = get_col(row, "hhh", "elev", "elevation")

            if not (aimag_name and name):
                skipped += 1
                continue

            aimag = get_or_create_aimag(aimag_name)

            # ✅ defaults: зөвхөн update хийх талбарууд
            defaults = {
                "status": "OPERATIONAL",
            }

            # Байгаа талбарууд л бол бөглөнө
            if hasattr(Location, "wmo_index"):
                defaults["wmo_index"] = to_int(wmo_index)

            if hasattr(Location, "latitude"):
                defaults["latitude"] = to_float(lat)

            if hasattr(Location, "longitude"):
                defaults["longitude"] = to_float(lon)

            # Танайд elevation талбар "elevation" гэж байсан
            if hasattr(Location, "elevation"):
                defaults["elevation"] = to_float(hhh)

            # ✅ Давхардал дарахгүй түлхүүр: name + aimag + location_type
            obj, created = Location.objects.get_or_create(
                name=norm(name),
                aimag_fk=aimag,
                location_type=location_type,
                defaults=defaults,
            )

            if created:
                added += 1
            else:
                changed = False
                for k, v in defaults.items():
                    if v is None:
                        continue
                    if getattr(obj, k, None) != v:
                        setattr(obj, k, v)
                        changed = True
                if changed:
                    obj.save()
                    updated += 1

        print(f"✅ Done {filename}: Added={added}, Updated={updated}, Skipped={skipped}")

def main():
    for fname, ltype in FILES:
        import_file(fname, ltype)
    print("\n🎉 Import finished.")

if __name__ == "__main__":
    main()
