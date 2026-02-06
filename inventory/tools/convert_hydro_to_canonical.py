import pandas as pd

src = r"D:\meteo_system\import_source\HYDROЕ_exact.csv"
out = r"D:\meteo_system\import_source\HYDRO_canonical.csv"

df = pd.read_csv(src, encoding="utf-8-sig")  # comma
print("CSV columns:", list(df.columns))

# Аймгийн нэрэнд "-" ордог тусгай тохиолдлууд
AIMAG_HYPHEN = {
    "Дархан-Уул",
    "Говь-Алтай",
    "Баян-Өлгий",
}

def split_admin(x: str):
    x = (x or "").strip()

    # 1) "Сум, Аймаг" хэлбэр
    if "," in x:
        parts = [p.strip() for p in x.split(",") if p.strip()]
        if len(parts) >= 2:
            sum_name = parts[0]
            aimag_name = parts[-1]
            return aimag_name, sum_name

    # 2) "Аймаг" дангаараа
    # (зарим мөр дээр сум байхгүй байж болно)
    if "-" not in x:
        return x, ""

    # 3) "-" байгаа бол эхлээд аймаг нь өөрөө "-" агуулдаг эсэхийг шалгана
    # Ж: "Баян-Өлгий" / "Говь-Алтай" / "Дархан-Уул"
    parts = [p.strip() for p in x.split("-") if p.strip()]
    if len(parts) >= 2:
        first2 = f"{parts[0]}-{parts[1]}"
        if first2 in AIMAG_HYPHEN:
            aimag_name = first2
            sum_name = "-".join(parts[2:]).strip() if len(parts) > 2 else ""
            return aimag_name, sum_name

    # 4) Ерөнхий fallback: "Сум - Аймаг" биш байж болно, гэхдээ ихэнхдээ
    # "Сум - Аймаг" гэж ирдэг тохиолдолд last-г аймаг гэж авна
    if len(parts) >= 2:
        aimag_name = parts[-1]
        sum_name = parts[0]
        return aimag_name, sum_name

    return x, ""

aimag_sum = df["Сум_Аймаг_Хот"].apply(split_admin)
df["aimag_name"] = aimag_sum.apply(lambda t: t[0])
df["sum_name"] = aimag_sum.apply(lambda t: t[1])

out_df = pd.DataFrame({
    "aimag_name": df["aimag_name"].astype(str).str.strip(),
    "sum_name": df["sum_name"].astype(str).str.strip(),
    "location_type": "HYDRO",
    "name": df["Харуулын нэрс"].astype(str).str.strip(),
    "lat": df["Өргөрөг"],
    "lon": df["Уртраг"],
    "elevation_m": "",
    "notes": df["Төрөл"].astype(str).str.strip(),
})

out_df.to_csv(out, index=False, sep=";", encoding="utf-8-sig")
print("Wrote:", out, "rows=", len(out_df))
