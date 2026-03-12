from django.core.management.base import BaseCommand
from inventory.models import Aimag, SumDuureg

UB_NAME = "Улаанбаатар"
DISTRICTS = [
    "Багануур",
    "Багахангай",
    "Баянгол",
    "Баянзүрх",
    "Налайх",
    "Сонгинохайрхан",
    "Сүхбаатар",
    "Хан-Уул",
    "Чингэлтэй",
]

class Command(BaseCommand):
    help = "Seed Улаанбаатар аймаг + 9 дүүрэг (SumDuureg) үүсгэнэ"

    def handle(self, *args, **options):
        ub, _ = Aimag.objects.get_or_create(name=UB_NAME, defaults={"code": "UB"})

        created = 0
        for d in DISTRICTS:
            obj, was_created = SumDuureg.objects.get_or_create(
                aimag=ub,
                name=d,
                defaults={"code": ""},
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"OK: UB={ub.id}. Newly created districts={created} (total={len(DISTRICTS)})"))
