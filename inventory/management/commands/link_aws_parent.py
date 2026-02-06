from __future__ import annotations

import math
from django.core.management.base import BaseCommand
from django.db import transaction

from inventory.models import Location


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2) + math.cos(p1) * math.cos(p2) * (math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def norm_name(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("\u00A0", " ")
    s = " ".join(s.split())
    # зураасны хэлбэрүүдийг нэгтгэх
    s = s.replace("–", "-").replace("—", "-")
    return s


class Command(BaseCommand):
    help = "Link AWS.parent_location to METEO(WEATHER) in same aimag: prefer exact name match, else nearest-by-distance with threshold."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--max-distance-m", type=float, default=30000.0)     # nearest fallback threshold
        parser.add_argument("--name-max-distance-m", type=float, default=200000.0)  # if name matches, allow up to 200km
        parser.add_argument("--report-top", type=int, default=20)

    def handle(self, *args, **opts):
        dry = bool(opts["dry_run"])
        max_dist = float(opts["max_distance_m"])
        name_max = float(opts["name_max_distance_m"])
        report_top = int(opts["report_top"])

        aws_qs = Location.objects.filter(location_type="AWS").select_related("aimag_ref")
        wx_qs = Location.objects.filter(location_type="WEATHER").select_related("aimag_ref")

        # WEATHER-г aimag-аар бүлэглэж, мөн нэрээр индекс үүсгэнэ
        wx_by_aimag = {}
        wx_name_index = {}  # (aimag_id, norm_name) -> [wx...]
        for w in wx_qs:
            wx_by_aimag.setdefault(w.aimag_ref_id, []).append(w)
            wx_name_index.setdefault((w.aimag_ref_id, norm_name(w.name)), []).append(w)

        linked = 0
        missing_aimag = 0
        skipped_far = 0
        used_name_match = 0
        worst = []  # (dist, aimag, aws_name, wx_name, reason)

        @transaction.atomic
        def run():
            nonlocal linked, missing_aimag, skipped_far, used_name_match, worst

            for a in aws_qs:
                cands = wx_by_aimag.get(a.aimag_ref_id, [])
                if not cands:
                    missing_aimag += 1
                    continue

                # 1) exact-ish name match in same aimag
                nm = norm_name(a.name)
                same_name = wx_name_index.get((a.aimag_ref_id, nm), [])

                if same_name:
                    # if multiple, choose nearest among same-name
                    best = None
                    best_d = None
                    for w in same_name:
                        d = haversine_m(a.latitude, a.longitude, w.latitude, w.longitude)
                        if best is None or d < best_d:
                            best = w
                            best_d = d

                    if best_d is not None and best_d <= name_max:
                        used_name_match += 1
                        worst.append((best_d, a.aimag_ref.name, a.name, best.name, "NAME"))
                        worst.sort(reverse=True)
                        worst[:] = worst[:report_top]

                        if not dry:
                            a.parent_location = best
                            a.save(update_fields=["parent_location"])
                        linked += 1
                        continue
                    # name match байсан ч хэтэрхий хол бол skip
                    skipped_far += 1
                    worst.append((best_d or 0, a.aimag_ref.name, a.name, best.name if best else "-", "NAME_TOO_FAR"))
                    worst.sort(reverse=True)
                    worst[:] = worst[:report_top]
                    continue

                # 2) fallback: nearest in same aimag, threshold = max_dist
                best = None
                best_d = None
                for w in cands:
                    d = haversine_m(a.latitude, a.longitude, w.latitude, w.longitude)
                    if best is None or d < best_d:
                        best = w
                        best_d = d

                if best_d is None or best is None:
                    missing_aimag += 1
                    continue

                if best_d > max_dist:
                    skipped_far += 1
                    worst.append((best_d, a.aimag_ref.name, a.name, best.name, "NEAREST_TOO_FAR"))
                    worst.sort(reverse=True)
                    worst[:] = worst[:report_top]
                    continue

                worst.append((best_d, a.aimag_ref.name, a.name, best.name, "NEAREST"))
                worst.sort(reverse=True)
                worst[:] = worst[:report_top]

                if not dry:
                    a.parent_location = best
                    a.save(update_fields=["parent_location"])
                linked += 1

        run()

        self.stdout.write(self.style.SUCCESS(
            f"mode={'DRY' if dry else 'APPLY'} linked={linked} used_name_match={used_name_match} "
            f"missing_aimag={missing_aimag} skipped_far={skipped_far} "
            f"(nearest_max={max_dist:.0f}m name_max={name_max:.0f}m)"
        ))
        self.stdout.write("Worst distance samples:")
        for d, aimag, aws_name, wx_name, reason in worst:
            self.stdout.write(f"  {d:8.1f} m | {aimag} | AWS '{aws_name}' -> METEO '{wx_name}' [{reason}]")
