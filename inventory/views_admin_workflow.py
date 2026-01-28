# inventory/views_admin_workflow.py
from dataclasses import dataclass
from typing import List, Optional, Any

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import MaintenanceService, ControlAdjustment

ADMIN_PREFIX = "/django-admin"  # танайд admin зам энэ


@dataclass
class WorkflowRow:
    kind: str  # "MAINT" | "CONTROL"
    status: str
    created_at: Any
    device_label: str
    device_id: Optional[int]
    device_url: str
    record_url: str
    location_label: str
    location_url: str
    aimag: str
    org: str


def _get_user_aimag(request):
    # UserProfile дээр aimag FK байдаг
    prof = getattr(request.user, "userprofile", None)
    return getattr(prof, "aimag", None)


def _admin_url(app_label: str, model_name: str, obj_id: int) -> str:
    return f"{ADMIN_PREFIX}/{app_label}/{model_name}/{obj_id}/change/"


@staff_member_required
def workflow_pending_dashboard(request):
    # -------------------------
    # Filters (GET params)
    # -------------------------
    status = (request.GET.get("status") or "").strip()
    kind = (request.GET.get("kind") or "").strip().upper()  # MAINT / CONTROL
    aimag = (request.GET.get("aimag") or "").strip()
    org = (request.GET.get("org") or "").strip()
    days = (request.GET.get("days") or "").strip()  # e.g. 7, 30

    PENDING_SET = ["PENDING", "NEED_APPROVAL"]
    base_statuses = PENDING_SET if not status else [status]

    # -------------------------
    # Role-based scoping
    # -------------------------
    user_aimag = _get_user_aimag(request)
    is_aimag_engineer = request.user.groups.filter(name="AimagEngineer").exists()

    # -------------------------
    # Querysets
    # NOTE: Location дээр танайд aimag_ref / sum_ref гэж байна
    # -------------------------
    ms_qs = MaintenanceService.objects.select_related(
        "device",
        "device__location",
        "device__location__aimag_ref",
        "device__location__owner_org",
    )
    ca_qs = ControlAdjustment.objects.select_related(
        "device",
        "device__location",
        "device__location__aimag_ref",
        "device__location__owner_org",
    )

    ms_qs = ms_qs.filter(workflow_status__in=base_statuses)
    ca_qs = ca_qs.filter(workflow_status__in=base_statuses)

    if days.isdigit():
        dt = timezone.now() - timezone.timedelta(days=int(days))
        ms_qs = ms_qs.filter(created_at__gte=dt)
        ca_qs = ca_qs.filter(created_at__gte=dt)

    # aimag filter
    if is_aimag_engineer and user_aimag:
        ms_qs = ms_qs.filter(device__location__aimag_ref=user_aimag)
        ca_qs = ca_qs.filter(device__location__aimag_ref=user_aimag)
    elif aimag:
        # aimag: code эсвэл нэрээр хайна (аль талбар байгаагаас хамаарч)
        aimag_q = (
            Q(device__location__aimag_ref__code__iexact=aimag)
            | Q(device__location__aimag_ref__name__iexact=aimag)
            | Q(device__location__aimag_ref__name__icontains=aimag)
        )
        ms_qs = ms_qs.filter(aimag_q)
        ca_qs = ca_qs.filter(aimag_q)

    # org filter (org / owner_org алиныг нь хэрэглэж байгаагаас үл хамааруулж)
    if org:
        org_q = (
            Q(device__location__owner_org__name__icontains=org)
            | Q(device__location__org__name__icontains=org)
        )
        ms_qs = ms_qs.filter(org_q)
        ca_qs = ca_qs.filter(org_q)

    rows: List[WorkflowRow] = []

    def _safe(obj, attr, default=""):
        try:
            v = getattr(obj, attr)
            return default if v is None else v
        except Exception:
            return default

    if kind in ("", "MAINT"):
        for r in ms_qs.order_by("-created_at")[:2000]:
            d = getattr(r, "device", None)
            loc = getattr(d, "location", None) if d else None
            aim = getattr(loc, "aimag_ref", None) if loc else None
            org_obj = getattr(loc, "owner_org", None) if loc else None
            if not org_obj and loc:
                org_obj = getattr(loc, "org", None)

            rows.append(
                WorkflowRow(
                    kind="MAINT",
                    status=str(_safe(r, "workflow_status", "")),
                    created_at=_safe(r, "created_at", ""),
                    device_label=str(d) if d else "-",
                    device_id=_safe(d, "id", None),
                    device_url=_admin_url("inventory", "device", d.id) if d else "#",
                    record_url=_admin_url("inventory", "maintenanceservice", r.id),
                    location_label=str(loc) if loc else "-",
                    location_url=_admin_url("inventory", "location", loc.id) if loc else "#",
                    aimag=str(aim) if aim else "-",
                    org=str(org_obj) if org_obj else "-",
                )
            )

    if kind in ("", "CONTROL"):
        for r in ca_qs.order_by("-created_at")[:2000]:
            d = getattr(r, "device", None)
            loc = getattr(d, "location", None) if d else None
            aim = getattr(loc, "aimag_ref", None) if loc else None
            org_obj = getattr(loc, "owner_org", None) if loc else None
            if not org_obj and loc:
                org_obj = getattr(loc, "org", None)

            rows.append(
                WorkflowRow(
                    kind="CONTROL",
                    status=str(_safe(r, "workflow_status", "")),
                    created_at=_safe(r, "created_at", ""),
                    device_label=str(d) if d else "-",
                    device_id=_safe(d, "id", None),
                    device_url=_admin_url("inventory", "device", d.id) if d else "#",
                    record_url=_admin_url("inventory", "controladjustment", r.id),
                    location_label=str(loc) if loc else "-",
                    location_url=_admin_url("inventory", "location", loc.id) if loc else "#",
                    aimag=str(aim) if aim else "-",
                    org=str(org_obj) if org_obj else "-",
                )
            )

    rows.sort(key=lambda x: (x.created_at or timezone.datetime.min), reverse=True)

    ctx = {
        "title": "Pending Workflow",
        "rows": rows[:5000],
        "filters": {"status": status, "kind": kind, "aimag": aimag, "org": org, "days": days},
        "pending_statuses": PENDING_SET,
        "is_aimag_engineer": is_aimag_engineer,
    }
    return render(request, "admin/inventory/workflow_pending.html", ctx)


@staff_member_required
def workflow_pending_counts(request):
    PENDING_SET = ["PENDING", "NEED_APPROVAL"]

    user_aimag = _get_user_aimag(request)
    is_aimag_engineer = request.user.groups.filter(name="AimagEngineer").exists()

    ms_qs = MaintenanceService.objects.filter(workflow_status__in=PENDING_SET)
    ca_qs = ControlAdjustment.objects.filter(workflow_status__in=PENDING_SET)

    if is_aimag_engineer and user_aimag:
        ms_qs = ms_qs.filter(device__location__aimag_ref=user_aimag)
        ca_qs = ca_qs.filter(device__location__aimag_ref=user_aimag)

    pending_maint = ms_qs.count()
    pending_control = ca_qs.count()

    return JsonResponse(
        {
            "ok": True,
            "pending_total": pending_maint + pending_control,
            "pending_maint": pending_maint,
            "pending_control": pending_control,
        }
    )


@staff_member_required
@require_POST
def workflow_review_action(request):
    kind = (request.POST.get("kind") or "").upper().strip()
    rid = (request.POST.get("id") or "").strip()
    action = (request.POST.get("action") or "").lower().strip()
    reason = (request.POST.get("reason") or "").strip()

    if kind not in ("MAINT", "CONTROL"):
        return JsonResponse({"ok": False, "error": "Invalid kind"}, status=400)
    if not rid.isdigit():
        return JsonResponse({"ok": False, "error": "Invalid id"}, status=400)
    if action not in ("approve", "reject"):
        return JsonResponse({"ok": False, "error": "Invalid action"}, status=400)

    # approve/reject эрх: superuser эсвэл WorkflowReviewer group
    if not (request.user.is_superuser or request.user.groups.filter(name="WorkflowReviewer").exists()):
        return JsonResponse({"ok": False, "error": "No permission"}, status=403)

    Model = MaintenanceService if kind == "MAINT" else ControlAdjustment
    obj = get_object_or_404(Model, pk=int(rid))
    now = timezone.now()

    if getattr(obj, "workflow_status", "") not in ("PENDING", "NEED_APPROVAL", "SUBMITTED"):
        return JsonResponse({"ok": False, "error": f"Not pending: {obj.workflow_status}"}, status=400)

    if action == "approve":
        obj.workflow_status = "APPROVED"
        if hasattr(obj, "approved_at"):
            obj.approved_at = now
        if hasattr(obj, "approved_by"):
            obj.approved_by = request.user
        if hasattr(obj, "rejected_at"):
            obj.rejected_at = None
        if hasattr(obj, "rejected_by"):
            obj.rejected_by = None
        if hasattr(obj, "reject_reason"):
            obj.reject_reason = ""
    else:
        if hasattr(obj, "reject_reason") and not reason:
            return JsonResponse({"ok": False, "error": "Reject reason required"}, status=400)

        obj.workflow_status = "REJECTED"
        if hasattr(obj, "rejected_at"):
            obj.rejected_at = now
        if hasattr(obj, "rejected_by"):
            obj.rejected_by = request.user
        if hasattr(obj, "reject_reason"):
            obj.reject_reason = reason
        if hasattr(obj, "approved_at"):
            obj.approved_at = None
        if hasattr(obj, "approved_by"):
            obj.approved_by = None

    obj.save()
    return JsonResponse({"ok": True, "kind": kind, "id": obj.id, "status": getattr(obj, "workflow_status", "")})
