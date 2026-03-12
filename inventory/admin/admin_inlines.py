from django.contrib import admin
from ..models import DeviceMovement, MaintenanceService


class DeviceMovementInline(admin.TabularInline):
    model = DeviceMovement
    extra = 0
    autocomplete_fields = ("from_location", "to_location")
    readonly_fields = ("moved_at",)


class MaintenanceInline(admin.TabularInline):
    model = MaintenanceService
    extra = 0