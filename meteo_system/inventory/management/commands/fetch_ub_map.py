from django.core.management.base import BaseCommand
import geopandas as gpd
# ... таны бусад импорт ...

class Command(BaseCommand):
    help = 'UB хотын 9 дүүргийн газрын зургийг GeoBoundaries-аас татаж авна'

    def handle(self, *args, **options):
        # Таны main() функц энд ороод 
        # out_gj файлыг static/data/ хавтсанд хадгалахаар тохируулна
        self.stdout.write(self.style.SUCCESS('Амжилттай татаж авлаа'))