# inventory/management/commands/import_locations.py
import csv
from django.core.management.base import BaseCommand
from django.db import transaction
from inventory.models import Location, Aimag, SumDuureg

class Command(BaseCommand):
    help = 'CSV файлаас станцын байршлуудыг импортлох'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='CSV файлын зам')

    def handle(self, *args, **options):
        file_path = options['csv_file']
        
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            success_count = 0
            error_count = 0
            
            try:
                with transaction.atomic():
                    for row in reader:
                        try:
                            # 1. Аймаг, Сумыг олох эсвэл үүсгэх
                            aimag, _ = Aimag.objects.get_or_create(name=row['aimag'])
                            sum_obj, _ = SumDuureg.objects.get_or_create(
                                name=row['sum'], aimag=aimag
                            )
                            
                            # 2. Координат шалгах (Монгол улсын хязгаар)
                            lat = float(row['latitude'])
                            lon = float(row['longitude'])
                            if not (41.0 <= lat <= 53.0 and 87.0 <= lon <= 120.0):
                                raise ValueError(f"Буруу координат: {lat}, {lon}")

                            # 3. Location үүсгэх
                            Location.objects.update_or_create(
                                name=row['name'],
                                defaults={
                                    'location_type': row['type'],
                                    'aimag_ref': aimag,
                                    'sum_ref': sum_obj,
                                    'wmo_index': row.get('wmo'),
                                    'latitude': lat,
                                    'longitude': lon,
                                }
                            )
                            success_count += 1
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"Алдаа {row['name']}: {e}"))
                            error_count += 1
                            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Гүйлгээ цуцлагдлаа: {e}"))
                return

        self.stdout.write(self.style.SUCCESS(f"Амжилттай: {success_count}, Алдаа: {error_count}"))