from django.contrib import admin
from .models import Organization, User, Department, Zone

# Personalizar visualización filtros y busquedas- ppt 3 --> pm
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
# columnas, filtros, campos de busqueda, campos  de auditoria solo lectura, orden predeterminado
    list_display = (
        "organization_id",
        "legal_name",
        "comercial_name",
        "tax",
        "email",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = (
        "organization_id",
        "legal_name",
        "comercial_name",
        "tax",
        "email",
    )
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    ordering = ("legal_name",)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
# columnas, filtros, campos de busqueda, optimizacion sql, campos  de auditoria solo lectura, orden predeterminado
    list_display = (
        "user_id",
        "username",
        "rut",
        "email",
        "role",
        "organization",
        "department",
        "status",
    )
    list_filter = ("role", "status", "organization", "department")
    search_fields = (
        "user_id",
        "username",
        "rut",
        "email",
        "organization__legal_name",
    )
    list_select_related = ("organization", "department")
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    ordering = ("username",)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
# columnas, filtros, campos de busqueda, optimizacion sql, campos  de auditoria solo lectura, orden predeterminado
    list_display = (
        "department_id",
        "name",
        "organization",
        "user",
        "status",
        "created_at",
    )
    list_filter = ("status", "organization", "created_at")
    search_fields = (
        "department_id",
        "name",
        "organization__legal_name",
        "user__username",
    )
    list_select_related = ("organization", "user")
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    ordering = ("name",)

@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
# columnas, filtros, campos de busqueda, optimizacion sql, campos  de auditoria solo lectura, orden predeterminado
    list_display = (
        "zone_id",
        "name",
        "organization",
        "department",
        "status",
        "created_at",
    )
    list_filter = ("status", "organization", "department")
    search_fields = (
        "zone_id",
        "name",
        "organization__legal_name",
        "department__name",
    )
    list_select_related = ("organization", "department")
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    ordering = ("name",)