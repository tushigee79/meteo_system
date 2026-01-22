import re
from django.core.management.base import BaseCommand
from django.db import transaction
from inventory.models import Organization, Aimag, Location, UserProfile

def canon_name(aimag_name: str) -> str:
    return f"{aimag_name} УЦУОШТ"

def looks_like_ucuosht(name: str) -> bool:
    t = (name or "").lower()
    return "уцоуошт" in t

class Command(BaseCommand):
    help = "Merge duplicated UCUOSHT organizations into canonical '{aimag} УЦУОШТ'"

    @transaction.atomic
    def handle(self, *args, **opts):
        merged = 0

        for aimag in Aimag.objects.all():
            # тухайн аймаг дээрх уцоуошт маягийн бүх organization
            orgs = Organization.objects.filter(aimag=aimag).filter(name__icontains="УЦУОШТ")
            if orgs.count() <= 1:
                continue

            target_name = canon_name(aimag.name)
            target, _ = Organization.objects.get_or_create(
                name=target_name,
                defaults={"org_type": "OBS_CENTER", "aimag": aimag, "is_ub": ("улаанбаатар" in aimag.name.lower())}
            )

            for o in orgs:
                if o.id == target.id:
                    continue

                # FK-уудыг target руу шилжүүлнэ
                Location.objects.filter(owner_org=o).update(owner_org=target)
                UserProfile.objects.filter(org=o).update(org=target)

                o.delete()
                merged += 1

        self.stdout.write(self.style.SUCCESS(f"Merged organizations: {merged}"))
