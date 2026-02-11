# inventory/views_admin.py
from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.http.response import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .models import SumDuureg


@staff_member_required
@require_GET
def reports_sums_by_aimag(request):
    """
    Device form дээр Aimag сонгоход Sum/Duureg-ийн сонголтыг динамикаар авах endpoint.
    GET params: aimag / aimag_id
    """
    aimag_id = request.GET.get("aimag") or request.GET.get("aimag_id")

    qs = SumDuureg.objects.all().order_by("name")
    if aimag_id:
        qs = qs.filter(aimag_ref_id=aimag_id)

    results = [{"id": s.id, "text": s.name} for s in qs]
    return JsonResponse({"results": results})
def dashboard_home(request):
    # /django-admin/dashboard/
    # ✅ templates/admin/dashboard.html ашиглана
    return render(request, "admin/dashboard.html", {})


@staff_member_required
def dashboard_table(request):
    # /django-admin/dashboard/table/
    return render(request, "admin/dashboard_table.html", {})


@staff_member_required
def dashboard_graph(request):
    # /django-admin/dashboard/graph/
    return render(request, "admin/dashboard_graph.html", {})


@staff_member_required
def admin_data_entry(request):
    # /django-admin/data-entry/
    return render(request, "admin/admin_data_entry.html", {})

@staff_member_required
def dashboard_general(request):
    # /django-admin/dashboard/general/
    return render(request, "admin/dashboard.html", {})

