import os
import csv
import django
import decimal
from decimal import Decimal

# Django-ийн орчныг тохируулах
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meteo_config.settings')
django.setup()

from inventory.models import Location, Aimag, Soum

# Монгол улсын аймгуудын жагсаалт
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
    Soum.objects.all().delete()
    
    aimag_objs = {}
    for name in AIMAG_LIST:
        obj, _ = Aimag.objects.get_or_create(name=name)
        aimag_objs[name] = obj
    return aimag_objs

def clean_decimal(value, default="0"):
    """Тоон утгыг аюулгүй хөрвүүлэх"""
    if not value or value.strip() == "":
        return Decimal(default)
    try:
        return Decimal(value.strip().replace(',', '.'))
    except (decimal.InvalidOperation, ValueError):
        return Decimal(default)

def run_import(file_path, loc_type, aimag_objs):
    if not os.path.exists(file_path):
        print(f"Файл олдсонгүй: {file_path}")
        return

    print(f"--- {loc_type} төрлийн станцуудыг {file_path}-аас оруулж байна ---")
    
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader) # Гарчиг алгасах
        
        count = 0
        for row in reader:
            if not row or len(row) < 5: continue
            
            try:
                # Баганы дараалал: [0:aimag, 1:station_nam, 2:index, 3:lat, 4:lon, 5:hhh]
                aimag_name = row[0].strip()
                station_name = row[1].strip()
                wmo_idx = row[2].strip()
                lat = clean_decimal(row[3])
                lon = clean_decimal(row[4])
                elev = clean_decimal(row[5]) if len(row) > 5 else Decimal("0")

                # Аймгийг таних
                target_aimag = aimag_objs.get(aimag_name)
                if not target_aimag:
                    for a_name, a_obj in aimag_objs.items():
                        if a_name in aimag_name or aimag_name in a_name:
                            target_aimag = a_obj
                            break
                if not target_aimag: target_aimag = aimag_objs["Улаанбаатар"]

                # "Төв" гэхийн оронд Станцын нэрийг Сум-д бүртгэх
                # Хаалт доторх нэмэлт тайлбарыг (Ус судлалын харуул гэх мэт) цэвэрлэх
                soum_name = station_name.split('(')[0].strip()
                target_soum, _ = Soum.objects.get_or_create(name=soum_name, aimag=target_aimag)

                # Байршлыг үүсгэх
                Location.objects.create(
                    name=station_name,
                    wmo_index=wmo_idx,
                    latitude=lat,
                    longitude=lon,
                    elevation=elev,
                    location_type=loc_type,
                    aimag_ref=target_aimag,
                    soum_ref=target_soum,
                )
                count += 1
            except Exception as e:
                print(f"Алдаа: {row} дээр: {e}")

    print(f"Амжилттай: {count} станц/сум бүртгэгдлээ.")

if __name__ == "__main__":
    # 1. Системийг цэвэрлэж, 21 аймаг бэлдэх
    objs = clear_and_prep()
    
    # 2. Файлууд байгаа хавтас
    base_path = "import_data"
    
    # Файлуудыг дарааллан унших
    run_import(os.path.join(base_path, "AWS.csv"), "AWS", objs)
    run_import(os.path.join(base_path, "HYDRO.csv"), "HYDRO", objs)
    run_import(os.path.join(base_path, "METEO.csv"), "METEO", objs)