#correccion eva2-n3
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from django.shortcuts import render
from .forms import ArchiveDevicesForm
from .models import Device
from organizations.models import Zone


def zone_list(request):
    # Obtiene todas las zonas desde la aplicación organizations
    zones = Zone.objects.all()
    return render(request, 'devices/zone_list.html', {'zones': zones})


def zone_detail(request, pk):
    zone = get_object_or_404(Zone, pk=pk)
    devices = Device.objects.filter(zone=zone) if hasattr(Device, 'zone') else []
    
    # Cálculo de consumo para la vista de detalle
    total_kwh = sum(getattr(d, 'kwh', 0) for d in devices)
    limit = getattr(zone, 'limit_kwh', 0)
    status = "ALERTA" if total_kwh > limit else "NORMAL"
    
    context = {
        'zone': zone,
        'devices': devices,
        'total_kwh': total_kwh,
        'count': len(devices),
        'status': status,
    }
    return render(request, 'devices/zone_detail.html', context)


def get_visible_devices(user):
    """Dispositivos activos que el usuario puede ver (scoping por organización)."""
    qs = Device.objects.filter(deleted_at__isnull=True).select_related(
        "product", "zone"
    )
    if user.is_superuser:
        return qs
    profile = getattr(user, "profile", None)
    # Sin perfil u organización: no ve nada (nunca acceso global por error)
    if profile is None or profile.organization_id is None:
        return qs.none()
    return qs.filter(zone__organization=profile.organization)


@login_required
@permission_required("devices.view_device", raise_exception=True)
def device_list(request):
    devices = get_visible_devices(request.user)
    can_archive = request.user.has_perm("devices.change_device")

    if request.method == "POST":
        if not can_archive:
            raise PermissionDenied
        form = ArchiveDevicesForm(request.POST, queryset=devices)
        if form.is_valid():
            now = timezone.now()
            updated = form.cleaned_data["devices"].update(
                deleted_at=now, updated_at=now
            )
            messages.success(request, f"{updated} dispositivo(s) archivado(s).")
        else:
            messages.error(request, "Selecciona al menos un dispositivo válido.")
        return redirect("devices:device_list")

    return render(
        request,
        "devices/device_list.html",
        {"devices": devices, "can_archive": can_archive},
    )

@login_required
def indicators_view(request):
    """Vista de indicadores de consumo requerida por el dashboard."""
    profile = getattr(request.user, "profile", None)
    
    if request.user.is_superuser:
        devices = Device.objects.filter(deleted_at__isnull=True)
    elif profile and profile.organization:
        devices = Device.objects.filter(zone__organization=profile.organization, deleted_at__isnull=True)
    else:
        devices = Device.objects.none()

    # Cálculo básico de consumo total
    total_consumption = sum(getattr(d, 'kwh', 0) for d in devices)

    context = {
        'devices': devices,
        'total_consumption': total_consumption,
    }
    return render(request, 'devices/indicators.html', context)