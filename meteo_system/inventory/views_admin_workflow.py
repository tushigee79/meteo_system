from django.http import JsonResponse, HttpRequest
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from .models import SumDuureg
from .dashboards.services import build_workflow_pending_counts

def reports_sums_json(request: HttpRequest) -> JsonResponse:
    """
    Compatibility wrapper for reports dashboard.
    """
    aid = (
        request.GET.get("aimag_id")
        or request.GET.get("aimag")
        or request.GET.get("aimag_ref")
        or ""
    ).strip()

    qs = SumDuureg.objects.all().order_by("name")
    if aid:
        qs = qs.filter(aimag_id=aid)

    rows = [{"id": s.id, "name": s.name} for s in qs[:5000]]

    return JsonResponse(
        {
            "results": rows,
            "sums": rows,
        },
        json_dumps_params={"ensure_ascii": False},
    )

@staff_member_required
def workflow_pending_dashboard(request, admin_site=None):
    context = {
        **(admin_site.each_context(request) if admin_site else {}),
        "title": "Хүлээгдэж буй workflow",
        "pending_counts": build_workflow_pending_counts(),
    }
    return render(request, "admin/workflow_pending_dashboard.html", context)

@staff_member_required
def workflow_pending_counts(request):
    return JsonResponse(build_workflow_pending_counts())

@staff_member_required
def workflow_review_action(request):
    """
    Workflow-ийн хүсэлтийг хянах, батлах эсвэл татгалзах үйлдэл.
    """
    if request.method == "POST":
        # Энд таны workflow-ийг боловсруулах логик орно
        # Жишээ нь: action = request.POST.get('action')
        return JsonResponse({"status": "success", "message": "Үйлдэл амжилттай"})
    
    return JsonResponse({"status": "error", "message": "Зөвхөн POST хүсэлт зөвшөөрөгдөнө"}, status=400)

# inventory/views_admin_workflow.py файлын төгсгөлд нэмэх:

@staff_member_required
def workflow_review_action(request):
    """
    Workflow-ийн шийдвэр гаргах (approve/reject) үйлдэл.
    """
    if request.method == "POST":
        return JsonResponse({"status": "success", "message": "Амжилттай"})
    return JsonResponse({"status": "error", "message": "POST хүсэлт шаардлагатай"}, status=400)

@staff_member_required
def workflow_audit_log(request):
    """
    Workflow-ийн түүх болон аудитын лог харуулах.
    """
    context = {
        "title": "Workflow-ийн аудитын бүртгэл",
    }
    # Хэрэв template файл байгаа бол render хийнэ, байхгүй бол HttpResponse ашиглаж болно
    return render(request, "admin/workflow_audit_log.html", context)

@staff_member_required
def workflow_history(request, object_id=None):
    """
    Тодорхой нэг объектын workflow түүх.
    """
    return JsonResponse({"status": "ok", "history": []})