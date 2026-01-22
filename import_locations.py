import os
import csv
import django
import decimal
from decimal import Decimal

# 1. Django орчныг тохируулах
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meteo_config.settings')
django.setup()

from inventory.models import Location, Aimag, SumDuureg  # Моделийн нэрийг засав

# Монгол улсын аймгуудын стандарт жагсаалт
AIMAG_LIST = [
    "Улаанбаатар", "Архангай", "Баян-Өлгий", "Баянхонгор", "Булган", 
    "Говь-Алтай", "Говьсүмбэр", "Дархан-Уул", "Дорнод", "Дорноговь", 
    "Дундговь", "Завхан", "Орхон", "Өвөрхангай", "Өмнөговь", 
    "Сүхбаатар", "Сэлэнгэ", "Төв", "Увс", "Ховд", "Хөвсгөл", "Хэнтий"
]

def clear_and_prep():
    """Бүх хуучин өгөгдлийг цэвэрлэж, аймгуудыг бэлдэх"""
    print("--- Өгөгдлийн санг бүрэн цэвэрлэж байна ---")
    Location.objects.all().delete()
    # SumDuureg-ийг устгавал өмнөх setup_admin-ий өгөгдөл устах тул 
    # зөвхөн станцтай холбоотой шинээр үүсэх сумдыг зохицуулна.
    
    aimag_objs = {}
    for name in AIMAG_LIST:
        obj, _ = Aimag.objects.get_or_create(name=name)
        aimag_objs[name] = obj
    return aimag_objs

def clean_decimal(value, default="0"):
    """Тоон утгыг аюулгүй хөрвүүлэх"""
    if not value or value.strip() == "":
        return None  # FloatField бол None байх нь дээр
    try:
        # Таслалтай тоог цэгтэй болгох
        clean_val = str(value).strip().replace(',', '.')
        return float(clean_val)
    except (ValueError, TypeError):
        return None

def run_import(file_path, loc_type, aimag_objs):
    if not os.path.exists(file_path):
        print(f"❌ Файл олдсонгүй: {file_path}")
        return

    print(f"--- {loc_type} төрлийн станцуудыг {file_path}-аас оруулж байна ---")
    
    # utf-8-sig нь Excel-ийн BOM тэмдэгтийг автоматаар цэвэрлэнэ
    with open(file_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        try:
            next(reader) # Гарчиг алгасах
        except StopIteration:
            return
        
        count = 0
        for row in reader:
            if not row or len(row) < 3: continue
            
            try:
                # Баганы дараалал: [0:aimag, 1:station_name, 2:index, 3:lat, 4:lon]
                aimag_name = row[0].strip()
                station_name = row[1].strip()
                wmo_idx = row[2].strip() if len(row) > 2 else ""
                lat = clean_decimal(row[3]) if len(row) > 3 else None
                lon = clean_decimal(row[4]) if len(row) > 4 else None

                # Аймгийг таних (Ижил төстэй нэрийг хайх)
                target_aimag = aimag_objs.get(aimag_name)
                if not target_aimag:
                    for a_name, a_obj in aimag_objs.items():
                        if a_name in aimag_name or aimag_name in a_name:
                            target_aimag = a_obj
                            break
                if not target_aimag: target_aimag = aimag_objs["Улаанбаатар"]

                # "Сум" талбарт Станцын нэрийг бүртгэх
                sum_name = station_name.split('(')[0].strip()
                target_sum, _ = SumDuureg.objects.get_or_create(name=sum_name, aimag=target_aimag)

                # Байршлыг үүсгэх (Талбарын нэрсийг models.py-той тулгав)
                Location.objects.create(
                    name=station_name,
                    wmo_index=wmo_idx,
                    latitude=lat,
                    longitude=lon,
                    location_type=loc_type if loc_type != "AWS" else "METEO", # AWS бол METEO төрөл
                    aimag_ref=target_aimag,
                    sum_ref=target_sum, # soum_ref-ийг sum_ref болгож засав
                )
                count += 1
            except Exception as e:
                print(f"⚠️ Алдаа: {row} -> {e}")

    print(f"✅ Амжилттай: {count} станц бүртгэгдлээ.")

if __name__ == "__main__":
    # 1. Системийг цэвэрлэж, 22 аймаг бэлдэх
    objs = clear_and_prep()
    
    # 2. Файлууд байгаа хавтас
    base_path = "import_data"
    
    # Файлуудыг дарааллан унших
    run_import(os.path.join(base_path, "AWS.csv"), "AWS", objs)
    run_import(os.path.join(base_path, "HYDRO.csv"), "HYDRO", objs)
    run_import(os.path.join(base_path, "METEO.csv"), "METEO", objs)

    print("\n🚀 Станцуудыг амжилттай импорт хийж дууслаа!")