"""
Compatibility loader for Django admin registration.

All real admin code lives under inventory/admin/*
"""

from .admin.admin_site import inventory_admin_site

# Import modules so Django registers ModelAdmin classes
from .admin import admin_filters  # noqa: F401
from .admin import admin_qr  # noqa: F401
from .admin import admin_passport  # noqa: F401
from .admin import admin_locations  # noqa: F401
from .admin import admin_devices  # noqa: F401
from .admin import admin_dashboard  # noqa: F401
from .admin import admin_reports  # noqa: F401