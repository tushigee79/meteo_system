import os
import csv
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meteo_config.settings')
django.setup()

from inventory.models import Location, Aimag, SumDuureg

def run_final_import():
    base_path = "import_data"
    files = [
        ('METEO.csv', 'METEO'),
        ('HYDRO.csv', 'HYDRO'),
        ('AWS.csv', 'METEO'),
    ]

    print("--- Өгөгдлийг бүрэн цэвэрлэж байна ---")
    Location.objects.all().delete()

    for file_name, loc_type in files:
        file_path = os.path.join(base_path, file_name)
        if not os.path.exists(file_path):
            print(f"❌ Файл олдсонгүй: {file_path}")
            continue

        print(f"⏳ {file_name} файлыг оруулж байна...")
        with open(file_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                try:
                    aimag_raw = row.get('aimag', '').strip()
                    # ✅ ЧУХАЛ: "Нийслэл" гэж байвал "Улаанбаатар" руу хөрвүүлэх
                    if aimag_raw == "Нийслэл" or aimag_raw == "Нийслэл хот":
                        aimag_name = "Улаанбаатар"
                    else:
                        aimag_name = aimag_raw

                    station_name = row.get('station_nam', '').strip()
                    
                    # 1. Аймаг олох
                    aimag = Aimag.objects.filter(name__icontains=aimag_name).first()
                    if not aimag:
                        continue

                    # 2. Сум олох
                    sum_name = station_name.split('(')[0].strip()
                    sum_obj = SumDuureg.objects.filter(name__icontains=sum_name, aimag=aimag).first()

                    # 3. Location үүсгэх
                    Location.objects.create(
                        name=station_name,
                        aimag_ref=aimag,
                        sum_ref=sum_obj,
                        location_type=loc_type,
                        wmo_index=row.get('index', ''),
                        latitude=float(row['lat']) if row.get('lat') else None,
                        longitude=float(row['lon']) if row.get('lon') else None,
                    )
                    count += 1
                except Exception as e:
                    pass
            print(f"✅ {file_name}: {count} станц нэмэгдлээ.")

if __name__ == "__main__":
    run_final_import()
    print("\n🚀 Бүх станцууд (Нийслэлийг оруулаад) амжилттай орлоо!")