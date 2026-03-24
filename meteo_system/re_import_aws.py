import os
import csv
import django

# 1. Django орчныг тохируулах
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meteo_config.settings')
django.setup()

from inventory.models import Location, Aimag, SumDuureg

def re_import_aws():
    file_path = os.path.join('import_data', 'AWS.csv')
    
    if not os.path.exists(file_path):
        print(f"❌ Файл олдсонгүй: {file_path}")
        return

    print("--- Өмнөх станцуудыг цэвэрлэж байна ---")
    Location.objects.all().delete() # Зөвхөн станцуудыг цэвэрлэнэ

    print(f"⏳ {file_path} файлыг засаж оруулж байна...")
    
    with open(file_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        count = 0
        
        for row in reader:
            try:
                # Баганын нэрсийг таны файлтай тулгав (aimag, station_nam, index, lat, lon)
                aimag_name = row.get('aimag', '').strip()
                station_name = row.get('station_nam', '').strip()
                
                # ✅ ЗАСВАР: "Нийслэл" гэж байвал "Улаанбаатар" болгох
                if aimag_name == "Нийслэл":
                    aimag_name = "Улаанбаатар"

                # 1. Аймаг олох
                aimag = Aimag.objects.filter(name__icontains=aimag_name).first()
                if not aimag:
                    print(f"⚠️ Аймаг олдсонгүй: {aimag_name}")
                    continue

                # 2. Сум олох (Станцын нэртэй ижил сум хайх)
                sum_name = station_name.split('(')[0].strip()
                sum_obj = SumDuureg.objects.filter(name__icontains=sum_name, aimag=aimag).first()

                # 3. Станц үүсгэх
                Location.objects.create(
                    name=station_name,
                    aimag_ref=aimag,
                    sum_ref=sum_obj,
                    location_type='METEO', # AWS бол METEO төрөл
                    wmo_index=row.get('index', ''),
                    latitude=float(row['lat']) if row.get('lat') else None,
                    longitude=float(row['lon']) if row.get('lon') else None,
                )
                count += 1
            except Exception as e:
                print(f"❌ Алдаа: {row.get('station_nam')} -> {e}")

    print(f"✅ Нийт {count} станц амжилттай шинэчлэгдэж орлоо.")

if __name__ == "__main__":
    re_import_aws()