# inventory/views_admin_workflow.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import ControlAdjustment, MaintenanceService

# ------------------------------------------------------------
# Safe imports (reports_hub vs reports_hub_compat)
# ------------------------------------------------------------
try:
    # new/compat style
    from .reports_hub_compat import _get_user_aimag, _has_field, _admin_url  # type: ignore
except Exception:  # pragma: no cover
    # legacy style
    from .reports_hub import _get_user_aimag, _has_field, _admin_url  # type: ignore


# ============================================================
# Pending workflow row
# ============================================================
@dataclass
class WorkflowRow:
    kind: str                 # "MAINT" | "CONTROL"
    status: str               # workflow_status
    created_at: Any           # datetime/date
    device_label: str
    device_id: Optional[int]
    device_url: str
    record_id: int            # MaintenanceService.id / ControlAdjustment.id
    record_url: str
    location_label: str
    location_url: str
    aimag: str
    org: str


# ============================================================
# Pending dashboard page (HTML + AJAX JSON)
# ============================================================
@staff_member_required
def workflow_pending_dashboard(request: HttpRequest) -> HttpResponse:
    status = (request.GET.get("status") or "").strip().upper()
    kind = (request.GET.get("kind") or "").strip().upper()
    aimag = (request.GET.get("aimag") or "").strip()
    org = (request.GET.get("org") or "").strip()
    days = (request.GET.get("days") or "").strip()

    PENDING_SET = ["PENDING", "NEED_APPROVAL"]
    base_statuses = PENDING_SET if not status else [status]

    user_aimag = _get_user_aimag(request)
    is_aimag_engineer = request.user.groups.filter(name="AimagEngineer").exists()

    ms_qs = (
        MaintenanceService.objects.select_related(
            "device",
            "device__location",
            "device__location__aimag_ref",
            "device__location__owner_org",
        )
        .filter(workflow_status__in=base_statuses)
    )

    ca_qs = (
        ControlAdjustment.objects.select_related(
            "device",
            "device__location",
            "device__location__aimag_ref",
            "device__location__owner_org",
        )
        .filter(workflow_status__in=base_statuses)
    )

    # Days filter
    if days.isdigit():
        dt = timezone.now() - timezone.timedelta(days=int(days))
        if _has_field(MaintenanceService, "created_at"):
            ms_qs = ms_qs.filter(created_at__gte=dt)
        else:
            ms_qs = ms_qs.filter(date__gte=dt.date())

        if _has_field(ControlAdjustment, "created_at"):
            ca_qs = ca_qs.filter(created_at__gte=dt)
        else:
            ca_qs = ca_qs.filter(date__gte=dt.date())

    # Aimag scope
    if is_aimag_engineer and user_aimag:
        ms_qs = ms_qs.filter(device__location__aimag_ref=user_aimag)
        ca_qs = ca_qs.filter(device__location__aimag_ref=user_aimag)
    elif aimag:
        aimag_q = (
            Q(device__location__aimag_ref__code__iexact=aimag)
            | Q(device__location__aimag_ref__name__iexact=aimag)
            | Q(device__location__aimag_ref__name__icontains=aimag)
        )
        ms_qs = ms_qs.filter(aimag_q)
        ca_qs = ca_qs.filter(aimag_q)

    # Org filter
    if org:
        org_q = (
            Q(device__location__owner_org__name__icontains=org)
            | Q(device__location__org__name__icontains=org)
        )
        ms_qs = ms_qs.filter(org_q)
        ca_qs = ca_qs.filter(org_q)

    ms_order = "-created_at" if _has_field(MaintenanceService, "created_at") else "-date"
    ca_order = "-created_at" if _has_field(ControlAdjustment, "created_at") else "-date"

    rows: List[WorkflowRow] = []

    if kind in ("", "MAINT"):
        for r in ms_qs.order_by(ms_order, "-id")[:1500]:
            d = getattr(r, "device", None)
            loc = getattr(d, "location", None)
            created = getattr(r, "created_at", None) or getattr(r, "date", None)

            rows.append(
                WorkflowRow(
                    kind="MAINT",
                    status=str(r.workflow_status).upper(),
                    created_at=created,
                    device_label=str(d) if d else "",
                    device_id=getattr(d, "id", None),
                    device_url=_admin_url("inventory", "device", d.id) if d else "#",
                    record_id=int(r.id),
                    record_url=_admin_url("inventory", "maintenanceservice", r.id),
                    location_label=str(loc) if loc else "",
                    location_url=_admin_url("inventory", "location", loc.id) if loc else "#",
                    aimag=str(getattr(loc, "aimag_ref", "-")),
                    org=str(getattr(loc, "owner_org", "-")),
                )
            )

    if kind in ("", "CONTROL"):
        for r in ca_qs.order_by(ca_order, "-id")[:1500]:
            d = getattr(r, "device", None)
            loc = getattr(d, "location", None)
            created = getattr(r, "created_at", None) or getattr(r, "date", None)

            rows.append(
                WorkflowRow(
                    kind="CONTROL",
                    status=str(r.workflow_status).upper(),
                    created_at=created,
                    device_label=str(d) if d else "",
                    device_id=getattr(d, "id", None),
                    device_url=_admin_url("inventory", "device", d.id) if d else "#",
                    record_id=int(r.id),
                    record_url=_admin_url("inventory", "controladjustment", r.id),
                    location_label=str(loc) if loc else "",
                    location_url=_admin_url("inventory", "location", loc.id) if loc else "#",
                    aimag=str(getattr(loc, "aimag_ref", "-")),
                    org=str(getattr(loc, "owner_org", "-")),
                )
            )

    tz = timezone.get_current_timezone()
    min_dt = timezone.datetime.min.replace(tzinfo=tz)
    rows.sort(key=lambda x: (x.created_at or min_dt), reverse=True)

    # AJAX JSON (template чинь "&ajax=1" явуулдаг)
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("ajax") == "1":
        return JsonResponse(
            {
                "ok": True,
                "rows": [
                    {
                        "kind": r.kind,
                        "status": r.status,
                        "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if hasattr(r.created_at, "strftime") else (str(r.created_at) if r.created_at else ""),
                        "device_label": r.device_label,
                        "device_url": r.device_url,
                        "record_id": r.record_id,
                        "record_url": r.record_url,
                        "location_label": r.location_label,
                        "location_url": r.location_url,
                        "aimag": r.aimag,
                        "org": r.org,
                    }
                    for r in rows[:2000]
                ],
            }
        )

    ctx = {
        "title": "Хүлээгдэж буй ажлууд",
        "rows": rows[:2000],
        "filters": {"status": status, "kind": kind, "aimag": aimag, "org": org, "days": days},
        "pending_statuses": PENDING_SET,
        "is_aimag_engineer": is_aimag_engineer,
    }
    return render(request, "admin/inventory/workflow_pending.html", ctx)


# ============================================================
# Pending counts (legacy polling)
# ============================================================
@staff_member_required
def workflow_pending_counts(request: HttpRequest) -> JsonResponse:
    PENDING_SET = ["PENDING", "NEED_APPROVAL"]

    user_aimag = _get_user_aimag(request)
    is_aimag_engineer = request.user.groups.filter(name="AimagEngineer").exists()

    ms_qs = MaintenanceService.objects.filter(workflow_status__in=PENDING_SET)
    ca_qs = ControlAdjustment.objects.filter(workflow_status__in=PENDING_SET)

    if is_aimag_engineer and user_aimag:
        ms_qs = ms_qs.filter(device__location__aimag_ref=user_aimag)
        ca_qs = ca_qs.filter(device__location__aimag_ref=user_aimag)

    return JsonResponse(
        {
            "ok": True,
            "pending_maint": ms_qs.count(),
            "pending_control": ca_qs.count(),
            "pending_total": ms_qs.count() + ca_qs.count(),
        }
    )


# ============================================================
# Review action (approve/reject)
# ============================================================
@staff_member_required
@require_POST
def workflow_review_action(request: HttpRequest) -> JsonResponse:
    kind = (request.POST.get("kind") or "").upper().strip()
    rid = (request.POST.get("id") or "").strip()
    action = (request.POST.get("action") or "").lower().strip()
    reason = (request.POST.get("reason") or "").strip()

    if kind not in ("MAINT", "CONTROL") or not rid.isdigit() or action not in ("approve", "reject"):
        return JsonResponse({"ok": False, "error": "Invalid params"}, status=400)

    if not (request.user.is_superuser or request.user.groups.filter(name="WorkflowReviewer").exists()):
        return JsonResponse({"ok": False, "error": "No permission"}, status=403)

    Model = MaintenanceService if kind == "MAINT" else ControlAdjustment
    obj = get_object_or_404(Model, pk=int(rid))

    if action == "approve":
        obj.workflow_status = "APPROVED"
    else:
        if not reason:
            return JsonResponse({"ok": False, "error": "Reason required"}, status=400)
        obj.workflow_status = "REJECTED"
        if hasattr(obj, "reject_reason"):
            obj.reject_reason = reason

    obj.save()
    return JsonResponse({"ok": True, "kind": kind, "id": obj.id, "status": str(obj.workflow_status)})


# ============================================================
# Audit page (simple: list MAINT/CONTROL history)
# NOTE: Таны upload хийсэн workflow_audit.html нь logs гэж хүлээж байна.
# Энэ view одоохондоо rows өгнө (pending-аас өөр зориулалттай).
# ============================================================
@staff_member_required
@require_GET
def workflow_audit_log(request: HttpRequest) -> HttpResponse:
    q = (request.GET.get("q") or "").strip()
    days = (request.GET.get("days") or "").strip()
    kind = (request.GET.get("kind") or "").upper()
    status = (request.GET.get("status") or "").upper()

    dt_from = timezone.now() - timezone.timedelta(days=int(days)) if days.isdigit() else None

    ms_qs = MaintenanceService.objects.select_related("device", "device__location")
    ca_qs = ControlAdjustment.objects.select_related("device", "device__location")

    is_aimag_engineer = request.user.groups.filter(name="AimagEngineer").exists()
    if is_aimag_engineer:
        user_aimag = _get_user_aimag(request)
        if user_aimag:
            ms_qs = ms_qs.filter(device__location__aimag_ref=user_aimag)
            ca_qs = ca_qs.filter(device__location__aimag_ref=user_aimag)

    if dt_from:
        if _has_field(MaintenanceService, "created_at"):
            ms_qs = ms_qs.filter(created_at__gte=dt_from)
        else:
            ms_qs = ms_qs.filter(date__gte=dt_from)
        if _has_field(ControlAdjustment, "created_at"):
            ca_qs = ca_qs.filter(created_at__gte=dt_from)
        else:
            ca_qs = ca_qs.filter(date__gte=dt_from)

    if status:
        ms_qs = ms_qs.filter(workflow_status__iexact=status)
        ca_qs = ca_qs.filter(workflow_status__iexact=status)

    if q:
        ms_qs = ms_qs.filter(Q(note__icontains=q))
        ca_qs = ca_qs.filter(Q(note__icontains=q))

    ms_order = "-created_at" if _has_field(MaintenanceService, "created_at") else "-date"
    ca_order = "-created_at" if _has_field(ControlAdjustment, "created_at") else "-date"

    rows: List[dict] = []

    if kind in ("", "MAINT"):
        for o in ms_qs.order_by(ms_order, "-id")[:1500]:
            when = getattr(o, "created_at", None) or getattr(o, "date", None)
            rows.append(
                {
                    "kind": "MAINT",
                    "when": when.strftime("%Y-%m-%d %H:%M") if hasattr(when, "strftime") else (str(when) if when else ""),
                    "status": str(o.workflow_status).upper(),
                    "device": str(o.device),
                    "record_url": _admin_url("inventory", "maintenanceservice", o.id),
                }
            )

    if kind in ("", "CONTROL"):
        for o in ca_qs.order_by(ca_order, "-id")[:1500]:
            when = getattr(o, "created_at", None) or getattr(o, "date", None)
            rows.append(
                {
                    "kind": "CONTROL",
                    "when": when.strftime("%Y-%m-%d %H:%M") if hasattr(when, "strftime") else (str(when) if when else ""),
                    "status": str(o.workflow_status).upper(),
                    "device": str(o.device),
                    "record_url": _admin_url("inventory", "controladjustment", o.id),
                }
            )

    # sort
    rows.sort(key=lambda r: r.get("when") or "", reverse=True)

    return render(
        request,
        "admin/inventory/workflow_audit.html",
        {
            "title": "Workflow Audit",
            "rows": rows[:3000],
            "filters": {"q": q, "days": days, "kind": kind, "status": status},
        },
    )


# ------------------------------------------------------------
# Aliases for admin.py compatibility
# admin.py дээр wf.workflow_pending / wf.workflow_audit гэж дуудахад унахгүй болгоно
# ------------------------------------------------------------
workflow_pending = workflow_pending_dashboard
workflow_audit = workflow_audit_log
