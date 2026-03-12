# inventory/views_admin.py
from __future__ import annotations

from datetime import datetime, date
from typing import Optional, List, Any, Dict

from django.contrib.admin.views.decorators import staff_member_required
from django.db import models
from django.db.models import Q
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.urls import reverse

from .models import MaintenanceService, ControlAdjustment, Device, Location


# =============================================================================
# Helpers
# =============================================================================

def _get_field(model, field_name: str):
    try:
        return model._meta.get_field(field_name)
    except Exception:
        return None


def _fmt_date(v) -> str:
    if not v:
        return ""
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d")
    return str(v)


def _safe_attr(obj, path: str, default=""):
    """
    Object-Ð¾Ð¾Ñ Ñ†ÑÐ³ÑÑÑ€ Ñ‚ÑƒÑÐ³Ð°Ð°Ñ€Ð»Ð°Ð³Ð´ÑÐ°Ð½ Ð·Ð°Ð¼Ð°Ð°Ñ€ ÑƒÑ‚Ð³Ð° Ð°Ð²Ð°Ñ… (Ð¶: 'device.location.name')
    """
    try:
        cur = obj
        for p in path.split("."):
            if cur is None:
                return default
            cur = getattr(cur, p, None)
        return cur if cur is not None else default
    except Exception:
        return default


def _wf_label(obj) -> str:
    # Choices display
    for name in ("get_workflow_status_display", "get_status_display"):
        fn = getattr(obj, name, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                pass

    v = getattr(obj, "workflow_status", None) or getattr(obj, "status", None)
    return str(v) if v is not None else ""


def _is_done(obj) -> bool:
    v = getattr(obj, "workflow_status", None) or getattr(obj, "status", None)
    if v is None:
        return False
    s = str(v).upper()
    return any(x in s for x in ("APPROVED", "DONE", "COMPLETED", "FINISHED", "SUCCESS"))


def _is_pending(obj) -> bool:
    v = getattr(obj, "workflow_status", None) or getattr(obj, "status", None)
    if v is None:
        return True
    s = str(v).upper()
    return any(x in s for x in ("PENDING", "WAIT", "NEW", "DRAFT", "PROCESS"))


def _parse_date(s: str) -> Optional[date]:
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%d/%m/%Y", "%d.%m.%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _pick_existing_field(model, candidates: List[str]) -> Optional[str]:
    try:
        field_names = {f.name for f in model._meta.get_fields()}
    except Exception:
        return None
    for c in candidates:
        if c in field_names:
            return c
    return None


def _select_related_existing(qs, model, paths: List[str]):
    """
    select_related() -Ð¸Ð¹Ð³ Ð·Ó©Ð²Ñ…Ó©Ð½ Ð±Ð¾Ð´Ð¸Ñ‚Ð¾Ð¾Ñ€ Ð±Ð°Ð¹Ð³Ð°Ð° FK Ð·Ð°Ð¼ÑƒÑƒÐ´ Ð´ÑÑÑ€ Ñ…ÑÑ€ÑÐ³Ð»ÑÐ½Ñ.
    'org_ref' Ð·ÑÑ€ÑÐ³ Ð±Ð°Ð¹Ñ…Ð³Ò¯Ð¹ Ñ‚Ð°Ð»Ð±Ð°Ñ€ Ð´ÑÑÑ€ FieldError Ð³Ð°Ñ€Ð°Ñ…Ð°Ð°Ñ Ñ…Ð°Ð¼Ð³Ð°Ð°Ð»Ð½Ð°.
    """
    ok: List[str] = []
    for path in paths:
        cur_model = model
        good = True
        for seg in path.split("__"):
            f = _get_field(cur_model, seg)
            if f is None or not getattr(f, "is_relation", False):
                good = False
                break
            cur_model = f.remote_field.model
        if good:
            ok.append(path)

    if ok:
        try:
            return qs.select_related(*ok)
        except Exception:
            return qs
    return qs


# =============================================================================
# Dashboard Table (HTML + JSON)
# =============================================================================

@staff_member_required
def dashboard_table(request: HttpRequest):
    """
    1) ?ajax=1   -> table JSON (maintenance/control)
    2) else      -> HTML
    """
    if request.GET.get("ajax") == "1":
        report = request.GET.get("report", "maintenance")
        performer = (request.GET.get("performer") or "").strip()
        date_from = _parse_date(request.GET.get("date_from") or "")
        date_to = _parse_date(request.GET.get("date_to") or "")

        Model = MaintenanceService if report == "maintenance" else ControlAdjustment
        qs = Model.objects.all()

        # ---- Date filter (safe) ----
        date_field = _pick_existing_field(
            Model, ["date", "performed_at", "performed_date", "service_date", "created_at", "updated_at"]
        )
        if date_field:
            f_inst = _get_field(Model, date_field)
            is_dt = isinstance(f_inst, models.DateTimeField)

            if date_from:
                lookup = f"{date_field}__date__gte" if is_dt else f"{date_field}__gte"
                qs = qs.filter(**{lookup: date_from})
            if date_to:
                lookup = f"{date_field}__date__lte" if is_dt else f"{date_field}__lte"
                qs = qs.filter(**{lookup: date_to})

        # ---- Performer filter (if fields exist) ----
        try:
            field_names = {f.name for f in Model._meta.get_fields()}
        except Exception:
            field_names = set()

        if performer and field_names:
            q_obj = Q()
            if "performer_engineer_name" in field_names:
                q_obj |= Q(performer_engineer_name__icontains=performer)
            if "performer_org_name" in field_names:
                q_obj |= Q(performer_org_name__icontains=performer)
            if q_obj.children:
                qs = qs.filter(q_obj)

        # ---- KPI ----
        total = qs.count()
        done = pending = None
        status_field = _pick_existing_field(Model, ["workflow_status", "status"])
        if status_field:
            f_inst = _get_field(Model, status_field)
            if isinstance(f_inst, (models.CharField, models.TextField)):
                try:
                    done = qs.filter(**{f"{status_field}__icontains": "APPROVED"}).count()
                    pending = qs.filter(**{f"{status_field}__icontains": "PENDING"}).count()
                except Exception:
                    done = pending = None

        if done is None or pending is None:
            sample = list(qs.order_by("-id")[:500])
            done = sum(1 for x in sample if _is_done(x))
            pending = sum(1 for x in sample if _is_pending(x))

        # ---- Rows ----
        order_by = f"-{date_field}" if date_field else "-id"
        rows_qs = qs.order_by(order_by)[:200]
        rows_qs = _select_related_existing(rows_qs, Model, [
            "device",
            "device__location",
            "device__owner_org",
            "device__location__owner_org",
            "device__location__aimag_ref",
            "device__location__sum_ref",
        ])

        columns = [
            "#",
            "Огноо",
            "Багаж (Serial)",
            "Байршил",
            "Аймаг",
            "Сум / Дүүрэг",
            "Эзэмшигч байгууллага",
            "Гүйцэтгэгч (нэр/байгууллага)",
            "Статус",
            "Тайлбар",
        ]

        rows: List[List[Any]] = []
        for i, obj in enumerate(rows_qs, start=1):
            dev = getattr(obj, "device", None)
            loc = getattr(dev, "location", None) if dev else None

            aimag = _safe_attr(loc, "aimag_ref.name") or _safe_attr(loc, "aimag.name")
            sumduureg = (
                _safe_attr(loc, "sum_ref.name")
                or _safe_attr(loc, "district_name")
                or _safe_attr(loc, "sum_duureg.name")
            )

            owner_org = (
                _safe_attr(dev, "owner_org.name")
                or _safe_attr(loc, "owner_org.name")
            )

            performer_name = (
                (_safe_attr(obj, "performer_engineer_name") or _safe_attr(obj, "performer_org_name")) or ""
            ).strip()

            dval = getattr(obj, date_field, None) if date_field else None
            rows.append([
                i,
                _fmt_date(dval) if dval is not None else "",
                _safe_attr(dev, "serial_number") or _safe_attr(dev, "name"),
                _safe_attr(loc, "name"),
                aimag,
                sumduureg,
                owner_org,
                performer_name,
                _wf_label(obj),
                _safe_attr(obj, "note") or _safe_attr(obj, "description") or "",
            ])

        return JsonResponse({
            "meta": {"total": total, "done": done, "pending": pending},
            "columns": columns,
            "rows": rows,
        })

    return render(request, "admin/dashboard_table.html", {})


# =============================================================================
# Dashboard Graph
# =============================================================================

@staff_member_required
def dashboard_graph(request: HttpRequest):
    """
    Graph dashboard-ийн HTML хуудас.

    URL-уудыг template дотроос namespace-оор reverse хийхгүй, эндээс context-оор өгч байна.
    (ингэснээр namespace-ийн алдаа гарахгүй)
    """

    # best effort reverse (fall back to hardcoded paths)
    try:
        pending_counts_url = reverse("inventory_admin:workflow_pending_counts")
    except Exception:
        pending_counts_url = "/django-admin/inventory/workflow/pending-counts/"

    try:
        graph_data_url = reverse("inventory_admin:dashboard_graph_data")
    except Exception:
        graph_data_url = "/django-admin/dashboard/graph/data/"

    ctx = {
        "pending_counts_url": pending_counts_url,
        "dash_graph_data_url": graph_data_url,
    }
    
    return render(request, "admin/dashboard_graph.html", ctx)


@staff_member_required
def dashboard_graph_data(request: HttpRequest):
    """
    Graph dashboard-ийн JSON endpoint.
    HTML хуудас дээр JSON-ыг ашиглах боломжтой (алдаа гарахгүй).
    """
    try:
        # ----- Filters -----
        date_from = _parse_date(request.GET.get("date_from") or "")
        date_to = _parse_date(request.GET.get("date_to") or "")
        aimag_id = (request.GET.get("aimag_id") or "").strip()
        location_types = (request.GET.get("location_types") or request.GET.get("kind") or "").strip()

        loc_qs = Location.objects.all()

        # aimag
        if aimag_id.isdigit():
            loc_qs = loc_qs.filter(aimag_ref_id=int(aimag_id))

        # location_types: "AWS,RADAR" (comma separated)
        if location_types:
            types = [t.strip().upper() for t in location_types.split(",") if t.strip()]
            if types:
                # your model uses location_type field
                if _get_field(Location, "location_type"):
                    loc_qs = loc_qs.filter(location_type__in=types)

        # dates: if Location has created_at/updated_at you can filter; else ignore safely
        date_field = _pick_existing_field(Location, ["created_at", "updated_at"])
        if date_field and (date_from or date_to):
            f_inst = _get_field(Location, date_field)
            is_dt = isinstance(f_inst, models.DateTimeField)
            if date_from:
                lookup = f"{date_field}__date__gte" if is_dt else f"{date_field}__gte"
                loc_qs = loc_qs.filter(**{lookup: date_from})
            if date_to:
                lookup = f"{date_field}__date__lte" if is_dt else f"{date_field}__lte"
                loc_qs = loc_qs.filter(**{lookup: date_to})

        # ----- Map points -----
        pts = []
        for loc in loc_qs.only("id", "name", "latitude", "longitude").iterator(chunk_size=2000):
            lat = getattr(loc, "latitude", None)
            lon = getattr(loc, "longitude", None)
            if lat is None or lon is None:
                continue
            pts.append({
                "id": loc.id,
                "name": loc.name,
                "lat": float(lat),
                "lon": float(lon),
                "location_type": getattr(loc, "location_type", "") or "",
            })

        # ----- Simple demo aggregates (replace with real later) -----
        # These keys match your dashboard_graph.js expectations
        data = {
            "echarts_workflow_stacked": [
                {"name": "Батлагдсан", "value": 1}
            ]          ,
            "echarts_sla": [
    {"name": "31-90", "value": 1},
    {"name": "0-30", "value": 1},
    {"name": "90+", "value": 1}
],
            "echarts_aimag": [
                {"name": "Хөвсгөл", "value": 50},
                {"name": "Сэлэнгэ", "value": 20}
            ],
            "echarts_kind": [
                {"name": "AWS", "value": 1}
            ],
            "locations": pts,

        }
        return JsonResponse(data, json_dumps_params={"ensure_ascii": False})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# =============================================================================
# Dashboard Charts
# =============================================================================

@staff_member_required
def dashboard_charts(request: HttpRequest):
    """
    /django-admin/dashboard/charts/?ajax=1  -> Ð“Ñ€Ð°Ñ„Ð¸ÐºÐ¸Ð¹Ð½ JSON Ó©Ð³Ó©Ð³Ð´Ó©Ð» Ð±ÑƒÑ†Ð°Ð°Ð½Ð°.
    """
    if request.GET.get("ajax") == "1":
        data = {
            "devices_by_status": {
                "axis": ["Даваа", "Мягмар", "Лхагва", "Пүрэв", "Баасан"],
                "series": {
                    "Идэвхтэй": [10, 12, 11, 14, 15],
                    "Засвартай": [2, 1, 3, 2, 1],
                },
            },
            "workflow": {
                "axis": ["Jan", "Feb", "Mar"],
                "ms": [5, 10, 8],  # Maintenance Service
                "ca": [3, 6, 9],   # Control Adjustment
            },
        }
        return JsonResponse(data, json_dumps_params={"ensure_ascii": False})

    return JsonResponse({"error": "ajax=1 required"}, status=400)


# =============================================================================
# Other pages required by InventoryAdminSite
# =============================================================================

@staff_member_required
def dashboard_general(request):
    from inventory.views import dashboard_view
    return dashboard_view(request)


@staff_member_required
def dashboard_general(request: HttpRequest):
    return render(request, "admin/dashboard_general.html", {})


@staff_member_required
def admin_data_entry(request: HttpRequest):
    return render(request, "admin/admin_data_entry.html", {})

