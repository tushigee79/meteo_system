import csv
import secrets
import string

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group
from django.db import transaction

from inventory.models import Aimag, Organization, UserProfile


def make_temp_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


class Command(BaseCommand):
    help = "Import AimagEngineer users from CSV (username, aimag, email?, org?)"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to CSV file")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do not write to DB (just validate and preview)",
        )

    def handle(self, *args, **opts):
        csv_path = opts["csv_path"]
        dry_run = opts["dry_run"]

        try:
            f = open(csv_path, "r", encoding="utf-8-sig", newline="")
        except OSError as e:
            raise CommandError(f"Cannot open CSV: {e}")

        with f:
            reader = csv.DictReader(f)
            required = {"username", "aimag"}
            if not reader.fieldnames or not required.issubset(set(h.strip() for h in reader.fieldnames)):
                raise CommandError("CSV must include headers: username, aimag (email, org optional)")

            group, _ = Group.objects.get_or_create(name="AimagEngineer")

            created_users = 0
            updated_users = 0
            created_profiles = 0
            updated_profiles = 0
            errors = 0

            rows = list(reader)
            if not rows:
                self.stdout.write(self.style.WARNING("CSV is empty. Nothing to import."))
                return

            def resolve_org(i: int, aimag, aimag_name: str, org_name: str):
                """
                org resolution priority:
                1) CSV org provided and found -> use it
                2) else auto: "<Аймаг> > УЦУОШТ" (create if missing)
                """
                org = None

                if org_name:
                    org = Organization.objects.filter(name=org_name).first()
                    if not org:
                        self.stdout.write(self.style.WARNING(
                            f"[Row {i}] Organization not found (skipped): {org_name}"
                        ))
                        org = None

                if org is None:
                    auto_name = f"{aimag_name} > УЦУОШТ"
                    org, _created = Organization.objects.get_or_create(
                        name=auto_name,
                        defaults={
                            "org_type": "OBS_CENTER",
                            "aimag": aimag,
                            "is_ub": (aimag_name.strip() == "Улаанбаатар"),
                        }
                    )
                return org

            def process():
                nonlocal created_users, updated_users, created_profiles, updated_profiles, errors

                for i, row in enumerate(rows, start=2):  # header=1
                    username = (row.get("username") or "").strip()
                    aimag_name = (row.get("aimag") or "").strip()
                    email = (row.get("email") or "").strip()
                    org_name = (row.get("org") or "").strip()

                    if not username or not aimag_name:
                        errors += 1
                        self.stdout.write(self.style.ERROR(f"[Row {i}] Missing username/aimag"))
                        continue

                    try:
                        aimag = Aimag.objects.get(name=aimag_name)
                    except Aimag.DoesNotExist:
                        errors += 1
                        self.stdout.write(self.style.ERROR(f"[Row {i}] Aimag not found: {aimag_name}"))
                        continue

                    # ✅ org автоматаар оноох
                    org = resolve_org(i=i, aimag=aimag, aimag_name=aimag_name, org_name=org_name)

                    # User create/update
                    user, was_created = User.objects.get_or_create(username=username)
                    if was_created:
                        temp_pass = make_temp_password()
                        user.set_password(temp_pass)
                        created_users += 1
                        self.stdout.write(self.style.SUCCESS(
                            f"[Row {i}] Created user={username} temp_pass={temp_pass}"
                        ))
                    else:
                        updated_users += 1
                        self.stdout.write(f"[Row {i}] Updated user={username}")

                    user.is_staff = True
                    user.is_superuser = False
                    if email:
                        user.email = email
                    user.save()

                    user.groups.add(group)

                    # ✅ Profile create/update
                    profile, p_created = UserProfile.objects.get_or_create(user=user)
                    profile.aimag = aimag
                    if org:
                        profile.org = org

                    # ✅ Аймгийн инженерүүд эхний login дээр заавал password солино
                    profile.must_change_password = True

                    profile.save()

                    if p_created:
                        created_profiles += 1
                    else:
                        updated_profiles += 1

            if dry_run:
                self.stdout.write(self.style.WARNING("DRY RUN (no DB writes)"))
                for i, row in enumerate(rows, start=2):
                    username = (row.get("username") or "").strip()
                    aimag_name = (row.get("aimag") or "").strip()
                    if not username or not aimag_name:
                        self.stdout.write(self.style.ERROR(f"[Row {i}] Missing username/aimag"))
                        continue
                    if not Aimag.objects.filter(name=aimag_name).exists():
                        self.stdout.write(self.style.ERROR(f"[Row {i}] Aimag not found: {aimag_name}"))
                self.stdout.write(self.style.WARNING("Dry run complete."))
                return

            with transaction.atomic():
                process()

            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("DONE"))
            self.stdout.write(f"Users: created={created_users}, updated={updated_users}")
            self.stdout.write(f"Profiles: created={created_profiles}, updated={updated_profiles}")
            self.stdout.write(f"Errors: {errors}")
