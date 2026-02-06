from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Dict, Tuple


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


def is_mojibake(line: str) -> bool:
    return ("â" in line) or ("Ð" in line) or ("Ñ" in line)


def fix_mojibake(s: str) -> str:
    return s.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")


def read_text_smart(path: str) -> str:
    b = Path(path).read_bytes()

    # 1) UTF-8 (BOM байж болно)
    try:
        s = b.decode("utf-8-sig")
        first = s.splitlines()[0] if s else ""
        return fix_mojibake(s) if is_mojibake(first) else s
    except UnicodeDecodeError:
        pass

    # 2) latin1 fallback
    s = b.decode("latin1", errors="ignore")
    first = s.splitlines()[0] if s else ""
    return fix_mojibake(s) if is_mojibake(first) else s


# === Таны HYDRO/METEO файлын бодит толгойт багануудыг хамруулах ===
COLMAP = {
    # аймаг (танайд Сум_Аймаг_Хот дээр аймаг л байгааг бид ашиглана)
    "aimag_name": ["Аймаг", "Аймаг_Хот", "Аймаг/Хот", "Aimag", "aimag_name", "Сум_Аймаг_Хот"],

    # сум (танайд тусдаа sum байхгүй тул нэрээс нь гаргана)
    "sum_name": ["Сумын нэр", "Сум", "Sum", "sum_name"],

    # нэр
    "name": ["Өртөө/Харуулын нэр", "ӨртөөХаруулын нэр", "Харуулын нэрс", "Нэр", "Name", "name"],

    # координат
    "lat": ["Өргөрөг", "Latitude", "lat", "latitude"],
    "lon": ["Уртраг", "Longitude", "lon", "longitude"],

    # өндөр
    "elevation_m": ["Өндөр", "Өндөр(m)", "Elevation", "elevation", "elevation_m"],

    # optional notes
    "notes": ["Тайлбар", "Notes", "notes"],

    # Гол/Нуур (танайд "Төрөл" дээр байна)
    "feature": ["Төрөл", "Feature", "feature"],
}


def pick(row: Dict[str, str], keys: list[str]) -> str:
    for k in keys:
        if k in row and norm(row[k]):
            return norm(row[k])
    return ""


def infer_sum_from_name(name: str) -> str:
    """
    'Сэлэнгэ - Тосонцэнгэл' -> 'Тосонцэнгэл'
    'Долооннуурын гол-Мөнххайрхан' -> 'Мөнххайрхан'
    """
    n = norm(name)
    if not n:
        return ""

    # 1) хамгийн нийтлэг: " - "
    if " - " in n:
        parts = [p.strip() for p in n.split(" - ") if p.strip()]
        if len(parts) >= 2:
            return parts[-1]

    # 2) space-гүй зураас
    if "-" in n:
        parts = [p.strip() for p in n.split("-") if p.strip()]
        if len(parts) >= 2:
            return parts[-1]

    # 3) тусгай тохиолдол: "гол" гэсэн үг орсон бол түүнээс хойшхийг sum гэж үзэх
    m = re.search(r"(?:гол)\s*(.*)$", n, flags=re.IGNORECASE)
    if m:
        tail = m.group(1).strip(" -")
        if tail:
            return tail

    return ""


def map_feature_to_tag(feature_raw: str) -> str:
    f = norm(feature_raw)
    if not f:
        return ""
    if "Нуур" in f:
        return "LAKE"
    if "Гол" in f:
        return "RIVER"
    return f.upper()


def convert(in_path: str, out_path: str, location_type: str, default_notes: str = "") -> int:
    raw = read_text_smart(in_path)
    delim = sniff_delim(raw[:2000])

    reader = csv.DictReader(raw.splitlines(), delimiter=delim)

    out_headers = ["aimag_name", "sum_name", "location_type", "name", "lat", "lon", "elevation_m", "notes"]
    out_rows = []

    for r in reader:
        aimag = pick(r, COLMAP["aimag_name"])
        summ = pick(r, COLMAP["sum_name"])
        name = pick(r, COLMAP["name"])

        # ✅ Танай HYDRO.txt-д sum байхгүй тул нэрээс нь автоматаар авна
        if not summ:
            summ = infer_sum_from_name(name)

        lat = to_float_str(pick(r, COLMAP["lat"]))
        lon = to_float_str(pick(r, COLMAP["lon"]))
        elev = to_float_str(pick(r, COLMAP["elevation_m"]))
        notes = pick(r, COLMAP["notes"]) or default_notes

        # HYDRO feature tag (RIVER/LAKE) notes-д шингээх
        feature_tag = map_feature_to_tag(pick(r, COLMAP["feature"]))
        if feature_tag:
            tag = f"[HYDRO_FEATURE={feature_tag}]"
            if tag not in (notes or ""):
                notes = (notes + " | " + tag).strip() if notes else tag
                notes = notes.replace("\r", " ").replace("\n", " ").strip()


        # required check
        if not (aimag and summ and name and lat and lon):
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
