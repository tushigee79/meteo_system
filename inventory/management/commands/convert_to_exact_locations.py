from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Optional, Tuple


def sniff_delim(sample: str) -> str:
    return ";" if sample.count(";") >= sample.count(",") else ","


def norm(s: str) -> str:
    return (s or "").strip()


def to_float_str(s: str) -> str:
    s = norm(s)
    if not s:
        return ""
    try:
        return str(float(s))
    except ValueError:
        return ""


# олон янзын header-ийг нэгтгэж унших mapping
COLMAP = {
    # aimag
    "aimag_name": ["Аймаг", "Аймаг_Хот", "Аймаг/Хот", "Aimag", "AimagName", "aimag_name"],
    # sum
    "sum_name": ["Сумын нэр", "Сум", "Sum", "SumName", "sum_name"],
    # name
    "name": ["Өртөө/Харуулын нэр", "ӨртөөХаруулын нэр", "Харуулын нэрс", "Нэр", "Name", "name"],
    # lat/lon
    "lat": ["Өргөрөг", "Latitude", "lat", "latitude"],
    "lon": ["Уртраг", "Longitude", "lon", "longitude"],
    # elevation
    "elevation_m": ["Өндөр", "Өндөр(m)", "Elevation", "elevation", "elevation_m"],
    # combined "Сум_Аймаг_Хот"
    "sum_aimag_city": ["Сум_Аймаг_Хот"],
    # optional notes
    "notes": ["Тайлбар", "Notes", "notes"],
}


def pick(row: Dict[str, str], keys: list[str]) -> str:
    for k in keys:
        if k in row and norm(row[k]):
            return norm(row[k])
    return ""


def split_sum_aimag_city(value: str) -> Tuple[str, str]:
    """
    "Сум, Аймаг" / "Сум - Аймаг" / "Аймаг" гэх мэт янзтай байж болно.
    Энд хамгийн аюулгүй нь: хэрвээ 2 хэсэг бол sum, aimag гэж үзнэ.
    """
    v = norm(value)
    if not v:
        return ("", "")
    for sep in [" - ", "-", ",", " / ", "/"]:
        if sep in v:
            parts = [p.strip() for p in v.split(sep) if p.strip()]
            if len(parts) >= 2:
                # ихэнхдээ "Сум - Аймаг" эсвэл "Сум, Аймаг"
                return (parts[0], parts[1])
    # нэг л үг бол aimag гэж үзээд sum-г хоосон орхино
    return ("", v)


def convert(in_path: str, out_path: str, location_type: str, default_notes: str = "") -> int:
    raw = Path(in_path).read_text(encoding="utf-8-sig", errors="strict")
    delim = sniff_delim(raw[:2000])

    reader = csv.DictReader(raw.splitlines(), delimiter=delim)

    out_headers = ["aimag_name", "sum_name", "location_type", "name", "lat", "lon", "elevation_m", "notes"]
    out_rows = []

    for r in reader:
        aimag = pick(r, COLMAP["aimag_name"])
        summ = pick(r, COLMAP["sum_name"])
        name = pick(r, COLMAP["name"])
        lat = to_float_str(pick(r, COLMAP["lat"]))
        lon = to_float_str(pick(r, COLMAP["lon"]))
        elev = to_float_str(pick(r, COLMAP["elevation_m"]))
        notes = pick(r, COLMAP["notes"]) or default_notes

        # fallback: "Сум_Аймаг_Хот" байвал задлах
        if (not aimag or not summ) and "Сум_Аймаг_Хот" in (reader.fieldnames or []):
            s2, a2 = split_sum_aimag_city(pick(r, COLMAP["sum_aimag_city"]))
            summ = summ or s2
            aimag = aimag or a2

        # required check
        if not (aimag and summ and name and lat and lon):
            # дутуу мөрийг алгасна (хүсвэл энд raise болгож болно)
            continue

        out_rows.append({
            "aimag_name": aimag,
            "sum_name": summ,
            "location_type": location_type.upper(),
            "name": name,
            "lat": lat,
            "lon": lon,
            "elevation_m": elev,
            "notes": notes,
        })

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_headers, delimiter=";")
        w.writeheader()
        w.writerows(out_rows)

    return len(out_rows)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage: python convert_to_exact_locations.py <input.csv/txt> <output_exact.csv> <WEATHER|HYDRO> [notes]")
        raise SystemExit(2)
    notes = sys.argv[4] if len(sys.argv) >= 5 else ""
    n = convert(sys.argv[1], sys.argv[2], sys.argv[3], notes)
    print(f"OK: wrote {n} rows -> {sys.argv[2]}")
