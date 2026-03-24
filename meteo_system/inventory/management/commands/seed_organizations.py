from django.core.management.base import BaseCommand
from inventory.models import Aimag, Organization

class Command(BaseCommand):
    help = "Seed default organizations: 21 aimag UCUOSHT + UB UCUOSHT + BOHZTL + NCUT"

    def handle(self, *args, **kwargs):
        aimag_names = [
            "Архангай","Баян-Өлгий","Баянхонгор","Булган","Говь-Алтай","Говьсүмбэр",
            "Дархан-Уул","Дорноговь","Дорнод","Дундговь","Завхан","Орхон","Өвөрхангай",
            "Өмнөговь","Сүхбаатар","Сэлэнгэ","Төв","Увс","Ховд","Хөвсгөл","Хэнтий",
            "Улаанбаатар",
        ]

        # 1) Aimag үүсгэнэ (байхгүй бол)
        aimag_map = {}
        for n in aimag_names:
            a, _ = Aimag.objects.get_or_create(name=n)
            aimag_map[n] = a

        # 2) 21 аймгийн УЦУОШТ (УБ-гүй)
        for n in aimag_names:
            if n == "Улаанбаатар":
                continue
            Organization.objects.get_or_create(
                name=f"{n} аймгийн УЦУОШТ",
                defaults={
                    "org_type": "OBS_CENTER",
                    "aimag": aimag_map[n],
                    "is_ub": False,
                }
            )

        # 3) Улаанбаатар хотын УЦУОШТ
        Organization.objects.get_or_create(
            name="Улаанбаатар хотын УЦУОШТ",
            defaults={
                "org_type": "OBS_CENTER",
                "aimag": aimag_map["Улаанбаатар"],
                "is_ub": True,
            }
        )

        # 4) БОХЗТЛ
        Organization.objects.get_or_create(
            name="БОХЗТЛ",
            defaults={
                "org_type": "CAL_LAB",
                "aimag": None,
                "is_ub": True,  # хүсвэл True хэвээр үлдээнэ
            }
        )

        # 5) НЦУТ
        Organization.objects.get_or_create(
            name="НЦУТ",
            defaults={
                "org_type": "CENTER",
                "aimag": None,
                "is_ub": True,  # хүсвэл True хэвээр үлдээнэ
            }
        )

        self.stdout.write(self.style.SUCCESS("✅ Байгууллагууд seed амжилттай!"))
