from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import DeviceForm
from organizations.models import Zone

from .models import Device, MaintenanceRequest


def get_visible_devices(user):
    """Dispositivos activos que el usuario puede ver (scoping por organización)."""
    qs = Device.objects.filter(deleted_at__isnull=True).select_related(
        "product", "zone"
    )
    if user.is_superuser:
        return qs
    profile = getattr(user, "profile", None)
    if profile is None or profile.organization_id is None:
        return qs.none()
    return qs.filter(zone__organization=profile.organization)


# ---------- Clase 7: operación por pk ----------
@login_required
@permission_required("devices.view_device", raise_exception=True)
def device_detail(request, pk):
    device = get_object_or_404(get_visible_devices(request.user), pk=pk)
    return render(request, "devices/device_detail.html", {"device": device})


# ---------- Clase 8: CRUD ----------
# Mixin base del CRUD: exige login y permiso, y limita las consultas a los dispositivos del ámbito del usuario.
# Clase 8 - Alexander
class DeviceAccessMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Login + permiso; y solo dispositivos del ámbito del usuario."""

    raise_exception = True

    # Con raise_exception=True el anónimo también recibiría 403;
    # por eso: anónimo -> redirige al login, autenticado sin permiso -> 403.
    # Clase 8 - Alexander
    def handle_no_permission(self):
        # Anónimo -> login; autenticado sin permiso -> 403
        if not self.request.user.is_authenticated:
            return redirect_to_login(
                self.request.get_full_path(),
                self.get_login_url(),
                self.get_redirect_field_name(),
            )
        raise PermissionDenied

    def get_queryset(self):
        return get_visible_devices(self.request.user)

# Mixin para Create y Update: pasa el usuario al formulario, entrega el listado detrás del modal
# y envía open_modal=True para abrir el modal automáticamente.
# Clase 8 - Alexander
class DeviceFormPageMixin:
    """Create/Update: mismo listado detrás del modal, modal abierto, zonas acotadas."""

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["devices"] = get_visible_devices(self.request.user)
        context["open_modal"] = True
        return context

# Listado (ListView): exige el permiso view_device.
# Clase 8 - Alexander
class DeviceListView(DeviceAccessMixin, ListView):
    permission_required = "devices.view_device"
    template_name = "devices/device_list.html"
    context_object_name = "devices"

# Crear (CreateView): exige add_device y reutiliza DeviceForm y el mismo template del listado (modal).
# Clase 8 - Alexander
class DeviceCreateView(DeviceAccessMixin, SuccessMessageMixin, DeviceFormPageMixin, CreateView):
    permission_required = ("devices.view_device", "devices.add_device")
    model = Device
    form_class = DeviceForm
    template_name = "devices/device_list.html"
    success_url = reverse_lazy("devices:device_list")
    success_message = "Dispositivo creado correctamente."

# Editar (UpdateView): exige change_device y reutiliza el mismo DeviceForm.
# Clase 8 - Alexander
class DeviceUpdateView(DeviceAccessMixin, SuccessMessageMixin, DeviceFormPageMixin, UpdateView):
    permission_required = ("devices.view_device", "devices.change_device")
    model = Device
    form_class = DeviceForm
    template_name = "devices/device_list.html"
    success_url = reverse_lazy("devices:device_list")
    success_message = "Dispositivo actualizado correctamente."

# Eliminar (DeleteView): exige delete_device y recibe un POST con CSRF desde SweetAlert2.
# Clase 8 - Alexander
class DeviceDeleteView(DeviceAccessMixin, DeleteView):
    permission_required = "devices.delete_device"
    model = Device
    template_name = "devices/device_confirm_delete.html"
    success_url = reverse_lazy("devices:device_list")

    # Borrado lógico: marca deleted_at en vez de borrar el registro (coherente con BaseModel).
    # Clase 8 - Alexander
    def form_valid(self, form):
        # Borrado lógico, coherente con BaseModel.deleted_at
        self.object = self.get_object()
        self.object.deleted_at = timezone.now()
        self.object.save(update_fields=["deleted_at", "updated_at"])
        messages.success(self.request, "Dispositivo eliminado correctamente.")
        return HttpResponseRedirect(self.get_success_url())


# ---------- Clase 6 (compañera): zonas, indicadores y mantenimiento ----------
@login_required
def zone_list(request):
    # Obtiene todas las zonas desde la aplicación organizations
    zones = Zone.objects.all()
    return render(request, "devices/zone_list.html", {"zones": zones})


@login_required
def zone_detail(request, pk):
    zone = get_object_or_404(Zone, pk=pk)
    devices = Device.objects.filter(zone=zone) if hasattr(Device, "zone") else []

    # Cálculo de consumo para la vista de detalle
    total_kwh = sum(getattr(d, "kwh", 0) for d in devices)
    limit = getattr(zone, "limit_kwh", 0)
    status = "ALERTA" if total_kwh > limit else "NORMAL"

    context = {
        "zone": zone,
        "devices": devices,
        "total_kwh": total_kwh,
        "count": len(devices),
        "status": status,
    }
    return render(request, "devices/zone_detail.html", context)


@login_required
def indicators_view(request):
    """Vista de indicadores de consumo requerida por el dashboard."""
    profile = getattr(request.user, "profile", None)

    if request.user.is_superuser:
        devices = Device.objects.filter(deleted_at__isnull=True)
    elif profile and profile.organization:
        devices = Device.objects.filter(
            zone__organization=profile.organization, deleted_at__isnull=True
        )
    else:
        devices = Device.objects.none()

    # Cálculo básico de consumo total
    total_consumption = sum(getattr(d, "kwh", 0) for d in devices)

    context = {
        "devices": devices,
        "total_consumption": total_consumption,
    }
    return render(request, "devices/indicators.html", context)


@login_required
def maintenance_list(request):
    requests = MaintenanceRequest.objects.filter(deleted_at__isnull=True)
    return render(request, "devices/maintenance_list.html", {"requests": requests})
