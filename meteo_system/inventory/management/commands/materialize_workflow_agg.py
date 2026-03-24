from __future__ import annotations

from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, DurationField, ExpressionWrapper, F, Avg, Q
from django.utils import timezone

from inventory.models import (
    WorkflowDailyAgg,
    MaintenanceService,
    ControlAdjustment,
    WorkflowStatus,
    Aimag,
)


class Command(BaseCommand):
    help = "Materialize workflow daily aggregations into WorkflowDailyAgg (for heavy data)."

    def add_arguments(self, parser):
        parser.add_argument("--from", dest="date_from", default="", help="Start date YYYY-MM-DD (inclusive).")
        parser.add_argument("--to", dest="date_to", default="", help="End date YYYY-MM-DD (inclusive).")
        parser.add_argument("--days", dest="days", type=int, default=90, help="If from/to not given, last N days (default 90).")

    def handle(self, *args, **opts):
        df = opts.get("date_from") or ""
        dt = opts.get("date_to") or ""
        days = int(opts.get("days") or 90)

        if df:
            start = date.fromisoformat(df)
        else:
            start = timezone.localdate() - timedelta(days=days)

        if dt:
            end = date.fromisoformat(dt)
        else:
            end = timezone.localdate()

        if start > end:
            start, end = end, start

        self.stdout.write(self.style.NOTICE(f"Materializing workflow stats: {start} → {end}"))

        cur = start
        total = 0
        with transaction.atomic():
            while cur <= end:
                total += self._materialize_day(cur)
                cur += timedelta(days=1)

        self.stdout.write(self.style.SUCCESS(f"Done. Upserted rows: {total}"))

    def _materialize_day(self, day: date) -> int:
        ms = MaintenanceService.objects.filter(date=day)
        ca = ControlAdjustment.objects.filter(date=day)

        # Group by aimag (Location.aimag_ref)
        rows = []

        # We'll materialize: for each aimag and global total row (aimag=None)
        aimag_ids = list(
            set(
                ms.values_list("device__location__aimag_ref_id", flat=True)
                .exclude(device__location__aimag_ref_id__isnull=True)
            )
            | set(
                ca.values_list("device__location__aimag_ref_id", flat=True)
                .exclude(device__location__aimag_ref_id__isnull=True)
            )
        )

        targets = [None] + aimag_ids

        for aid in targets:
            ms_q = ms
            ca_q = ca
            if aid is not None:
                ms_q = ms_q.filter(device__location__aimag_ref_id=aid)
                ca_q = ca_q.filter(device__location__aimag_ref_id=aid)

            # counts
            def c(q, st): return q.filter(workflow_status=st).count()

            ms_sub = c(ms_q, WorkflowStatus.SUBMITTED)
            ms_app = c(ms_q, WorkflowStatus.APPROVED)
            ms_rej = c(ms_q, WorkflowStatus.REJECTED)
            ca_sub = c(ca_q, WorkflowStatus.SUBMITTED)
            ca_app = c(ca_q, WorkflowStatus.APPROVED)
            ca_rej = c(ca_q, WorkflowStatus.REJECTED)

            # SLA avg hours (approved only)
            dur = ExpressionWrapper(F("approved_at") - F("submitted_at"), output_field=DurationField())
            ms_sla = ms_q.filter(workflow_status=WorkflowStatus.APPROVED).exclude(approved_at__isnull=True).exclude(submitted_at__isnull=True).aggregate(avg=Avg(dur))["avg"]
            ca_sla = ca_q.filter(workflow_status=WorkflowStatus.APPROVED).exclude(approved_at__isnull=True).exclude(submitted_at__isnull=True).aggregate(avg=Avg(dur))["avg"]
            # merge (simple average of available)
            vals = []
            for v in (ms_sla, ca_sla):
                if v is not None:
                    vals.append(v.total_seconds() / 3600.0)
            sla_avg_hours = float(sum(vals) / len(vals)) if vals else 0.0

            obj, created = WorkflowDailyAgg.objects.update_or_create(
                day=day,
                aimag_id=aid,
                kind="",
                location_type="",
                defaults=dict(
                    ms_submitted=ms_sub,
                    ms_approved=ms_app,
                    ms_rejected=ms_rej,
                    ca_submitted=ca_sub,
                    ca_approved=ca_app,
                    ca_rejected=ca_rej,
                    sla_avg_hours=round(sla_avg_hours, 2),
                ),
            )
            rows.append(obj)

        return len(rows)
