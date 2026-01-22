import csv
import os
from django.core.management.base import BaseCommand
from inventory.models import Aimag, SumDuureg, Location, Organization

class Command(BaseCommand):
    help = 'METEO.csv файлаас давхардалгүйгээр өгөгдөл импортлох'

    def handle(self, *args, **options):
        file_path = 'METEO.csv'
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"'{file_path}' файл олдсонгүй!"))
            return

        try:
            with open(file_path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                count = 0
                
                for row in reader:
                    aimag_name = row.get('aimag')
                    station_name = row.get('station_nam')
                    wmo_index = row.get('index')
                    lat_val = float(row.get('lat')) if row.get('lat') else None
                    lon_val = float(row.get('lon')) if row.get('lon') else None

                    if not aimag_name or not station_name:
                        continue

                    # 1. Аймаг үүсгэх/унших
                    aimag_obj, _ = Aimag.objects.get_or_create(name=aimag_name.strip())
                    
                    # 2. Сум үүсгэх
                    sum_obj, _ = SumDuureg.objects.get_or_create(
                        name=station_name.strip(), 
                        aimag=aimag_obj
                    )
                    
                    # 3. Байгууллага үүсгэх
                    org_name = f"{aimag_obj.name} УЦУОШТ"
                    org_obj, _ = Organization.objects.get_or_create(name=org_name)
                    
                    # 4. Байршил үүсгэх (Нэр + Координатаар нь давхардал шалгана)
                    # update_or_create ашиглах нь "more than one" алдаанаас сэргийлнэ
                    loc_obj, created = Location.objects.update_or_create(
                        name=station_name.strip(),
                        aimag_ref=aimag_obj,
                        latitude=lat_val, # Координатыг нь түлхүүр болгож өгөв
                        longitude=lon_val,
                        defaults={
                            'sum_ref': sum_obj,
                            'owner_org': org_obj,
                            'location_type': 'METEO',
                            'wmo_index': wmo_index.strip() if wmo_index else None
                        }
                    )
                    if created:
                        count += 1

            self.stdout.write(self.style.SUCCESS(f'Амжилттай: {count} станцыг системд шинээр нэмлээ.'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Алдаа гарлаа: {str(e)}"))