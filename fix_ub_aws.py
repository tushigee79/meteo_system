import os
import csv
import django

# 1. Django орчныг тохируулах
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meteo_config.settings')
django.setup()

from inventory.models import Location, Aimag

def fix_aws_types():
    file_path = os.path.join('import_data', 'AWS.csv')
    
    if not os.path.exists(file_path):
        print(f"❌ Файл олдсонгүй: {file_path}")
        return

    print("--- Улаанбаатар болон бусад AWS станцуудын төрлийг засаж байна ---")
    
    with open(file_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        count = 0
        
        for row in reader:
            station_name = row.get('station_nam', '').strip()
            aimag_name = row.get('aimag', '').strip()
            
            # Нийслэл/Улаанбаатар зөрүүг шалгах
            if aimag_name in ["Нийслэл", "Нийслэл хот", "Улаанбаатар"]:
                aimag_name = "Улаанбаатар"

            # Станцыг нэр болон аймгаар нь хайх
            location = Location.objects.filter(
                name=station_name, 
                aimag_ref__name__icontains=aimag_name
            ).first()

            if location:
                # ✅ Төрлийг нь AWS болгож солих
                # Хэрэв таны модел дээр AWS төрөл байхгүй бол 'METEO' хэвээр үлдээгээд 
                # өөр талбараар ялгаж болно. Гэхдээ админ дээр салгаж харахын тулд 'AWS' байх хэрэгтэй.
                location.location_type = 'AWS' 
                location.save()
                count += 1

    print(f"✅ Нийт {count} станцын төрлийг AWS болгож шинэчиллээ.")

if __name__ == "__main__":
    fix_aws_types()