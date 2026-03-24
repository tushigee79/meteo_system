# inventory/management/commands/healthcheck_inventory.py
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Check critical inventory schema columns required by admin/dashboard."

    REQUIRED = {
        "inventory_userprofile": {"role"},
        "inventory_device": {"manufacturer"},
    }

    def handle(self, *args, **options):
        missing_total = False

        with connection.cursor() as cursor:
            for table_name, required_columns in self.REQUIRED.items():
                try:
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    rows = cursor.fetchall()
                except Exception as exc:
                    self.stdout.write(self.style.ERROR(f"[ERROR] Could not inspect {table_name}: {exc}"))
                    missing_total = True
                    continue

                existing_columns = {row[1] for row in rows}
                missing_columns = required_columns - existing_columns

                if missing_columns:
                    missing_total = True
                    self.stdout.write(
                        self.style.ERROR(
                            f"[MISSING] {table_name}: {', '.join(sorted(missing_columns))}"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"[OK] {table_name}: all required columns present"
                        )
                    )

        if missing_total:
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("Inventory schema healthcheck passed."))