import pandas as pd

src = r"D:\meteo_system\import_source\METEO_exact.csv"
out = r"D:\meteo_system\import_source\METEO_canonical.csv"

df = pd.read_csv(src, sep=";", encoding="utf-8-sig")
print("CSV columns:", list(df.columns))

out_df = pd.DataFrame({
    "aimag_name": df["Аймаг"].astype(str).str.strip(),
    "sum_name": df["Сумын нэр"].astype(str).str.strip(),
    "location_type": "WEATHER",
    "name": df["Өртөө/Харуулын нэр"].astype(str).str.strip(),
    "lat": df["Өргөрөг"],
    "lon": df["Уртраг"],
    "elevation_m": df["Өндөр"],
    "notes": "",
})

out_df.to_csv(out, index=False, sep=";", encoding="utf-8-sig")
print("Wrote:", out)
