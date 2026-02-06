from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

# Input (2 дахь файл) expected columns:
# Аймаг, №, Сумын нэр, Өртөө/Харуулын нэр, Өргөрөг, Уртраг, (optional) Өндөр
REQUIRED = {"Аймаг", "Сумын нэр", "Өртөө/Харуулын нэр", "Өргөрөг", "Уртраг"}

def sniff_delimiter(sample: str) -> str:
    # ; байвал ; үгүй бол ,
    return ";" if sample.count(";") > sample.count(",") else ","

def norm(s: str) -> str:
    return (s or "").strip()

def to_float_str(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    try:
        return str(float(s))
    except ValueError:
        return ""

def main(
    in_path: str,
    out_path: str,
    location_type: str,
    default_notes: str = "",
):
    location_type = norm(location_type).upper()
    if not location_type:
        raise SystemExit("location_type required (e.g., WEATHER or HYDRO)")

    raw = Path(in_path).read_text(encoding="utf-8-sig", errors="strict")
    delim = sniff_delimiter(raw[:2000])
    reader = csv.DictReader(raw.splitlines(), delimiter=delim)

    missing = REQUIRED - set(reader.fieldnames or [])
    if missing:
        raise SystemExit(f"Missing columns in input: {sorted(missing)}. Found={reader.fieldnames}")

    out_headers = [
        "aimag_name",
        "sum_name",
        "location_type",
        "name",
        "lat",
        "lon",
        "elevation_m",
        "notes",
    ]

    rows: List[Dict[str, str]] = []
    for r in reader:
        aimag = norm(r.get("Аймаг", ""))
        summ = norm(r.get("Сумын нэр", ""))
        name = norm(r.get("Өртөө/Харуулын нэр", ""))
        lat = to_float_str(r.get("Өргөрөг", ""))
        lon = to_float_str(r.get("Уртраг", ""))
        elev = to_float_str(r.get("Өндөр", "")) if "Өндөр" in (reader.fieldnames or []) else ""

        if not (aimag and summ and name and lat and lon):
            # Дутуу мөрийг алгасна (хүсвэл raise болгож өөрчилж болно)
            continue

        rows.append({
            "aimag_name": aimag,
            "sum_name": summ,
            "location_type": location_type,     # WEATHER эсвэл HYDRO
            "name": name,
            "lat": lat,
            "lon": lon,
            "elevation_m": elev,
            "notes": default_notes,
        })

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_headers, delimiter=";")
        w.writeheader()
        w.writerows(rows)

    print(f"OK: {len(rows)} rows -> {out} (type={location_type}, delim=';')")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage: python convert_guard_to_locations_exact.py <input_guard.csv> <output_exact.csv> <WEATHER|HYDRO> [notes]")
        raise SystemExit(2)
    notes = sys.argv[4] if len(sys.argv) >= 5 else ""
    main(sys.argv[1], sys.argv[2], sys.argv[3], notes)
