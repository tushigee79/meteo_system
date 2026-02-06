from __future__ import annotations

import csv
from pathlib import Path

# 2 дахь файл: "Аймаг,№,Сумын нэр,Өртөө/Харуулын нэр,Өргөрөг,Уртраг,Өндөр"
# заримдаа delimiter нь ',' байдаг, заримдаа ';' байх магадлалтай -> auto-detect

IN_COLUMNS = {
    "Аймаг",
    "Сумын нэр",
    "Өртөө/Харуулын нэр",
    "Өргөрөг",
    "Уртраг",
}

def sniff_delimiter(sample: str) -> str:
    # энгийн sniff: ; байвал ; үгүй бол ,
    return ";" if sample.count(";") > sample.count(",") else ","

def norm(s: str) -> str:
    return (s or "").strip()

def to_float(s: str):
    s = (s or "").strip()
    if not s:
        return ""
    try:
        return str(float(s))
    except ValueError:
        return ""

def main(in_path: str, out_path: str, hydro_feature: str = "RIVER"):
    p = Path(in_path)
    raw = p.read_text(encoding="utf-8-sig", errors="strict")
    delim = sniff_delimiter(raw[:2000])

    reader = csv.DictReader(raw.splitlines(), delimiter=delim)

    missing = IN_COLUMNS - set(reader.fieldnames or [])
    if missing:
        raise SystemExit(f"Missing columns in input: {sorted(missing)}. Found={reader.fieldnames}")

    out_headers = [
        "aimag_name",
        "sum_name",
        "location_type",
        "hydro_feature",
        "name",
        "lat",
        "lon",
        "elevation_m",
    ]

    rows = []
    for r in reader:
        aimag = norm(r.get("Аймаг", ""))
        summ = norm(r.get("Сумын нэр", ""))
        name = norm(r.get("Өртөө/Харуулын нэр", ""))
        lat = to_float(r.get("Өргөрөг", ""))
        lon = to_float(r.get("Уртраг", ""))
        elev = to_float(r.get("Өндөр", "")) if "Өндөр" in (reader.fieldnames or []) else ""

        if not (aimag and summ and name and lat and lon):
            # дутуу мөр алгасна (хүсвэл энд raise болгож болно)
            continue

        rows.append({
            "aimag_name": aimag,
            "sum_name": summ,
            "location_type": "HYDRO",
            "hydro_feature": hydro_feature,  # default RIVER
            "name": name,
            "lat": lat,
            "lon": lon,
            "elevation_m": elev,
        })

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_headers, delimiter=";")
        w.writeheader()
        w.writerows(rows)

    print(f"OK: wrote {len(rows)} rows -> {out}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python convert_guard_to_hydro_csv.py <input_guard.csv> <output_hydro_locations.csv> [RIVER|LAKE]")
        raise SystemExit(2)
    feature = sys.argv[3].strip().upper() if len(sys.argv) >= 4 else "RIVER"
    main(sys.argv[1], sys.argv[2], feature)
