import logging
from typing import Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from django.urls import reverse

from .models import Device, Location, MaintenanceService, ControlAdjustment, AuthAuditLog

# 1. Мэдээллийн бүтэц (Алдаанаас сэргийлнэ)
@dataclass
class WorkflowRow:
    kind: str
    status: str
    created_at: Any
    device_label: str
    device_id: Optional[int]
    device_url: str
    record_id: int
    record_url: str
    location_label: str
    location_url: str
    aimag: str
    org: str

# 2. Туслах функцүүд
def _admin_url(app_label: str, model_name: str, pk: Any) -> str:
    try:
        return reverse(f"admin:{app_label}_{model_name}_change", args=[pk])
    except:
        return "#"

def _get_user_aimag(user) -> Optional[object]:
    if not user or user.is_anonymous: return None
    prof = getattr(user, "userprofile", None) or getattr(user, "profile", None)
    return getattr(prof, "aimag", None) if prof else None

# 3. Үндсэн Dashboard View
@staff_member_required
def workflow_pending_dashboard(request: HttpRequest) -> HttpResponse:
    status = (request.GET.get("status") or "").strip().upper()
    kind = (request.GET.get("kind") or "").strip().upper()
    
    PENDING_SET = ["SUBMITTED", "PENDING", "NEED_APPROVAL"]
    base_statuses = [status] if status else PENDING_SET

    # Өгөгдөл авах
    ms_qs = MaintenanceService.objects.select_related("device", "device__location__aimag_ref").filter(workflow_status__in=base_statuses)
    ca_qs = ControlAdjustment.objects.select_related("device", "device__location__aimag_ref").filter(workflow_status__in=base_statuses)

    rows: List[WorkflowRow] = []

    # Maintenance rows
    if kind in ("", "MAINT"):
        for r in ms_qs.order_by("-id")[:500]:
            d = r.device
            loc = d.location if d else None
            rows.append(WorkflowRow(
                kind="MAINT", status=str(r.workflow_status).upper(), 
                created_at=getattr(r, "created_at", None) or getattr(r, "date", None),
                device_label=str(d), device_id=d.id if d else None,
                device_url=_admin_url("inventory", "device", d.id) if d else "#",
                record_id=r.id, record_url=_admin_url("inventory", "maintenanceservice", r.id),
                location_label=str(loc) if loc else "", location_url=_admin_url("inventory", "location", loc.id) if loc else "#",
                aimag=str(getattr(loc, "aimag_ref", "-")), org=str(getattr(loc, "owner_org", "-"))
            ))

    # Control rows
    if kind in ("", "CONTROL"):
        for r in ca_qs.order_by("-id")[:500]:
            d = r.device
            loc = d.location if d else None
            rows.append(WorkflowRow(
                kind="CONTROL", status=str(r.workflow_status).upper(), 
                created_at=getattr(r, "created_at", None) or getattr(r, "date", None),
                device_label=str(d), device_id=d.id if d else None,
                device_url=_admin_url("inventory", "device", d.id) if d else "#",
                record_id=r.id, record_url=_admin_url("inventory", "controladjustment", r.id),
                location_label=str(loc) if loc else "", location_url=_admin_url("inventory", "location", loc.id) if loc else "#",
                aimag=str(getattr(loc, "aimag_ref", "-")), org=str(getattr(loc, "-"))
            ))

    # AJAX Response
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("ajax") == "1":
        data = [{
            "kind": r.kind, "status": r.status, "device_label": r.device_label,
            "record_url": r.record_url, "aimag": r.aimag
        } for r in rows]
        return JsonResponse({"ok": True, "rows": data})

    # ✅ ЗААВАЛ RETURN ХИЙХ ХЭСЭГ (HTML)
    context = {
        "title": "Хүлээгдэж буй ажлууд",
        "rows": rows,
        "pending_statuses": PENDING_SET,
        "filters": {"status": status, "kind": kind}
    }
    return render(request, "inventory/admin/workflow_pending.html", context)

# 4. Review & Audit Views
@staff_member_required
@require_POST
def workflow_review_action(request: HttpRequest) -> JsonResponse:
    kind = request.POST.get("kind", "").upper()
    rid = request.POST.get("id")
    action = request.POST.get("action", "").lower()
    
    Model = MaintenanceService if kind == "MAINT" else ControlAdjustment
    obj = get_object_or_404(Model, pk=rid)
    obj.workflow_status = "APPROVED" if action == "approve" else "REJECTED"
    obj.save()
    return JsonResponse({"ok": True})

@staff_member_required
def workflow_audit_log(request: HttpRequest) -> HttpResponse:
    logs = AuthAuditLog.objects.all().order_by("-created_at")[:100]
    return render(request, "inventory/admin/workflow_audit.html", {"logs": logs})

@staff_member_required
def workflow_pending_counts(request: HttpRequest) -> JsonResponse:
    m = MaintenanceService.objects.filter(workflow_status__in=["PENDING", "NEED_APPROVAL"]).count()
    c = ControlAdjustment.objects.filter(workflow_status__in=["PENDING", "NEED_APPROVAL"]).count()
    return JsonResponse({"pending_total": m + c, "ok": True})