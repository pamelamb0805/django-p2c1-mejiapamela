from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from .excel import export_queryset_excel

def home_view(request):
    """Vista para la página de inicio que usa el home.html global de la estructura."""
    return render(request, 'home.html')


# Creación vista que muestra la página 403 personalizada, con status HTTP 403.
# Clase 7 - Alexander
def permission_denied_view(request, exception=None):
    return render(request, "403.html", status=403)

@login_required
def export_crud_excel(request, module):

    # Importaciones locales para evitar dependencias circulares.
    from accounts.views import UserProfileListView

    from organizations.views import (
        OrganizationListView,
        DepartmentListView,
        ZoneListView,
    )

    from devices.views import (
        DeviceListView,
        CategoryListView,
        CatalogListView,
        ProductListView,
        MeasurementListView,
        AlertListView,
        MaintenanceListView,
    )

    exports = {
        "organizaciones": (
            OrganizationListView,
            "organizations.view_organization",
            "Organizaciones",
        ),
        "departamentos": (
            DepartmentListView,
            "organizations.view_department",
            "Departamentos",
        ),
        "zonas": (
            ZoneListView,
            "organizations.view_zone",
            "Zonas",
        ),
        "usuarios": (
            UserProfileListView,
            "accounts.view_userprofile",
            "Usuarios",
        ),
        "categorias": (
            CategoryListView,
            "devices.view_catalog",
            "Categorías",
        ),
        "catalogos": (
            CatalogListView,
            "devices.view_catalog",
            "Catálogos",
        ),
        "productos": (
            ProductListView,
            "devices.view_product",
            "Productos",
        ),
        "dispositivos": (
            DeviceListView,
            "devices.view_device",
            "Dispositivos",
        ),
        "mediciones": (
            MeasurementListView,
            "devices.view_measurement",
            "Mediciones",
        ),
        "alertas": (
            AlertListView,
            "devices.view_alertevent",
            "Alertas",
        ),
        "mantenimiento": (
            MaintenanceListView,
            "devices.view_maintenancerequest",
            "Mantenimiento",
        ),
    }

    if module not in exports:
        raise PermissionDenied

    list_class, permission, title = exports[module]

    if not request.user.has_perm(permission):
        raise PermissionDenied

    # Reutilizar la consulta real del listado CRUD.
    list_view = list_class()
    list_view.setup(request)

    queryset = list_view.get_queryset()

    # Columnas adicionales para usuarios y perfiles.
    extra_columns = None

    if module == "usuarios":
        extra_columns = [
            (
                "Nombre completo",
                lambda obj: obj.user.get_full_name()
            ),
            (
                "Correo electrónico",
                lambda obj: obj.user.email
            ),
            (
                "Roles",
                lambda obj: ", ".join(
                    obj.user.groups.values_list(
                        "name",
                        flat=True
                    )
                )
            ),
            (
                "Cuenta activa",
                lambda obj: (
                    "Activa" if obj.user.is_active
                    else "Inactiva"
                )
            ),
        ]

    return export_queryset_excel(
        queryset=queryset,
        filename=f"EcoEnergy_{module}",
        sheet_title=title,
        extra_columns=extra_columns,
    )