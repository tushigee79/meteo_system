# inventory/reports_hub_compat.py
from django.shortcuts import render
from django.http import JsonResponse
from django.urls import reverse
from .models import MaintenanceService, ControlAdjustment

def workflow_pending_dashboard(request):
    PENDING_STATUS = ["SUBMITTED", "PENDING", "NEED_APPROVAL"]
    
    # Засвар үйлчилгээний өгөгдөл бэлтгэх
    maint = MaintenanceService.objects.filter(workflow_status__in=PENDING_STATUS).select_related('device', 'device__location')
    # Хяналт тохируулгын өгөгдөл бэлтгэх
    control = ControlAdjustment.objects.filter(workflow_status__in=PENDING_STATUS).select_related('device', 'device__location')
    
    rows = []
# inventory/reports_hub_compat.py-д нэмэх
def workflow_review_action(request):
    if request.method == "POST":
        kind = request.POST.get("kind")
        obj_id = request.POST.get("id")
        action = request.POST.get("action")
        reason = request.POST.get("reason", "")
        
        Model = MaintenanceService if kind == "MAINT" else ControlAdjustment
        obj = Model.objects.get(pk=obj_id)
        
        if action == "approve":
            obj.workflow_status = "APPROVED"
        else:
            obj.workflow_status = "REJECTED"
            obj.note = f"{obj.note}\nReject reason: {reason}"
        
        obj.save()
        return JsonResponse({"ok": True})
    
    # Засварын мөрүүдийг нэгтгэх
    for m in maint:
        rows.append({
            "kind": "MAINT",
            "record_id": m.pk,
            "status": m.workflow_status,
            "created_at": m.date.strftime("%Y-%m-%d") if m.date else "",
            "device_label": str(m.device),
            "device_url": reverse("admin:inventory_device_change", args=[m.device.pk]),
            "record_url": reverse("admin:inventory_maintenanceservice_change", args=[m.pk]),
            "location_label": str(m.device.location) if m.device.location else "-",
            "aimag": str(m.device.location.aimag_ref) if m.device.location and m.device.location.aimag_ref else "-",
            "org": str(m.device.location.owner_org) if m.device.location and m.device.location.owner_org else "-",
        })

    # Хяналтын мөрүүдийг нэгтгэх
    for c in control:
        rows.append({
            "kind": "CONTROL",
            "record_id": c.pk,
            "status": c.workflow_status,
            "created_at": c.date.strftime("%Y-%m-%d") if c.date else "",
            "device_label": str(c.device),
            "device_url": reverse("admin:inventory_device_change", args=[c.device.pk]),
            "record_url": reverse("admin:inventory_controladjustment_change", args=[c.pk]),
            "location_label": str(c.device.location) if c.device.location else "-",
            "aimag": str(c.device.location.aimag_ref) if c.device.location and c.device.location.aimag_ref else "-",
            "org": str(c.device.location.owner_org) if c.device.location and c.device.location.owner_org else "-",
        })

    # AJAX хүсэлт ирвэл зөвхөн JSON буцаана
    if request.GET.get("ajax") == "1":
        return JsonResponse({"ok": True, "rows": rows})

    context = {
        "title": "Хүлээгдэж буй ажлууд",
        "rows": rows,
        "pending_statuses": PENDING_STATUS,
        "is_aimag_engineer": getattr(request.user, "userprofile", None) and request.user.userprofile.role == "aimag_engineer",
    }
    return render(request, "inventory/admin/workflow_pending.html", context)