import csv
from django.core.management.base import BaseCommand
from django.db import transaction
from inventory.models import Aimag, SumDuureg


def norm(s: str) -> str:
    return (s or "").strip().lower().replace("\ufeff", "")


# ✅ "sum_name"-г нэмлээ
AIMAG_KEYS = {"aimag", "аймаг", "aimag_name", "province"}
SUM_KEYS = {
    "sum", "сум", "sum_name",          # ✅ энд нэмсэн
    "duureg", "дүүрэг",
    "sumduureg", "soum", "district"
}


class Command(BaseCommand):
    help = "Import Mongolia admin units from CSV (aimag,sum) - flexible header & delimiter"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str)

    def handle(self, *args, **opts):
        path = opts["csv_file"]

        created_aimag = 0
        created_sum = 0

        with open(path, "r", encoding="utf-8-sig", newline="") as f, transaction.atomic():
            # delimiter автоматаар таах
            sample = f.read(4096)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t"])
            reader = csv.DictReader(f, dialect=dialect)

            # header-уудыг normalize хийж map үүсгэнэ
            field_map = {norm(k): k for k in (reader.fieldnames or [])}

            aimag_col = None
            sum_col = None

            for k in AIMAG_KEYS:
                if k in field_map:
                    aimag_col = field_map[k]
                    break

            for k in SUM_KEYS:
                if k in field_map:
                    sum_col = field_map[k]
                    break

            if not aimag_col or not sum_col:
                raise SystemExit(
                    "CSV header танигдсангүй.\n"
                    f"Олдсон header-ууд: {reader.fieldnames}\n"
                    "Шаардлагатай нь: aimag/Аймаг ба sum/Сум (эсвэл sum_name) төрлийн багана."
                )

            for row in reader:
                aimag_name = (row.get(aimag_col) or "").strip()
                sum_name = (row.get(sum_col) or "").strip()

                # ✅ таслалын өмнө/дараах зай, давхар space цэвэрлэх
                aimag_name = " ".join(aimag_name.split())
                sum_name = " ".join(sum_name.split())

                if not aimag_name or not sum_name:
                    continue

                aimag, a_created = Aimag.objects.get_or_create(name=aimag_name)
                if a_created:
                    created_aimag += 1

                _, s_created = SumDuureg.objects.get_or_create(
                    name=sum_name,
                    aimag=aimag
                )
                if s_created:
                    created_sum += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Created aimag={created_aimag}, sum/duureg={created_sum}"
        ))
