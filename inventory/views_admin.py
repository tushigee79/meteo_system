# inventory/views_admin.py
from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render


@staff_member_required
def dashboard_home(request):
    # /django-admin/dashboard/
    return render(request, "admin/dashboard_home.html", {})


@staff_member_required
def dashboard_table(request):
    # /django-admin/dashboard/table/
    return render(request, "admin/dashboard_table.html", {})


@staff_member_required
def dashboard_graph(request):
    # /django-admin/dashboard/graph/
    return render(request, "admin/dashboard_graph.html", {})


@staff_member_required
def dashboard_general(request):
    # /django-admin/dashboard/general/
    return render(request, "admin/dashboard_general.html", {})


@staff_member_required
def admin_data_entry(request):
    # /django-admin/data-entry/
    return render(request, "admin/admin_data_entry.html", {})
