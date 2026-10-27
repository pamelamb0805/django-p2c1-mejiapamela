from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import DeviceForm
from organizations.models import Zone

from .models import Device, MaintenanceRequest
#revisar importacion alert
from urllib.parse import urlencode
from django.db.models import Q
from django.core.paginator import Paginator
from .forms import CatalogForm, DeviceForm, MeasurementForm
from .models import AlertEvent, Catalog, Device, History, MaintenanceRequest, Measurement

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
# Clase 8 - Alexander --> actualizacion preentrega eva 3 --> PM

class DeviceFormPageMixin:
    """Comparte el listado y abre el modal de crear o editar."""

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        dispositivos = get_visible_devices(self.request.user)

        context["devices"] = dispositivos
        context["zonas"] = Zone.objects.filter(
            pk__in=dispositivos.values("zone_id"),
            deleted_at__isnull=True,
        ).distinct().order_by("name")

        context["estados"] = (
            dispositivos.exclude(status__isnull=True)
            .exclude(status__exact="")
            .values_list("status", flat=True)
            .distinct()
            .order_by("status")
        )

        context["buscar"] = self.request.GET.get("buscar", "")
        context["estado_seleccionado"] = self.request.GET.get(
            "estado", ""
        )
        context["zona_seleccionada"] = self.request.GET.get("zona", "")
        context["open_modal"] = True

        return context


# Listado (ListView): exige el permiso view_device.
# Clase 8 - Alexander

class DeviceListView(DeviceAccessMixin, ListView):
    permission_required = "devices.view_device"
    template_name = "devices/device_list.html"
    context_object_name = "devices"
    paginate_by = 10

    def get_queryset(self):
        # Solo dispositivos activos y autorizados para el usuario.
        queryset = get_visible_devices(self.request.user)

        # Buscador general.
        buscar = self.request.GET.get("buscar", "").strip()
        if buscar:
            queryset = queryset.filter(
                Q(device_id__icontains=buscar)
                | Q(internal_name__icontains=buscar)
                | Q(serial_number__icontains=buscar)
                | Q(product__name__icontains=buscar)
                | Q(product__sku__icontains=buscar)
            )

        # Filtro por estado.
        estado = self.request.GET.get("estado", "").strip()
        if estado:
            queryset = queryset.filter(status__iexact=estado)

        # Filtro por zona.
        zona = self.request.GET.get("zona", "").strip()
        if zona.isdigit():
            queryset = queryset.filter(zone_id=int(zona))

        return queryset.select_related(
            "product", "zone", "zone__organization"
        ).order_by("internal_name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Las zonas disponibles respetan el ámbito de acceso del usuario.
        dispositivos_visibles = get_visible_devices(self.request.user)

        context["zonas"] = (
            Zone.objects.filter(
                pk__in=dispositivos_visibles.values("zone_id"),
                deleted_at__isnull=True,
            )
            .distinct()
            .order_by("name")
        )

        # Mantener los valores seleccionados en los controles.
        context["buscar"] = self.request.GET.get("buscar", "")
        context["estado_seleccionado"] = self.request.GET.get(
            "estado", ""
        )
        context["zona_seleccionada"] = self.request.GET.get("zona", "")

        # Construir enlaces de paginación conservando los filtros.
        parametros = self.request.GET.copy()
        parametros.pop("page", None)
        query_string = urlencode(parametros, doseq=True)

        context["query_string"] = (
            f"&{query_string}" if query_string else ""
        )

        context["estados"] = (
            dispositivos_visibles.exclude(status__isnull=True)
            .exclude(status__exact="")
            .values_list("status", flat=True)
            .distinct()
            .order_by("status")
        )

        return context


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

#pre entrega eva 3 --> vistas
@login_required
@permission_required("devices.view_measurement", raise_exception=True)
def measurement_list(request):
    measurements = Measurement.objects.filter(
        deleted_at__isnull=True,
        device__in=get_visible_devices(request.user),
    ).select_related("device")
    return render(request, "devices/measurement_list.html", {"measurements": measurements})


@login_required
@permission_required("devices.add_measurement", raise_exception=True)
def measurement_create(request):
    form = MeasurementForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        measurement = form.save(commit=False)
        measurement.user = request.user
        measurement.save()
        messages.success(request, "Medición registrada correctamente.")
        return redirect("devices:measurement_list")
    return render(request, "devices/measurement_form.html", {"form": form})


@login_required
@permission_required("devices.view_alertevent", raise_exception=True)
def alert_list(request):
    alerts = AlertEvent.objects.filter(
        deleted_at__isnull=True,
        device__in=get_visible_devices(request.user),
    ).select_related("device")
    return render(request, "devices/alert_list.html", {"alerts": alerts})


@login_required
def history_list(request):
    history = History.objects.filter(
        deleted_at__isnull=True,
        device__in=get_visible_devices(request.user),
    ).select_related("device")
    return render(request, "devices/history_list.html", {"history": history})

#preentrega eva 3 --> PM -- CRUD CATEGORIAS
def get_visible_catalogs():
    """Categorías activas (el catálogo es global: no depende de la organización)."""
    return Catalog.objects.filter(deleted_at__isnull=True)


class CatalogAccessMixin(LoginRequiredMixin, PermissionRequiredMixin):
    raise_exception = True

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect_to_login(
                self.request.get_full_path(),
                self.get_login_url(),
                self.get_redirect_field_name(),
            )
        raise PermissionDenied

    def get_queryset(self):
        return get_visible_catalogs()


class CatalogFormPageMixin:
    """Entrega el listado detrás del modal y abre el modal de crear o editar."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        categorias = get_visible_catalogs()

        context["catalogs"] = categorias.order_by("name")
        context["estados"] = (
            categorias.exclude(status__isnull=True)
            .exclude(status__exact="")
            .values_list("status", flat=True)
            .distinct()
            .order_by("status")
        )
        context["buscar"] = self.request.GET.get("buscar", "")
        context["estado_seleccionado"] = self.request.GET.get("estado", "")
        context["open_modal"] = True
        return context


class CatalogListView(CatalogAccessMixin, ListView):
    permission_required = "devices.view_catalog"
    template_name = "devices/catalog_list.html"
    context_object_name = "catalogs"
    paginate_by = 10

    def get_queryset(self):
        queryset = get_visible_catalogs()

        buscar = self.request.GET.get("buscar", "").strip()
        if buscar:
            queryset = queryset.filter(
                Q(catalog_id__icontains=buscar)
                | Q(name__icontains=buscar)
                | Q(description__icontains=buscar)
            )

        estado = self.request.GET.get("estado", "").strip()
        if estado:
            queryset = queryset.filter(status__iexact=estado)

        return queryset.order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        visibles = get_visible_catalogs()

        context["buscar"] = self.request.GET.get("buscar", "")
        context["estado_seleccionado"] = self.request.GET.get("estado", "")

        parametros = self.request.GET.copy()
        parametros.pop("page", None)
        query_string = urlencode(parametros, doseq=True)
        context["query_string"] = f"&{query_string}" if query_string else ""

        context["estados"] = (
            visibles.exclude(status__isnull=True)
            .exclude(status__exact="")
            .values_list("status", flat=True)
            .distinct()
            .order_by("status")
        )
        return context


class CatalogCreateView(CatalogAccessMixin, SuccessMessageMixin, CatalogFormPageMixin, CreateView):
    permission_required = ("devices.view_catalog", "devices.add_catalog")
    model = Catalog
    form_class = CatalogForm
    template_name = "devices/catalog_list.html"
    success_url = reverse_lazy("devices:catalog_list")
    success_message = "Categoría creada correctamente."


class CatalogUpdateView(CatalogAccessMixin, SuccessMessageMixin, CatalogFormPageMixin, UpdateView):
    permission_required = ("devices.view_catalog", "devices.change_catalog")
    model = Catalog
    form_class = CatalogForm
    template_name = "devices/catalog_list.html"
    success_url = reverse_lazy("devices:catalog_list")
    success_message = "Categoría actualizada correctamente."


class CatalogDeleteView(CatalogAccessMixin, DeleteView):
    permission_required = "devices.delete_catalog"
    model = Catalog
    template_name = "devices/catalog_confirm_delete.html"
    success_url = reverse_lazy("devices:catalog_list")

    def form_valid(self, form):
        self.object = self.get_object()
        # Regla extra: no se elimina una categoría que aún tiene productos activos
        if self.object.products.filter(deleted_at__isnull=True).exists():
            messages.error(self.request, "No se puede eliminar: la categoría tiene productos activos.")
            return HttpResponseRedirect(self.get_success_url())
        self.object.deleted_at = timezone.now()
        self.object.save(update_fields=["deleted_at", "updated_at"])
        messages.success(self.request, "Categoría eliminada correctamente.")
        return HttpResponseRedirect(self.get_success_url())