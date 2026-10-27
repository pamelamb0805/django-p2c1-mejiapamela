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
from organizations.models import Zone

from django.db.models import Count, Sum
from .forms import CategoryForm, DeviceForm, MeasurementForm, ProductForm
from .models import AlertEvent, Catalog, Product, AlertRule, Device, History, MaintenanceRequest, Measurement
#revisar importacion alert
from urllib.parse import urlencode
from django.db.models import Q
from django.core.paginator import Paginator
from .forms import (
    ALERT_STATUS_CHOICES,
    MAINTENANCE_PRIORITY_CHOICES,
    MAINTENANCE_STATUS_CHOICES,
    AlertEventForm,
    CatalogForm,
    DeviceForm,
    MaintenanceRequestForm,
    MeasurementForm,
)
from .models import AlertEvent, AlertRule, Catalog, Device, History, MaintenanceRequest, Measurement

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

#preentrega eva 3 PM --> CRUD Categorias
# ---------- CRUD de Categorías (modelo Catalog) ----------
def get_visible_categories(user):
    """Categorías activas. Son globales, el acceso se controla por permisos."""
    return Catalog.objects.filter(deleted_at__isnull=True)


class CategoryAccessMixin(LoginRequiredMixin, PermissionRequiredMixin):
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
        return get_visible_categories(self.request.user)


class CategoryFormPageMixin:
    """Comparte el listado y abre el modal de crear o editar."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        categorias = get_visible_categories(self.request.user)

        context["categories"] = categorias.annotate(
            products_count=Count("products", filter=Q(products__deleted_at__isnull=True))
        ).order_by("name")
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


class CategoryListView(CategoryAccessMixin, ListView):
    permission_required = "devices.view_catalog"
    template_name = "devices/category_list.html"
    context_object_name = "categories"
    paginate_by = 10

    def get_queryset(self):
        queryset = get_visible_categories(self.request.user)

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

        return queryset.annotate(
            products_count=Count("products", filter=Q(products__deleted_at__isnull=True))
        ).order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        categorias_visibles = get_visible_categories(self.request.user)

        context["buscar"] = self.request.GET.get("buscar", "")
        context["estado_seleccionado"] = self.request.GET.get("estado", "")

        parametros = self.request.GET.copy()
        parametros.pop("page", None)
        query_string = urlencode(parametros, doseq=True)
        context["query_string"] = f"&{query_string}" if query_string else ""

        context["estados"] = (
            categorias_visibles.exclude(status__isnull=True)
            .exclude(status__exact="")
            .values_list("status", flat=True)
            .distinct()
            .order_by("status")
        )
        return context


class CategoryCreateView(CategoryAccessMixin, SuccessMessageMixin, CategoryFormPageMixin, CreateView):
    permission_required = ("devices.view_catalog", "devices.add_catalog")
    model = Catalog
    form_class = CategoryForm
    template_name = "devices/category_list.html"
    success_url = reverse_lazy("devices:category_list")
    success_message = "Categoría creada correctamente."


class CategoryUpdateView(CategoryAccessMixin, SuccessMessageMixin, CategoryFormPageMixin, UpdateView):
    permission_required = ("devices.view_catalog", "devices.change_catalog")
    model = Catalog
    form_class = CategoryForm
    template_name = "devices/category_list.html"
    success_url = reverse_lazy("devices:category_list")
    success_message = "Categoría actualizada correctamente."


class CategoryDeleteView(CategoryAccessMixin, DeleteView):
    permission_required = "devices.delete_catalog"
    model = Catalog
    template_name = "devices/category_confirm_delete.html"
    success_url = reverse_lazy("devices:category_list")

    def form_valid(self, form):
        self.object = self.get_object()

        # No se elimina una categoría que todavía tiene productos activos.
        if self.object.products.filter(deleted_at__isnull=True).exists():
            messages.error(
                self.request,
                "No se puede eliminar la categoría porque tiene productos asociados.",
            )
            return HttpResponseRedirect(self.get_success_url())

        self.object.deleted_at = timezone.now()
        self.object.save(update_fields=["deleted_at", "updated_at"])
        messages.success(self.request, "Categoría eliminada correctamente.")
        return HttpResponseRedirect(self.get_success_url())


# ---------- CRUD de Productos ----------
def get_visible_products(user):
    """Productos activos. Son globales, el acceso se controla por permisos."""
    return Product.objects.filter(deleted_at__isnull=True).select_related("catalog")


class ProductAccessMixin(CategoryAccessMixin):
    def get_queryset(self):
        return get_visible_products(self.request.user)


def _product_filter_context(request):
    productos = get_visible_products(request.user)
    return {
        "categorias": Catalog.objects.filter(
            pk__in=productos.values("catalog_id"), deleted_at__isnull=True
        ).order_by("name"),
        "buscar": request.GET.get("buscar", ""),
        "categoria_seleccionada": request.GET.get("categoria", ""),
    }


class ProductFormPageMixin:
    """Comparte el listado y abre el modal de crear o editar."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["products"] = get_visible_products(self.request.user).order_by("name")
        context.update(_product_filter_context(self.request))
        context["open_modal"] = True
        return context


class ProductListView(ProductAccessMixin, ListView):
    permission_required = "devices.view_product"
    template_name = "devices/product_list.html"
    context_object_name = "products"
    paginate_by = 10

    def get_queryset(self):
        queryset = get_visible_products(self.request.user)

        buscar = self.request.GET.get("buscar", "").strip()
        if buscar:
            queryset = queryset.filter(
                Q(product_id__icontains=buscar)
                | Q(sku__icontains=buscar)
                | Q(name__icontains=buscar)
                | Q(manufacturer__icontains=buscar)
                | Q(model__icontains=buscar)
            )

        categoria = self.request.GET.get("categoria", "").strip()
        if categoria.isdigit():
            queryset = queryset.filter(catalog_id=int(categoria))

        return queryset.order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_product_filter_context(self.request))

        parametros = self.request.GET.copy()
        parametros.pop("page", None)
        query_string = urlencode(parametros, doseq=True)
        context["query_string"] = f"&{query_string}" if query_string else ""
        return context


class ProductCreateView(ProductAccessMixin, SuccessMessageMixin, ProductFormPageMixin, CreateView):
    permission_required = ("devices.view_product", "devices.add_product")
    model = Product
    form_class = ProductForm
    template_name = "devices/product_list.html"
    success_url = reverse_lazy("devices:product_list")
    success_message = "Producto creado correctamente."


class ProductUpdateView(ProductAccessMixin, SuccessMessageMixin, ProductFormPageMixin, UpdateView):
    permission_required = ("devices.view_product", "devices.change_product")
    model = Product
    form_class = ProductForm
    template_name = "devices/product_list.html"
    success_url = reverse_lazy("devices:product_list")
    success_message = "Producto actualizado correctamente."


class ProductDeleteView(ProductAccessMixin, DeleteView):
    permission_required = "devices.delete_product"
    model = Product
    template_name = "devices/product_confirm_delete.html"
    success_url = reverse_lazy("devices:product_list")

    def form_valid(self, form):
        self.object = self.get_object()

        en_uso = (
            self.object.devices.filter(deleted_at__isnull=True).exists()
            or self.object.alert_rules.filter(deleted_at__isnull=True).exists()
        )
        if en_uso:
            messages.error(
                self.request,
                "No se puede eliminar el producto porque está asociado a dispositivos o reglas de alerta.",
            )
            return HttpResponseRedirect(self.get_success_url())

        self.object.deleted_at = timezone.now()
        self.object.save(update_fields=["deleted_at", "updated_at"])
        messages.success(self.request, "Producto eliminado correctamente.")
        return HttpResponseRedirect(self.get_success_url())
    
# ---------- Clase 6 (PM): zonas, indicadores y mantenimiento ----------
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

#preentrega eva 3 PM --> def indicadores de consumo
@login_required
@permission_required("devices.view_measurement", raise_exception=True)
def indicators_view(request):
    """Indicadores de consumo: resumen y totales de mediciones por zona y producto."""
    dispositivos = get_visible_devices(request.user)
    mediciones = Measurement.objects.filter(
        deleted_at__isnull=True, device__in=dispositivos
    )

    por_zona = (
        mediciones.values("device__zone__name", "unit")
        .annotate(total=Sum("value"), lecturas=Count("id"))
        .order_by("device__zone__name", "unit")
    )
    por_producto = (
        mediciones.values("device__product__name", "unit")
        .annotate(total=Sum("value"), lecturas=Count("id"))
        .order_by("-total")[:10]
    )

    context = {
        "total_dispositivos": dispositivos.count(),
        "total_mediciones": mediciones.count(),
        "total_alertas": AlertEvent.objects.filter(
            deleted_at__isnull=True, device__in=dispositivos
        ).count(),
        "por_zona": por_zona,
        "por_producto": por_producto,
    }
    return render(request, "devices/indicators.html", context)

#pre entrega eva 3 PM --> vistas measurement-mediciones
# ---------- CRUD de Mediciones (basado en el CRUD de Dispositivos) ----------
def get_visible_measurements(user):
    """Mediciones activas de los dispositivos que el usuario puede ver."""
    return Measurement.objects.filter(
        deleted_at__isnull=True,
        device__in=get_visible_devices(user),
    ).select_related("device", "device__zone", "user")


# Login + permiso (hereda de DeviceAccessMixin) y consultas limitadas al ámbito del usuario.
class MeasurementAccessMixin(DeviceAccessMixin):
    def get_queryset(self):
        return get_visible_measurements(self.request.user)


# Opciones de los filtros del listado: dispositivos visibles y estados existentes.
def get_measurement_filter_options(user):
    return {
        "dispositivos": get_visible_devices(user).order_by("internal_name"),
        "estados": (
            get_visible_measurements(user)
            .exclude(status__isnull=True)
            .exclude(status__exact="")
            .values_list("status", flat=True)
            .distinct()
            .order_by("status")
        ),
    }


# Mixin para Create y Update: pasa el usuario al formulario, entrega el listado (paginado)
# detrás del modal y envía open_modal=True para abrir el modal automáticamente.
class MeasurementFormPageMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        page_obj = Paginator(
            get_visible_measurements(self.request.user).order_by("-datetime"), 10
        ).get_page(self.request.GET.get("page"))

        context["measurements"] = page_obj.object_list
        context["page_obj"] = page_obj
        context["is_paginated"] = page_obj.has_other_pages()
        context.update(get_measurement_filter_options(self.request.user))
        context["buscar"] = ""
        context["estado_seleccionado"] = ""
        context["dispositivo_seleccionado"] = ""
        context["query_string"] = ""
        context["open_modal"] = True
        return context


# Listado (ListView): exige view_measurement. Incluye buscador, dos filtros y paginación.
class MeasurementListView(MeasurementAccessMixin, ListView):
    permission_required = "devices.view_measurement"
    template_name = "devices/measurement_list.html"
    context_object_name = "measurements"
    paginate_by = 10

    def get_queryset(self):
        queryset = get_visible_measurements(self.request.user)

        # Buscador general.
        buscar = self.request.GET.get("buscar", "").strip()
        if buscar:
            queryset = queryset.filter(
                Q(measurement_id__icontains=buscar)
                | Q(device__device_id__icontains=buscar)
                | Q(device__internal_name__icontains=buscar)
                | Q(unit__icontains=buscar)
                | Q(origin__icontains=buscar)
            )

        # Filtro por estado.
        estado = self.request.GET.get("estado", "").strip()
        if estado:
            queryset = queryset.filter(status__iexact=estado)

        # Filtro por dispositivo.
        dispositivo = self.request.GET.get("dispositivo", "").strip()
        if dispositivo.isdigit():
            queryset = queryset.filter(device_id=int(dispositivo))

        return queryset.order_by("-datetime")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Mantener los valores seleccionados en los controles.
        context["buscar"] = self.request.GET.get("buscar", "")
        context["estado_seleccionado"] = self.request.GET.get("estado", "")
        context["dispositivo_seleccionado"] = self.request.GET.get("dispositivo", "")
        context.update(get_measurement_filter_options(self.request.user))

        # Construir enlaces de paginación conservando los filtros.
        parametros = self.request.GET.copy()
        parametros.pop("page", None)
        query_string = urlencode(parametros, doseq=True)
        context["query_string"] = f"&{query_string}" if query_string else ""

        return context


# Crear (CreateView): exige add_measurement. Guarda quién registró la medición.
class MeasurementCreateView(MeasurementAccessMixin, SuccessMessageMixin, MeasurementFormPageMixin, CreateView):
    permission_required = ("devices.view_measurement", "devices.add_measurement")
    model = Measurement
    form_class = MeasurementForm
    template_name = "devices/measurement_list.html"
    success_url = reverse_lazy("devices:measurement_list")
    success_message = "Medición registrada correctamente."

    def form_valid(self, form):
        form.instance.user = self.request.user  # el servidor decide el registrador, no el formulario
        return super().form_valid(form)


# Editar (UpdateView): exige change_measurement y reutiliza el mismo MeasurementForm.
class MeasurementUpdateView(MeasurementAccessMixin, SuccessMessageMixin, MeasurementFormPageMixin, UpdateView):
    permission_required = ("devices.view_measurement", "devices.change_measurement")
    model = Measurement
    form_class = MeasurementForm
    template_name = "devices/measurement_list.html"
    success_url = reverse_lazy("devices:measurement_list")
    success_message = "Medición actualizada correctamente."


# Eliminar (DeleteView): exige delete_measurement y recibe un POST con CSRF desde SweetAlert2.
class MeasurementDeleteView(MeasurementAccessMixin, DeleteView):
    permission_required = "devices.delete_measurement"
    model = Measurement
    http_method_names = ["post"]  # solo POST: la confirmación la hace SweetAlert2
    success_url = reverse_lazy("devices:measurement_list")

    # Borrado lógico. Si tiene eventos de alerta activos asociados, no se elimina.
    def form_valid(self, form):
        self.object = self.get_object()
        if self.object.alert_events.filter(deleted_at__isnull=True).exists():
            messages.error(
                self.request,
                "No se puede eliminar la medición porque tiene alertas asociadas.",
            )
            return HttpResponseRedirect(self.get_success_url())
        self.object.deleted_at = timezone.now()
        self.object.save(update_fields=["deleted_at", "updated_at"])
        messages.success(self.request, "Medición eliminada correctamente.")
        return HttpResponseRedirect(self.get_success_url())


# ---------- CRUD de Alertas (modelo AlertEvent, basado en el CRUD de Dispositivos) ----------
def get_visible_alerts(user):
    """Alertas activas de los dispositivos que el usuario puede ver."""
    return AlertEvent.objects.filter(
        deleted_at__isnull=True,
        device__in=get_visible_devices(user),
    ).select_related(
        "device", "measurement", "alert_rule", "acknowledged_by", "resolved_by"
    )


# Login + permiso (hereda de DeviceAccessMixin) y consultas limitadas al ámbito del usuario.
class AlertAccessMixin(DeviceAccessMixin):
    def get_queryset(self):
        return get_visible_alerts(self.request.user)


# Opciones de los filtros del listado: estados fijos y severidades de las reglas en uso.
def get_alert_filter_options(user):
    return {
        "estados": ALERT_STATUS_CHOICES,
        "severidades": (
            AlertRule.objects.filter(alert_events__in=get_visible_alerts(user))
            .exclude(severity__exact="")
            .values_list("severity", flat=True)
            .distinct()
            .order_by("severity")
        ),
    }


# Mixin de Create y Update: el servidor registra quién y cuándo reconoce o resuelve la alerta.
class AlertStatusMixin:
    def form_valid(self, form):
        alerta = form.instance
        estado = form.cleaned_data["status"]
        ahora = timezone.now()

        if estado == "abierta":
            alerta.acknowledged_by = alerta.acknowledged_at = None
            alerta.resolved_by = alerta.resolved_at = None
        else:
            if alerta.acknowledged_at is None:
                alerta.acknowledged_by = self.request.user
                alerta.acknowledged_at = ahora
            if estado == "resuelta":
                if alerta.resolved_at is None:
                    alerta.resolved_by = self.request.user
                    alerta.resolved_at = ahora
            else:  # reconocida: si se reabre desde "resuelta", se limpia la resolución
                alerta.resolved_by = alerta.resolved_at = None

        return super().form_valid(form)


# Mixin para Create y Update: pasa el usuario al formulario, entrega el listado (paginado)
# detrás del modal y envía open_modal=True para abrir el modal automáticamente.
class AlertFormPageMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        page_obj = Paginator(
            get_visible_alerts(self.request.user).order_by("-created_at"), 10
        ).get_page(self.request.GET.get("page"))

        context["alerts"] = page_obj.object_list
        context["page_obj"] = page_obj
        context["is_paginated"] = page_obj.has_other_pages()
        context.update(get_alert_filter_options(self.request.user))
        context["buscar"] = ""
        context["estado_seleccionado"] = ""
        context["severidad_seleccionada"] = ""
        context["query_string"] = ""
        context["open_modal"] = True
        return context


# Listado (ListView): exige view_alertevent. Incluye buscador, dos filtros y paginación.
class AlertListView(AlertAccessMixin, ListView):
    permission_required = "devices.view_alertevent"
    template_name = "devices/alert_list.html"
    context_object_name = "alerts"
    paginate_by = 10

    def get_queryset(self):
        queryset = get_visible_alerts(self.request.user)

        # Buscador general.
        buscar = self.request.GET.get("buscar", "").strip()
        if buscar:
            queryset = queryset.filter(
                Q(alert_event_id__icontains=buscar)
                | Q(device__device_id__icontains=buscar)
                | Q(device__internal_name__icontains=buscar)
                | Q(alert_rule__name__icontains=buscar)
                | Q(measurement__measurement_id__icontains=buscar)
                | Q(observations__icontains=buscar)
            )

        # Filtro por estado.
        estado = self.request.GET.get("estado", "").strip()
        if estado:
            queryset = queryset.filter(status__iexact=estado)

        # Filtro por severidad de la regla.
        severidad = self.request.GET.get("severidad", "").strip()
        if severidad:
            queryset = queryset.filter(alert_rule__severity__iexact=severidad)

        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Mantener los valores seleccionados en los controles.
        context["buscar"] = self.request.GET.get("buscar", "")
        context["estado_seleccionado"] = self.request.GET.get("estado", "")
        context["severidad_seleccionada"] = self.request.GET.get("severidad", "")
        context.update(get_alert_filter_options(self.request.user))

        # Construir enlaces de paginación conservando los filtros.
        parametros = self.request.GET.copy()
        parametros.pop("page", None)
        query_string = urlencode(parametros, doseq=True)
        context["query_string"] = f"&{query_string}" if query_string else ""

        return context

#preentrega eva 3 --> PM -- CRUD ALERTAS
# Crear (CreateView): exige add_alertevent.
class AlertCreateView(AlertAccessMixin, SuccessMessageMixin, AlertStatusMixin, AlertFormPageMixin, CreateView):
    permission_required = ("devices.view_alertevent", "devices.add_alertevent")
    model = AlertEvent
    form_class = AlertEventForm
    template_name = "devices/alert_list.html"
    success_url = reverse_lazy("devices:alert_list")
    success_message = "Alerta registrada correctamente."


# Editar (UpdateView): exige change_alertevent. Aquí se reconoce o resuelve una alerta.
class AlertUpdateView(AlertAccessMixin, SuccessMessageMixin, AlertStatusMixin, AlertFormPageMixin, UpdateView):
    permission_required = ("devices.view_alertevent", "devices.change_alertevent")
    model = AlertEvent
    form_class = AlertEventForm
    template_name = "devices/alert_list.html"
    success_url = reverse_lazy("devices:alert_list")
    success_message = "Alerta actualizada correctamente."


# Eliminar (DeleteView): exige delete_alertevent y recibe un POST con CSRF desde SweetAlert2.
class AlertDeleteView(AlertAccessMixin, DeleteView):
    permission_required = "devices.delete_alertevent"
    model = AlertEvent
    http_method_names = ["post"]  # solo POST: la confirmación la hace SweetAlert2
    success_url = reverse_lazy("devices:alert_list")

    # Borrado lógico: marca deleted_at en vez de borrar el registro.
    def form_valid(self, form):
        self.object = self.get_object()
        self.object.deleted_at = timezone.now()
        self.object.save(update_fields=["deleted_at", "updated_at"])
        messages.success(self.request, "Alerta eliminada correctamente.")
        return HttpResponseRedirect(self.get_success_url())

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

#preentrega eva 3 --> PM -- CRUD MANTENIMIENTO
# ---------- CRUD de Mantenimiento (modelo MaintenanceRequest, basado en el CRUD de Dispositivos) ----------
def get_visible_maintenance(user):
    """Solicitudes activas de la organización del usuario (el superusuario ve todas)."""
    qs = MaintenanceRequest.objects.filter(deleted_at__isnull=True).select_related(
        "device", "device__zone", "organization", "request_by", "assigned_to"
    )
    if user.is_superuser:
        return qs
    profile = getattr(user, "profile", None)
    # Sin perfil u organización: no ve nada (nunca acceso global por error)
    if profile is None or profile.organization_id is None:
        return qs.none()
    return qs.filter(organization_id=profile.organization_id)


# Login + permiso (hereda de DeviceAccessMixin) y consultas limitadas al ámbito del usuario.
class MaintenanceAccessMixin(DeviceAccessMixin):
    def get_queryset(self):
        return get_visible_maintenance(self.request.user)


# Opciones de los filtros del listado: estados y prioridades controlados.
def get_maintenance_filter_options(user):
    return {
        "estados": MAINTENANCE_STATUS_CHOICES,
        "prioridades": MAINTENANCE_PRIORITY_CHOICES,
    }


# Mixin de Create y Update: el servidor decide la organización, quién solicita y la fecha de cierre.
class MaintenanceServerFieldsMixin:
    def form_valid(self, form):
        solicitud = form.instance

        # La organización sale del dispositivo elegido (ya filtrado al ámbito del usuario).
        solicitud.organization = form.cleaned_data["device"].zone.organization

        # Quién solicita se guarda solo al crear.
        if solicitud.pk is None:
            solicitud.request_by = self.request.user

        # RN-14: la fecha de cierre la pone el servidor al pasar a "cerrada".
        if form.cleaned_data["status"] == "cerrada":
            if solicitud.closed_at is None:
                solicitud.closed_at = timezone.now()
        else:
            solicitud.closed_at = None  # si se reabre, se limpia el cierre

        return super().form_valid(form)


# Mixin para Create y Update: pasa el usuario al formulario, entrega el listado (paginado)
# detrás del modal y envía open_modal=True para abrir el modal automáticamente.
class MaintenanceFormPageMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        page_obj = Paginator(
            get_visible_maintenance(self.request.user).order_by("-created_at"), 10
        ).get_page(self.request.GET.get("page"))

        context["maintenance_requests"] = page_obj.object_list
        context["page_obj"] = page_obj
        context["is_paginated"] = page_obj.has_other_pages()
        context.update(get_maintenance_filter_options(self.request.user))
        context["buscar"] = ""
        context["estado_seleccionado"] = ""
        context["prioridad_seleccionada"] = ""
        context["query_string"] = ""
        context["open_modal"] = True
        return context


# Listado (ListView): exige view_maintenancerequest. Incluye buscador, dos filtros y paginación.
class MaintenanceListView(MaintenanceAccessMixin, ListView):
    permission_required = "devices.view_maintenancerequest"
    template_name = "devices/maintenance_list.html"
    context_object_name = "maintenance_requests"
    paginate_by = 10

    def get_queryset(self):
        queryset = get_visible_maintenance(self.request.user)

        # Buscador general.
        buscar = self.request.GET.get("buscar", "").strip()
        if buscar:
            queryset = queryset.filter(
                Q(maintenance_request_id__icontains=buscar)
                | Q(device__device_id__icontains=buscar)
                | Q(device__internal_name__icontains=buscar)
                | Q(reason__icontains=buscar)
                | Q(request_type__icontains=buscar)
                | Q(assigned_to__username__icontains=buscar)
            )

        # Filtro por estado.
        estado = self.request.GET.get("estado", "").strip()
        if estado:
            queryset = queryset.filter(status__iexact=estado)

        # Filtro por prioridad.
        prioridad = self.request.GET.get("prioridad", "").strip()
        if prioridad:
            queryset = queryset.filter(priority__iexact=prioridad)

        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Mantener los valores seleccionados en los controles.
        context["buscar"] = self.request.GET.get("buscar", "")
        context["estado_seleccionado"] = self.request.GET.get("estado", "")
        context["prioridad_seleccionada"] = self.request.GET.get("prioridad", "")
        context.update(get_maintenance_filter_options(self.request.user))

        # Construir enlaces de paginación conservando los filtros.
        parametros = self.request.GET.copy()
        parametros.pop("page", None)
        query_string = urlencode(parametros, doseq=True)
        context["query_string"] = f"&{query_string}" if query_string else ""

        return context


# Crear (CreateView): exige add_maintenancerequest.
class MaintenanceCreateView(MaintenanceAccessMixin, SuccessMessageMixin, MaintenanceServerFieldsMixin, MaintenanceFormPageMixin, CreateView):
    permission_required = ("devices.view_maintenancerequest", "devices.add_maintenancerequest")
    model = MaintenanceRequest
    form_class = MaintenanceRequestForm
    template_name = "devices/maintenance_list.html"
    success_url = reverse_lazy("devices:maintenance_list")
    success_message = "Solicitud de mantenimiento registrada correctamente."


# Editar (UpdateView): exige change_maintenancerequest. Aquí se asigna, se programa y se cierra.
class MaintenanceUpdateView(MaintenanceAccessMixin, SuccessMessageMixin, MaintenanceServerFieldsMixin, MaintenanceFormPageMixin, UpdateView):
    permission_required = ("devices.view_maintenancerequest", "devices.change_maintenancerequest")
    model = MaintenanceRequest
    form_class = MaintenanceRequestForm
    template_name = "devices/maintenance_list.html"
    success_url = reverse_lazy("devices:maintenance_list")
    success_message = "Solicitud de mantenimiento actualizada correctamente."


# Eliminar (DeleteView): exige delete_maintenancerequest y recibe un POST con CSRF desde SweetAlert2.
class MaintenanceDeleteView(MaintenanceAccessMixin, DeleteView):
    permission_required = "devices.delete_maintenancerequest"
    model = MaintenanceRequest
    http_method_names = ["post"]  # solo POST: la confirmación la hace SweetAlert2
    success_url = reverse_lazy("devices:maintenance_list")

    # Borrado lógico. Una solicitud cerrada es parte del historial (RF-29) y no se elimina.
    def form_valid(self, form):
        self.object = self.get_object()
        if (self.object.status or "").lower() == "cerrada":
            messages.error(
                self.request,
                "No se puede eliminar una solicitud cerrada: queda como historial de mantenimiento.",
            )
            return HttpResponseRedirect(self.get_success_url())
        self.object.deleted_at = timezone.now()
        self.object.save(update_fields=["deleted_at", "updated_at"])
        messages.success(self.request, "Solicitud de mantenimiento eliminada correctamente.")
        return HttpResponseRedirect(self.get_success_url())