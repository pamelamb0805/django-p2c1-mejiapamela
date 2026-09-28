from django.contrib import admin
from .models import Catalog, Product, Device, Measurement, AlertRule, AlertEvent, MaintenanceRequest, History

# Personalizar visualización filtros y busquedas- ppt 3 --> pm
@admin.register(Catalog)
class CatalogAdmin(admin.ModelAdmin):
# columnas, filtros, campos de busqueda, campos solo lectura, orden predeterminado
    list_display = ("catalog_id", "name", "status", "created_at", "updated_at")
    list_filter = ("status", "created_at")
    search_fields = ("catalog_id", "name")
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    ordering = ("name",)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
# columnas, filtros, campos de busqueda, optimizacion sql, campos de auditoria solo lectura, orden predeterminado
    list_display = ("sku", "name", "catalog", "manufacter", "kwh", "created_at")
    list_filter = ("catalog", "manufacter", "created_at")
    search_fields = ("sku", "product_id", "name", "catalog__name")
    list_select_related = ("catalog",)
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    ordering = ("name",)

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
# columnas, filtros, campos de busqueda, optimizacion sql, campos de auditoria solo lectura, orden predeterminado
    list_display = (
        "device_id",
        "internal_name",
        "product",
        "zone",
        "status",
        "created_at",
    )
    list_filter = ("status", "product", "zone", "created_at")
    search_fields = (
        "device_id",
        "internal_name",
        "serial_number",
        "product__name",
        "zone__name",
    )
    list_select_related = ("product", "zone")
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    ordering = ("internal_name",)

@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
# columnas, navegacion,filtros, campos de busqueda, optimizacion sql, campos de auditoria solo lectura, orden fecha descendente
    list_display = (
        "measurement_id",
        "device",
        "value",
        "unit",
        "datetime",
        "origin",
        "status",
    )
    date_hierarchy = "datetime"
    list_filter = ("unit", "origin", "status", "device")
    search_fields = (
        "measurement_id",
        "origin",
        "device__device_id",
        "device__internal_name",
    )
    list_select_related = ("device", "user")
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    ordering = ("-datetime",)

@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
# columnas, filtros, campos de busqueda, optimizacion sql, campos de auditoria solo lectura, orden predeterminado
    list_display = (
        "alert_rule_id",
        "name",
        "severity",
        "product",
        "min_limit",
        "max_limit",
        "status",
    )
    list_filter = ("severity", "status", "product")
    search_fields = ("alert_rule_id", "name", "product__name", "product__sku")
    list_select_related = ("product",)
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    ordering = ("name",)

class AlertEventAdmin(admin.ModelAdmin):
# columnas,navegacion jerarquica por fecha de creación, filtros, campos de busqueda, optimizacion sql, campos de auditoria solo lectura, orden descendente
    list_display = (
        "alert_event_id",
        "device",
        "alert_rule",
        "status",
        "acknowledged_by",
        "resolved_by",
        "created_at",
    )
    date_hierarchy = "created_at"
    list_filter = ("status", "device", "alert_rule", "created_at")
    search_fields = (
        "alert_event_id",
        "observations",
        "device__internal_name",
        "device__device_id",
        "alert_rule__name",
    )
    list_select_related = (
        "acknowledged_by",
        "resolved_by",
        "measurement",
        "device",
        "alert_rule",
    )
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    ordering = ("-created_at",)

@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
# columnas,navegacion jerarquica por fecha programada, filtros, campos de busqueda, optimizacion sql, campos de auditoria solo lectura, orden descendente
    list_display = (
        "maintenance_request_id",
        "request_type",
        "priority",
        "status",
        "device",
        "organization",
        "assigned_to",
        "scheduled_date",
    )
    date_hierarchy = "scheduled_date"
    list_filter = ("priority", "status", "request_type", "organization")
    search_fields = (
        "maintenance_request_id",
        "reason",
        "diagnosis",
        "device__internal_name",
        "organization__name",
    )
    list_select_related = (
        "device",
        "organization",
        "request_by",
        "assigned_to",
    )
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    ordering = ("-created_at",)

@admin.register(History)
class HistoryAdmin(admin.ModelAdmin):
# columnas,navegacion jerarquica por fecha de inicio, filtros, campos de busqueda, optimizacion sql, campos de auditoria solo lectura, orden descendente
    list_display = (
        "history_id",
        "device",
        "zone",
        "start_date",
        "end_date",
        "reason",
    )
    date_hierarchy = "start_date"
    list_filter = ("zone", "device", "start_date")
    search_fields = (
        "history_id",
        "reason",
        "device__internal_name",
        "device__device_id",
        "zone__name",
    )
    list_select_related = ("device", "zone")
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    ordering = ("-start_date",)   