import csv

src = r"D:\meteo_system\import_data\admin_units_full_utf8.csv"
dst = r"D:\meteo_system\import_data\admin_units_fixed.csv"

rows = []
with open(src, "r", encoding="utf-8-sig", errors="replace") as f:
    reader = csv.reader(f)
    for r in reader:
        if not r:
            continue
        parts = [p.strip() for p in r[0].split(",", 1)]
        if len(parts) == 2:
            rows.append(parts)

with open(dst, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["aimag", "sum"])
    for a, s in rows[1:]:
        w.writerow([a, s])

print("OK -> created:", dst)
