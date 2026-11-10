
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncDate, ExtractHour
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from accounts.models import UserProfile
from core.models import ActivityLog
from devices.models import (
    Device,
    Measurement,
    AlertEvent,
    MaintenanceRequest,
)


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

GLOBAL_MODULES = [
    "categorias",
    "catalogos",
    "productos",
]


def get_visible_activity(user, organization_id):

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

    if user.is_superuser:
        return queryset.order_by("-created_at")

    if not organization_id:
        return queryset.none()

    queryset = queryset.filter(
        Q(organization_id=organization_id)
        |
        Q(
            organization__isnull=True,
            module__in=GLOBAL_MODULES
        )
    )

    return queryset.order_by("-created_at")


def crear_serie(queryset, campo, limite=None):
    """
    Convierte resultados de una consulta en etiquetas y valores
    compatibles con Chart.js.
    """
    if limite:
        queryset = queryset[:limite]

    labels = []
    values = []

    for row in queryset:
        label = row.get(campo)

        if label is None or label == "":
            label = "Sin clasificar"

        labels.append(str(label))
        values.append(float(row.get("total") or 0))

    return {
        "labels": labels,
        "values": values,
    }


@login_required
def dashboard(request):

    user = request.user
    profile = getattr(user, "profile", None)

    if profile is None and not user.is_superuser:
        raise PermissionDenied(
            "La cuenta no posee un perfil habilitado."
        )

    organization = profile.organization if profile else None
    organization_id = profile.organization_id if profile else None

    # --------------------------------------------------
    # VISITAS
    # --------------------------------------------------

    visits = request.session.get("dashboard_visits", 0)
    request.session["dashboard_visits"] = visits + 1

    # --------------------------------------------------
    # USUARIOS
    # --------------------------------------------------

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

    # --------------------------------------------------
    # DISPOSITIVOS
    # --------------------------------------------------

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
            "zone__organization",
            "zone__department"
        )

        if not user.is_superuser:
            dispositivos = dispositivos.filter(
                zone__organization_id=organization_id
            )

        dispositivos_total = dispositivos.count()

        productos_por_zona = (
            dispositivos
            .values("zone__name")
            .annotate(total=Count("pk"))
            .order_by("zone__name")
        )

    # --------------------------------------------------
    # MEDICIONES
    # --------------------------------------------------

    mostrar_mediciones = user.has_perm(
        "devices.view_measurement"
    )

    mediciones = Measurement.objects.none()
    promedio_consumo = None
    mediciones_total = None
    consumo_total = 0

    if mostrar_mediciones:

        mediciones = Measurement.objects.filter(
            deleted_at__isnull=True,
            unit__iexact="kWh"
        ).select_related(
            "device",
            "device__zone",
            "device__zone__department"
        )

        if not user.is_superuser:
            mediciones = mediciones.filter(
                device__zone__organization_id=organization_id
            )

        resultado = mediciones.aggregate(
            promedio=Avg("value"),
            total=Sum("value")
        )

        promedio_consumo = resultado["promedio"]
        consumo_total = float(resultado["total"] or 0)
        mediciones_total = mediciones.count()

    # --------------------------------------------------
    # GRÁFICOS DE MEDICIONES
    # --------------------------------------------------

    charts = {
        "consumo_historico": {"labels": [], "values": []},
        "consumo_departamento": {"labels": [], "values": []},
        "consumo_zona": {"labels": [], "values": []},
        "top_dispositivos": {"labels": [], "values": []},
        "demanda_horaria": {"labels": [], "values": []},
        "estado_dispositivos": {"labels": [], "values": []},
        "estado_alertas": {"labels": [], "values": []},
        "estado_mantenimientos": {"labels": [], "values": []},
    }

    if mostrar_mediciones:

        # 1. Consumo histórico por día: últimos 14 días con lecturas.
        historico = (
            mediciones
            .filter(datetime__isnull=False)
            .annotate(dia=TruncDate("datetime"))
            .values("dia")
            .annotate(total=Sum("value"))
            .order_by("-dia")[:14]
        )

        historico = list(reversed(list(historico)))

        charts["consumo_historico"] = {
            "labels": [
                row["dia"].strftime("%d/%m") if row["dia"] else "Sin fecha"
                for row in historico
            ],
            "values": [
                float(row["total"] or 0)
                for row in historico
            ],
        }

        # 2. Consumo por departamento.
        por_departamento = (
            mediciones
            .values("device__zone__department__name")
            .annotate(total=Sum("value"))
            .order_by("-total")
        )

        charts["consumo_departamento"] = {
            "labels": [
                row["device__zone__department__name"] or "Sin departamento"
                for row in por_departamento
            ],
            "values": [
                float(row["total"] or 0)
                for row in por_departamento
            ],
        }

        # 3. Consumo por zona.
        por_zona = (
            mediciones
            .values("device__zone__name")
            .annotate(total=Sum("value"))
            .order_by("-total")
        )

        charts["consumo_zona"] = {
            "labels": [
                row["device__zone__name"] or "Sin zona"
                for row in por_zona
            ],
            "values": [
                float(row["total"] or 0)
                for row in por_zona
            ],
        }

        # 4. Cinco dispositivos con mayor consumo.
        top_dispositivos = (
            mediciones
            .values("device__internal_name")
            .annotate(total=Sum("value"))
            .order_by("-total")[:5]
        )

        charts["top_dispositivos"] = {
            "labels": [
                row["device__internal_name"] or "Sin nombre"
                for row in top_dispositivos
            ],
            "values": [
                float(row["total"] or 0)
                for row in top_dispositivos
            ],
        }

        # 5. Consumo agrupado por hora.
        por_hora = (
            mediciones
            .filter(datetime__isnull=False)
            .annotate(hora=ExtractHour("datetime"))
            .values("hora")
            .annotate(total=Sum("value"))
            .order_by("hora")
        )

        charts["demanda_horaria"] = {
            "labels": [
                f"{row['hora']:02d}:00"
                if row["hora"] is not None
                else "Sin hora"
                for row in por_hora
            ],
            "values": [
                float(row["total"] or 0)
                for row in por_hora
            ],
        }

    # --------------------------------------------------
    # ESTADO DE DISPOSITIVOS
    # --------------------------------------------------

    if mostrar_dispositivos:

        estados_dispositivos = (
            dispositivos
            .values("status")
            .annotate(total=Count("pk"))
            .order_by("status")
        )

        charts["estado_dispositivos"] = {
            "labels": [
                row["status"] or "Sin estado"
                for row in estados_dispositivos
            ],
            "values": [
                row["total"]
                for row in estados_dispositivos
            ],
        }

    # --------------------------------------------------
    # ALERTAS
    # --------------------------------------------------

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

        estados_alertas = (
            alertas
            .values("status")
            .annotate(total=Count("pk"))
            .order_by("status")
        )

        charts["estado_alertas"] = {
            "labels": [
                row["status"] or "Sin estado"
                for row in estados_alertas
            ],
            "values": [
                row["total"]
                for row in estados_alertas
            ],
        }

    # --------------------------------------------------
    # MANTENIMIENTOS
    # --------------------------------------------------

    mostrar_mantenimientos = user.has_perm(
        "devices.view_maintenancerequest"
    )

    if mostrar_mantenimientos:

        mantenimientos = MaintenanceRequest.objects.filter(
            deleted_at__isnull=True
        )

        if not user.is_superuser:
            mantenimientos = mantenimientos.filter(
                organization_id=organization_id
            )

        estados_mantenimientos = (
            mantenimientos
            .values("status")
            .annotate(total=Count("pk"))
            .order_by("status")
        )

        charts["estado_mantenimientos"] = {
            "labels": [
                row["status"] or "Sin estado"
                for row in estados_mantenimientos
            ],
            "values": [
                row["total"]
                for row in estados_mantenimientos
            ],
        }

    # --------------------------------------------------
    # BITÁCORA
    # --------------------------------------------------

    actividad = get_visible_activity(
        user,
        organization_id
    )[:15]

    # --------------------------------------------------
    # PERFIL
    # --------------------------------------------------

    roles = list(
        user.groups.values_list("name", flat=True)
    )

    if user.is_superuser:
        nombre_perfil = "Administrador de plataforma"
    elif roles:
        nombre_perfil = ", ".join(roles)
    else:
        nombre_perfil = "Usuario"

    avatar_url = (
        profile.avatar.url
        if profile and profile.avatar
        else None
    )

    # --------------------------------------------------
    # CONTEXTO
    # --------------------------------------------------

    context = {
        "organization": organization,
        "visits": visits + 1,
        "mode": request.session.get("dashboard_mode", "normal"),
        "nombre_perfil": nombre_perfil,
        "avatar_url": avatar_url,

        "mostrar_usuarios": mostrar_usuarios,
        "usuarios_total": usuarios_total,

        "mostrar_dispositivos": mostrar_dispositivos,
        "dispositivos_total": dispositivos_total,
        "productos_por_zona": productos_por_zona,

        "mostrar_mediciones": mostrar_mediciones,
        "promedio_consumo": promedio_consumo,
        "mediciones_total": mediciones_total,
        "consumo_total": consumo_total,

        "mostrar_alertas": mostrar_alertas,
        "alertas_total": alertas_total,

        "mostrar_mantenimientos": mostrar_mantenimientos,

        "charts": charts,
        "actividad": actividad,
    }

    return render(
        request,
        "dashboard/index.html",
        context
    )


@login_required
@require_POST
def remember_preference(request):

    request.session["dashboard_mode"] = "compact"

    messages.success(
        request,
        "Preferencia guardada correctamente."
    )

    return redirect("dashboard:dashboard")


@login_required
def export_dashboard_excel(request):

    from io import BytesIO
    from datetime import timedelta

    from django.http import HttpResponse
    from django.utils import timezone
    from django.db.models import Sum, Count, Avg
    from django.db.models.functions import TruncDate, ExtractHour

    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    from devices.views import (
        get_visible_devices,
        get_visible_maintenance,
    )

    user = request.user
    profile = getattr(user, "profile", None)

    if profile is None and not user.is_superuser:
        raise PermissionDenied(
            "La cuenta no posee un perfil habilitado."
        )

    organization_id = (
        profile.organization_id if profile else None
    )

    periods = {
        "semana": ("Última semana", 7),
        "mes": ("Último mes", 30),
        "semestral": ("Últimos seis meses", 182),
        "anual": ("Último año", 365),
    }

    selected_period = request.GET.get(
        "periodo",
        "semana"
    )

    if selected_period not in periods:
        selected_period = "semana"

    period_name, days = periods[selected_period]

    now = timezone.now()
    start_date = now - timedelta(days=days)

    # CONSULTAS CON ALCANCE DE PERMISOS

    if user.has_perm("devices.view_device"):
        devices = get_visible_devices(user)
    else:
        devices = Device.objects.none()

    measurements = Measurement.objects.none()

    if user.has_perm("devices.view_measurement"):
        measurements = Measurement.objects.filter(
            deleted_at__isnull=True,
            datetime__gte=start_date,
            unit__iexact="kWh",
            device__in=devices,
        ).select_related(
            "device",
            "device__zone",
            "device__zone__department",
        )

    alerts = AlertEvent.objects.none()

    if user.has_perm("devices.view_alertevent"):
        alerts = AlertEvent.objects.filter(
            deleted_at__isnull=True,
            created_at__gte=start_date,
            device__in=devices,
        )

    maintenance = MaintenanceRequest.objects.none()

    if user.has_perm("devices.view_maintenancerequest"):
        maintenance = get_visible_maintenance(
            user
        ).filter(
            created_at__gte=start_date
        )

    # DATOS DE GRÁFICOS

    chart_rows = []

    def add_chart_rows(title, queryset, label_field, unit):
        for row in queryset:
            label = row.get(label_field) or "Sin clasificar"
            value = float(row.get("total") or 0)

            chart_rows.append([
                title,
                str(label),
                value,
                unit,
            ])

    if user.has_perm("devices.view_measurement"):

        # Consumo histórico diario
        daily = (
            measurements
            .annotate(dia=TruncDate("datetime"))
            .values("dia")
            .annotate(total=Sum("value"))
            .order_by("dia")
        )

        for row in daily:
            chart_rows.append([
                "Consumo histórico",
                row["dia"].strftime("%d/%m/%Y") if row["dia"] else "Sin fecha",
                float(row["total"] or 0),
                "kWh",
            ])

        # Consumo por departamento
        department_data = (
            measurements
            .values("device__zone__department__name")
            .annotate(total=Sum("value"))
            .order_by("-total")
        )

        add_chart_rows(
            "Consumo por departamento",
            department_data,
            "device__zone__department__name",
            "kWh",
        )

        # Consumo por zona
        zone_data = (
            measurements
            .values("device__zone__name")
            .annotate(total=Sum("value"))
            .order_by("-total")
        )

        add_chart_rows(
            "Consumo por zona",
            zone_data,
            "device__zone__name",
            "kWh",
        )

        # Cinco dispositivos de mayor consumo
        top_devices = (
            measurements
            .values("device__internal_name")
            .annotate(total=Sum("value"))
            .order_by("-total")[:5]
        )

        add_chart_rows(
            "Top dispositivos",
            top_devices,
            "device__internal_name",
            "kWh",
        )

        # Demanda horaria
        hourly = (
            measurements
            .annotate(hora=ExtractHour("datetime"))
            .values("hora")
            .annotate(total=Sum("value"))
            .order_by("hora")
        )

        for row in hourly:
            chart_rows.append([
                "Demanda horaria",
                f"{row['hora']:02d}:00" if row["hora"] is not None else "Sin hora",
                float(row["total"] or 0),
                "kWh",
            ])

    # Estado actual de dispositivos
    if user.has_perm("devices.view_device"):

        device_states = (
            devices
            .values("status")
            .annotate(total=Count("pk"))
            .order_by("status")
        )

        for row in device_states:
            chart_rows.append([
                "Estado de dispositivos",
                row["status"] or "Sin estado",
                row["total"],
                "Dispositivos",
            ])

    # Estado de alertas creadas durante el período
    if user.has_perm("devices.view_alertevent"):

        alert_states = (
            alerts
            .values("status")
            .annotate(total=Count("pk"))
            .order_by("status")
        )

        for row in alert_states:
            chart_rows.append([
                "Estado de alertas",
                row["status"] or "Sin estado",
                row["total"],
                "Alertas",
            ])

    # Estado de mantenimientos creados durante el período
    if user.has_perm("devices.view_maintenancerequest"):

        maintenance_states = (
            maintenance
            .values("status")
            .annotate(total=Count("pk"))
            .order_by("status")
        )

        for row in maintenance_states:
            chart_rows.append([
                "Estado de mantenimientos",
                row["status"] or "Sin estado",
                row["total"],
                "Solicitudes",
            ])

    # ÚLTIMOS REGISTROS DE LA BITÁCORA

    activity = get_visible_activity(
        user,
        organization_id,
    ).filter(
        created_at__gte=start_date
    ).select_related(
        "actor",
        "organization",
    ).order_by("-created_at")[:15]

    # RESUMEN

    measurement_summary = measurements.aggregate(
        total=Sum("value"),
        promedio=Avg("value"),
        cantidad=Count("pk"),
    )

    # CREAR EXCEL

    workbook = Workbook()

    # HOJA 1: RESUMEN
    summary = workbook.active
    summary.title = "Resumen"

    summary.append(["INFORME ECOENERGY"])
    summary.append(["Período", period_name])
    summary.append(["Desde", timezone.localtime(start_date).replace(tzinfo=None)])
    summary.append(["Hasta", timezone.localtime(now).replace(tzinfo=None)])
    summary.append([])

    summary.append(["Indicador", "Resultado"])

    summary.append([
        "Total de mediciones",
        measurement_summary["cantidad"] or 0,
    ])

    summary.append([
        "Consumo acumulado (kWh)",
        float(measurement_summary["total"] or 0),
    ])

    summary.append([
        "Consumo promedio (kWh)",
        float(measurement_summary["promedio"] or 0),
    ])

    if user.has_perm("devices.view_device"):
        summary.append([
            "Dispositivos visibles",
            devices.count(),
        ])

    if user.has_perm("devices.view_alertevent"):
        summary.append([
            "Alertas del período",
            alerts.count(),
        ])

    if user.has_perm("devices.view_maintenancerequest"):
        summary.append([
            "Mantenimientos del período",
            maintenance.count(),
        ])

    # HOJA 2: DATOS DE LOS GRÁFICOS
    charts_sheet = workbook.create_sheet("Datos gráficos")

    charts_sheet.append([
        "Gráfico",
        "Categoría",
        "Valor",
        "Unidad",
    ])

    for row in chart_rows:
        charts_sheet.append(row)

    # HOJA 3: ÚLTIMOS REGISTROS
    activity_sheet = workbook.create_sheet("Últimos registros")

    activity_sheet.append([
        "Fecha y hora",
        "Módulo",
        "Operación",
        "Registro afectado",
        "Tipo de registro",
        "ID",
        "Responsable",
        "Organización",
    ])

    for registro in activity:
        fecha = registro.created_at

        if timezone.is_aware(fecha):
            fecha = timezone.localtime(fecha).replace(tzinfo=None)

        organizacion = ""

        if registro.organization:
            organizacion = (
                registro.organization.comercial_name
                or registro.organization.legal_name
            )

        activity_sheet.append([
            fecha,
            registro.get_module_display(),
            registro.get_action_display(),
            registro.object_label,
            registro.object_type,
            registro.object_pk,
            registro.actor_name,
            organizacion or "Global",
        ])

    # FORMATO DE LAS HOJAS
    for sheet in workbook.worksheets:

        sheet.freeze_panes = "A2"

        if sheet.max_row > 1:
            sheet.auto_filter.ref = sheet.dimensions

        for cell in sheet[1]:
            cell.font = Font(
                bold=True,
                color="FFFFFF",
            )
            cell.fill = PatternFill(
                fill_type="solid",
                fgColor="034159",
            )
            cell.alignment = Alignment(
                horizontal="center",
            )

        for column_cells in sheet.columns:
            max_length = max(
                len(str(cell.value or ""))
                for cell in column_cells
            )

            sheet.column_dimensions[
                column_cells[0].column_letter
            ].width = min(max(max_length + 3, 14), 45)

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )

    response["Content-Disposition"] = (
        f'attachment; filename="EcoEnergy_Dashboard_{selected_period}.xlsx"'
    )

    return response
