from django.http import HttpResponse

# =========================
# SAFE Lazy wrappers
# =========================
# ⚠️ IMPORTANT:
# - Do NOT import reports_hub at module import time
# - Import inside each function to avoid Django setup / circular import issues


# ===== Pages / charts =====
def reports_hub_view(request, *args, **kwargs):
    from . import reports_hub as rh
    return rh.reports_hub_view(request, *args, **kwargs)


def reports_chart_json(request, *args, **kwargs):
    from . import reports_hub as rh
    return rh.reports_chart_json(request, *args, **kwargs)


# ===== Sums (legacy name expected by admin.py) =====
def reports_sums_by_aimag(request, *args, **kwargs):
    from . import reports_hub as rh
    return rh.reports_sums_json(request, *args, **kwargs)


# ===== CSV exports (names expected by admin.py) =====
def reports_export_devices_csv(request, *args, **kwargs):
    from . import reports_hub as rh
    return rh.reports_export_devices_csv(request, *args, **kwargs)


def reports_export_locations_csv(request, *args, **kwargs):
    from . import reports_hub as rh
    fn = getattr(rh, "reports_export_locations_csv", None)
    if not fn:
        return HttpResponse("Locations CSV export not implemented.", content_type="text/plain", status=501)
    return fn(request, *args, **kwargs)


def reports_export_movements_csv(request, *args, **kwargs):
    from . import reports_hub as rh
    fn = getattr(rh, "reports_export_movements_csv", None)
    if not fn:
        return HttpResponse("Movements CSV export not implemented.", content_type="text/plain", status=501)
    return fn(request, *args, **kwargs)


def reports_export_maintenance_csv(request, *args, **kwargs):
    from . import reports_hub as rh
    fn = getattr(rh, "reports_export_maintenance_csv", None)
    if not fn:
        return HttpResponse("Maintenance CSV export not implemented.", content_type="text/plain", status=501)
    return fn(request, *args, **kwargs)


def reports_export_control_csv(request, *args, **kwargs):
    from . import reports_hub as rh
    fn = getattr(rh, "reports_export_control_csv", None)
    if not fn:
        return HttpResponse("Control CSV export not implemented.", content_type="text/plain", status=501)
    return fn(request, *args, **kwargs)


def reports_export_spareparts_csv(request, *args, **kwargs):
    from . import reports_hub as rh
    fn = getattr(rh, "reports_export_spareparts_csv", None)
    if not fn:
        return HttpResponse("Spareparts CSV export not implemented.", content_type="text/plain", status=501)
    return fn(request, *args, **kwargs)


# legacy alias (devices)
def reports_export_csv(request, *args, **kwargs):
    return reports_export_devices_csv(request, *args, **kwargs)


# ===== Auth audit CSV (NOT implemented in night code) =====
def reports_export_auth_audit_csv(request, *args, **kwargs):
    return HttpResponse(
        "Auth audit CSV export is not implemented in this build.",
        content_type="text/plain",
        status=501
    )


# ---- Dashboard Table bridge (SAFE wrapper) ----
def reports_table_json(request, *args, **kwargs):
    from .admin_dashboard import reports_table_json as _impl
    return _impl(request, *args, **kwargs)
