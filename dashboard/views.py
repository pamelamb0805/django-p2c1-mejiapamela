from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count, Q
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from accounts.models import UserProfile
from core.models import ActivityLog
from devices.models import Device, Measurement, AlertEvent


# ==========================================================
# PERMISOS DE VISUALIZACIÓN DE ACTIVIDAD
# ==========================================================

MODULE_PERMISSIONS = {
    "organizaciones": "organizations.view_organization",
    "departamentos": "organizations.view_department",
    "zonas": "organizations.view_zone",
    "usuarios": "accounts.view_userprofile",
    "categorias": "devices.view_catalog",
    "catalogos": "devices.view_catalog",
    "productos": "devices.view_product",
    "dispositivos": "devices.view_device",
    "mediciones": "devices.view_measurement",
    "alertas": "devices.view_alertevent",
    "mantenimiento": "devices.view_maintenancerequest",
}

# Estos módulos son globales y no pertenecen a una organización.
GLOBAL_MODULES = [
    "categorias",
    "catalogos",
    "productos",
]


# ==========================================================
# ACTIVIDAD VISIBLE PARA EL USUARIO
# ==========================================================

def get_visible_activity(user, organization_id):

    # Identificar los módulos que el usuario tiene permiso de consultar.
    allowed_modules = [
        module
        for module, permission in MODULE_PERMISSIONS.items()
        if user.has_perm(permission)
    ]

    queryset = ActivityLog.objects.filter(
        module__in=allowed_modules
    ).select_related(
        "actor",
        "organization"
    )

    # El superusuario puede consultar toda la actividad.
    if user.is_superuser:
        return queryset.order_by("-created_at")

    # Sin organización, no se permite consultar actividad.
    if not organization_id:
        return queryset.none()

    # Actividad de la organización actual
    # más actividad de los mantenedores globales autorizados.
    queryset = queryset.filter(
        Q(organization_id=organization_id)
        |
        Q(
            organization__isnull=True,
            module__in=GLOBAL_MODULES
        )
    )

    return queryset.order_by("-created_at")


# ==========================================================
# DASHBOARD PRINCIPAL
# ==========================================================

@login_required
def dashboard(request):

    user = request.user

    profile = getattr(user, "profile", None)

    # Los usuarios normales deben tener perfil.
    if profile is None and not user.is_superuser:
        raise PermissionDenied(
            "La cuenta no posee un perfil habilitado."
        )

    organization = (
        profile.organization
        if profile
        else None
    )

    organization_id = (
        profile.organization_id
        if profile
        else None
    )

    # ------------------------------------------------------
    # VISITAS Y SESIÓN
    # ------------------------------------------------------

    visits = request.session.get(
        "dashboard_visits",
        0
    )

    request.session["dashboard_visits"] = visits + 1

    # ------------------------------------------------------
    # 1. CANTIDAD DE USUARIOS
    # ------------------------------------------------------

    mostrar_usuarios = user.has_perm(
        "accounts.view_userprofile"
    )

    usuarios_total = None

    if mostrar_usuarios:

        usuarios = UserProfile.objects.filter(
            deleted_at__isnull=True
        )

        if not user.is_superuser:
            usuarios = usuarios.filter(
                organization_id=organization_id
            )

        usuarios_total = usuarios.count()

    # ------------------------------------------------------
    # 2. DISPOSITIVOS / PRODUCTOS POR ZONA
    # ------------------------------------------------------

    mostrar_dispositivos = user.has_perm(
        "devices.view_device"
    )

    dispositivos = Device.objects.none()

    dispositivos_total = None
    productos_por_zona = []

    if mostrar_dispositivos:

        dispositivos = Device.objects.filter(
            deleted_at__isnull=True
        ).select_related(
            "product",
            "zone",
            "zone__organization"
        )

        if not user.is_superuser:
            dispositivos = dispositivos.filter(
                zone__organization_id=organization_id
            )

        dispositivos_total = dispositivos.count()

        productos_por_zona = (
            dispositivos
            .values("zone__name")
            .annotate(
                total=Count("pk")
            )
            .order_by("zone__name")
        )

    # ------------------------------------------------------
    # 3. PROMEDIO DE CONSUMO
    # ------------------------------------------------------

    mostrar_mediciones = user.has_perm(
        "devices.view_measurement"
    )

    promedio_consumo = None
    mediciones_total = None

    if mostrar_mediciones:

        mediciones = Measurement.objects.filter(
            deleted_at__isnull=True,
            unit__iexact="kWh"
        )

        if not user.is_superuser:
            mediciones = mediciones.filter(
                device__zone__organization_id=organization_id
            )

        resultado = mediciones.aggregate(
            promedio=Avg("value")
        )

        promedio_consumo = resultado["promedio"]

        mediciones_total = mediciones.count()

    # ------------------------------------------------------
    # 4. ALERTAS REGISTRADAS
    # ------------------------------------------------------

    mostrar_alertas = user.has_perm(
        "devices.view_alertevent"
    )

    alertas_total = None

    if mostrar_alertas:

        alertas = AlertEvent.objects.filter(
            deleted_at__isnull=True
        )

        if not user.is_superuser:
            alertas = alertas.filter(
                device__zone__organization_id=organization_id
            )

        alertas_total = alertas.count()

    # ------------------------------------------------------
    # 5. ÚLTIMOS REGISTROS / BITÁCORA
    # ------------------------------------------------------

    actividad = get_visible_activity(
        user,
        organization_id
    )[:15]

    # ------------------------------------------------------
    # PERFIL Y ROL
    # ------------------------------------------------------

    roles = list(
        user.groups.values_list(
            "name",
            flat=True
        )
    )

    if user.is_superuser:
        nombre_perfil = "Administrador de plataforma"
    elif roles:
        nombre_perfil = ", ".join(roles)
    else:
        nombre_perfil = "Usuario"

    # ------------------------------------------------------
    # CONTEXTO
    # ------------------------------------------------------
    avatar_url = (
        profile.avatar.url
        if profile and profile.avatar
        else None
    )
    context = {
        "organization": organization,

        "visits": visits + 1,

        "mode": request.session.get(
            "dashboard_mode",
            "normal"
        ),

        "nombre_perfil": nombre_perfil,

        # Estadísticas.
        "mostrar_usuarios": mostrar_usuarios,
        "usuarios_total": usuarios_total,

        "mostrar_dispositivos": mostrar_dispositivos,
        "dispositivos_total": dispositivos_total,
        "productos_por_zona": productos_por_zona,

        "mostrar_mediciones": mostrar_mediciones,
        "promedio_consumo": promedio_consumo,
        "mediciones_total": mediciones_total,

        "mostrar_alertas": mostrar_alertas,
        "alertas_total": alertas_total,

        # Actividad.
        "actividad": actividad,
        
        "avatar_url": avatar_url,
    }

    return render(
        request,
        "dashboard/index.html",
        context
    )


# ==========================================================
# PREFERENCIAS DEL DASHBOARD
# ==========================================================

@login_required
@require_POST
def remember_preference(request):

    request.session["dashboard_mode"] = "compact"

    messages.success(
        request,
        "Preferencia guardada correctamente."
    )

    return redirect(
        "dashboard:dashboard"
    )