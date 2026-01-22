# inventory/admin_dashboard.py
import csv
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from .dashboard import build_dashboard_context, scoped_devices_qs


@staff_member_required(login_url="/django-admin/login/")
def dashboard_table_view(request):
    """Хүснэгт/KPI dashboard (templates/admin/dashboard.html)"""
    ctx = build_dashboard_context(request.user)
    return render(request, "admin/dashboard.html", ctx)


@staff_member_required(login_url="/django-admin/login/")
def dashboard_graph_view(request):
    """График/Chart dashboard (templates/inventory/dashboard.html)"""
    ctx = build_dashboard_context(request.user)
    return render(request, "inventory/dashboard.html", ctx)


@staff_member_required(login_url="/django-admin/login/")
def export_devices_csv(request):
    """Багажуудыг CSV хэлбэрээр экспортлох"""
    qs = scoped_devices_qs(request.user).select_related("catalog_item", "location")

    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="devices_export.csv"'
    resp.write("\ufeff")  # Excel-д UTF-8 BOM

    w = csv.writer(resp)
    w.writerow(["ID", "Төрөл(kind)", "Каталогийн нэр", "Бусад нэр", "Байршил", "Серийн дугаар", "Төлөв(status)"])

    for d in qs:
        kind = d.catalog_item.get_kind_display() if d.catalog_item else "-"
        cat_name = d.catalog_item.name_mn if d.catalog_item else "-"
        loc_name = str(d.location) if d.location else "-"
        w.writerow([
            d.id,
            kind,
            cat_name,
            d.other_name or "",
            loc_name,
            getattr(d, "serial_number", "-"),
            getattr(d, "status", "-"),
        ])

    return resp
