from urllib.parse import urlencode

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import DepartmentForm, OrganizationForm, ZoneForm
from .models import Organization, Department, Zone
from core.pagination import PageSizeMixin 

# ==========================================
# 1. ORGANIZACIONES (RF-01, RF-04)
#Avance preentrega eva 3 - PM --> Basado en Crud Dispositivos
# ==========================================


def get_visible_organizations(user):
    """Organizaciones activas que el usuario puede ver (scoping por organización)."""
    queryset = Organization.objects.filter(deleted_at__isnull=True)
    if user.is_superuser:
        return queryset
    profile = getattr(user, "profile", None)
    if profile is None or profile.organization_id is None:
        return queryset.none()
    # Un usuario normal solo ve su propia organización.
    return queryset.filter(pk=profile.organization_id)


# Mixin base de los CRUD de este módulo: exige login y permiso.
class CrudAccessMixin(LoginRequiredMixin, PermissionRequiredMixin):
    raise_exception = True

    # Con raise_exception=True el anónimo también recibiría 403;
    # por eso: anónimo -> redirige al login, autenticado sin permiso -> 403.
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect_to_login(
                self.request.get_full_path(),
                self.get_login_url(),
                self.get_redirect_field_name(),
            )
        raise PermissionDenied


# Además de login y permiso, limita las consultas a las organizaciones del ámbito del usuario.
class OrganizationAccessMixin(CrudAccessMixin):
    def get_queryset(self):
        return get_visible_organizations(self.request.user)


# Mixin para Create y Update: entrega el listado (paginado) detrás del modal
# y envía open_modal=True para abrir el modal automáticamente.
class OrganizationFormPageMixin:
    #correccion paginacion Eva3 --> PM
    page_size_session_key = "organization_page_size"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        page_obj = Paginator(
            get_visible_organizations(self.request.user).order_by("legal_name"), 10
        ).get_page(self.request.GET.get("page"))

        context["organizations"] = page_obj.object_list
        context["page_obj"] = page_obj
        context["is_paginated"] = page_obj.has_other_pages()
        context["buscar"] = ""
        context["estado_seleccionado"] = ""
        context["query_string"] = ""
        context["open_modal"] = True
        return context


# Listado (ListView): exige view_organization. Incluye buscador, filtro por estado y paginación.
class OrganizationListView(PageSizeMixin,OrganizationAccessMixin, ListView):
    permission_required = "organizations.view_organization"
    template_name = "organizations/organization_list.html"
    context_object_name = "organizations"
    page_size_session_key = "organization_page_size"

    def get_queryset(self):
        # Solo organizaciones activas y autorizadas para el usuario.
        queryset = get_visible_organizations(self.request.user)

        # Buscador general.
        buscar = self.request.GET.get("buscar", "").strip()
        if buscar:
            queryset = queryset.filter(
                Q(organization_id__icontains=buscar)
                | Q(legal_name__icontains=buscar)
                | Q(comercial_name__icontains=buscar)
                | Q(tax__icontains=buscar)
                | Q(email__icontains=buscar)
                | Q(contact__icontains=buscar)
            )

        # Filtro por estado: "1" = activas, "0" = inactivas.
        estado = self.request.GET.get("estado", "").strip()
        if estado in ("0", "1"):
            queryset = queryset.filter(status=(estado == "1"))

        return queryset.order_by("legal_name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Mantener los valores seleccionados en los controles.
        context["buscar"] = self.request.GET.get("buscar", "")
        context["estado_seleccionado"] = self.request.GET.get("estado", "")

        # Construir enlaces de paginación conservando los filtros.
        parametros = self.request.GET.copy()
        parametros.pop("page", None)
        query_string = urlencode(parametros, doseq=True)
        context["query_string"] = f"&{query_string}" if query_string else ""

        return context


# Crear (CreateView): exige add_organization y reutiliza el template del listado (modal).
class OrganizationCreateView(OrganizationAccessMixin, SuccessMessageMixin, OrganizationFormPageMixin, CreateView):
    permission_required = ("organizations.view_organization", "organizations.add_organization")
    model = Organization
    form_class = OrganizationForm
    template_name = "organizations/organization_list.html"
    success_url = reverse_lazy("organizations:organization_list")
    success_message = "Organización creada correctamente."


# Editar (UpdateView): exige change_organization y reutiliza el mismo OrganizationForm.
class OrganizationUpdateView(OrganizationAccessMixin, SuccessMessageMixin, OrganizationFormPageMixin, UpdateView):
    permission_required = ("organizations.view_organization", "organizations.change_organization")
    model = Organization
    form_class = OrganizationForm
    template_name = "organizations/organization_list.html"
    success_url = reverse_lazy("organizations:organization_list")
    success_message = "Organización actualizada correctamente."


# Eliminar (DeleteView): exige delete_organization y recibe un POST con CSRF desde SweetAlert2.
class OrganizationDeleteView(OrganizationAccessMixin, DeleteView):
    permission_required = "organizations.delete_organization"
    model = Organization
    http_method_names = ["post"]  # solo POST: la confirmación la hace SweetAlert2
    success_url = reverse_lazy("organizations:organization_list")

    # Borrado lógico: marca deleted_at en vez de borrar el registro (coherente con BaseModel).
    # Si la organización aún tiene datos activos asociados, no se elimina.
    def form_valid(self, form):
        self.object = self.get_object()

        dependencias = []
        if self.object.departments.filter(deleted_at__isnull=True).exists():
            dependencias.append("departamentos")
        if self.object.zones.filter(deleted_at__isnull=True).exists():
            dependencias.append("zonas")
        if self.object.user_profiles.filter(deleted_at__isnull=True).exists():
            dependencias.append("perfiles de usuario")
        if self.object.maintenance_requests.filter(deleted_at__isnull=True).exists():
            dependencias.append("solicitudes de mantenimiento")

        if dependencias:
            messages.error(
                self.request,
                "No se puede eliminar la organización porque tiene "
                + ", ".join(dependencias)
                + " asociados.",
            )
            return HttpResponseRedirect(self.get_success_url())

        self.object.deleted_at = timezone.now()
        self.object.save(update_fields=["deleted_at", "updated_at"])
        messages.success(self.request, "Organización eliminada correctamente.")
        return HttpResponseRedirect(self.get_success_url())

# ==========================================
# 2. DEPARTAMENTOS (RF-02, RN-02, RN-05)
#preentrega eva 3 - PM
# ==========================================


def get_visible_departments(user):
    """Departamentos activos que el usuario puede ver (scoping por organización)."""
    queryset = Department.objects.filter(deleted_at__isnull=True).select_related(
        "organization", "user"
    )
    if user.is_superuser:
        return queryset
    profile = getattr(user, "profile", None)
    if profile is None or profile.organization_id is None:
        return queryset.none()
    # Un usuario normal solo ve los departamentos de su organización.
    return queryset.filter(organization_id=profile.organization_id)


# Login + permiso, y consultas limitadas al ámbito del usuario.
class DepartmentAccessMixin(CrudAccessMixin):
    def get_queryset(self):
        return get_visible_departments(self.request.user)


# Mixin para Create y Update: pasa el usuario al formulario, entrega el listado (paginado)
# detrás del modal y envía open_modal=True para abrir el modal automáticamente.
class DepartmentFormPageMixin:
    #correccion paginacion Eva3 --> PM
    page_size_session_key = "department_page_size"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        page_obj = Paginator(
            get_visible_departments(self.request.user).order_by("name"), 10
        ).get_page(self.request.GET.get("page"))

        context["departments"] = page_obj.object_list
        context["page_obj"] = page_obj
        context["is_paginated"] = page_obj.has_other_pages()
        context["buscar"] = ""
        context["estado_seleccionado"] = ""
        context["query_string"] = ""
        context["open_modal"] = True
        return context


# Listado (ListView): exige view_department. Incluye buscador, filtro por estado y paginación.
class DepartmentListView(PageSizeMixin, DepartmentAccessMixin, ListView):
    permission_required = "organizations.view_department"
    template_name = "organizations/department_list.html"
    context_object_name = "departments"
    page_size_session_key = "department_page_size"

    def get_queryset(self):
        queryset = get_visible_departments(self.request.user)

        # Buscador general.
        buscar = self.request.GET.get("buscar", "").strip()
        if buscar:
            queryset = queryset.filter(
                Q(department_id__icontains=buscar)
                | Q(name__icontains=buscar)
                | Q(description__icontains=buscar)
                | Q(organization__legal_name__icontains=buscar)
                | Q(user__username__icontains=buscar)
            )

        # Filtro por estado: "1" = activos, "0" = inactivos.
        estado = self.request.GET.get("estado", "").strip()
        if estado in ("0", "1"):
            queryset = queryset.filter(status=(estado == "1"))

        return queryset.order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Mantener los valores seleccionados en los controles.
        context["buscar"] = self.request.GET.get("buscar", "")
        context["estado_seleccionado"] = self.request.GET.get("estado", "")

        # Construir enlaces de paginación conservando los filtros.
        parametros = self.request.GET.copy()
        parametros.pop("page", None)
        query_string = urlencode(parametros, doseq=True)
        context["query_string"] = f"&{query_string}" if query_string else ""

        return context


# Crear (CreateView): exige add_department y reutiliza el template del listado (modal).
class DepartmentCreateView(DepartmentAccessMixin, SuccessMessageMixin, DepartmentFormPageMixin, CreateView):
    permission_required = ("organizations.view_department", "organizations.add_department")
    model = Department
    form_class = DepartmentForm
    template_name = "organizations/department_list.html"
    success_url = reverse_lazy("organizations:department_list")
    success_message = "Departamento creado correctamente."


# Editar (UpdateView): exige change_department y reutiliza el mismo DepartmentForm.
class DepartmentUpdateView(DepartmentAccessMixin, SuccessMessageMixin, DepartmentFormPageMixin, UpdateView):
    permission_required = ("organizations.view_department", "organizations.change_department")
    model = Department
    form_class = DepartmentForm
    template_name = "organizations/department_list.html"
    success_url = reverse_lazy("organizations:department_list")
    success_message = "Departamento actualizado correctamente."


# Eliminar (DeleteView): exige delete_department y recibe un POST con CSRF desde SweetAlert2.
class DepartmentDeleteView(DepartmentAccessMixin, DeleteView):
    permission_required = "organizations.delete_department"
    model = Department
    http_method_names = ["post"]  # solo POST: la confirmación la hace SweetAlert2
    success_url = reverse_lazy("organizations:department_list")

    # Borrado lógico. Si aún tiene zonas, usuarios o perfiles activos asociados, no se elimina.
    def form_valid(self, form):
        self.object = self.get_object()

        dependencias = []
        if self.object.zones.filter(deleted_at__isnull=True).exists():
            dependencias.append("zonas")
        if self.object.users.filter(deleted_at__isnull=True).exists():
            dependencias.append("usuarios")
        if self.object.user_profiles.filter(deleted_at__isnull=True).exists():
            dependencias.append("perfiles de usuario")

        if dependencias:
            messages.error(
                self.request,
                "No se puede eliminar el departamento porque tiene "
                + ", ".join(dependencias)
                + " asociados.",
            )
            return HttpResponseRedirect(self.get_success_url())

        self.object.deleted_at = timezone.now()
        self.object.save(update_fields=["deleted_at", "updated_at"])
        messages.success(self.request, "Departamento eliminado correctamente.")
        return HttpResponseRedirect(self.get_success_url())
# ==========================================
# 3. ZONAS FÍSICAS (RF-03, RN-02, RN-05)
# preentrega eva 3 - PM
# ==========================================

def get_visible_zones(user):
    """Zonas activas que el usuario puede ver (scoping por organización)."""
    queryset = Zone.objects.filter(deleted_at__isnull=True).select_related(
        "organization", "department"
    )
    if user.is_superuser:
        return queryset
    profile = getattr(user, "profile", None)
    if profile is None or profile.organization_id is None:
        return queryset.none()
    # Un usuario normal solo ve las zonas de su organización.
    return queryset.filter(organization_id=profile.organization_id)


# Departamentos que el usuario puede usar en el filtro del listado.
def get_zone_filter_departments(user):
    return get_visible_departments(user).order_by("name")


# Login + permiso, y consultas limitadas al ámbito del usuario.
class ZoneAccessMixin(CrudAccessMixin):
    def get_queryset(self):
        return get_visible_zones(self.request.user)


# Mixin para Create y Update: pasa el usuario al formulario, entrega el listado (paginado)
# detrás del modal y envía open_modal=True para abrir el modal automáticamente.
class ZoneFormPageMixin:
    #correccion paginacion Eva3 --> PM
    page_size_session_key = "zone_page_size"
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        page_obj = Paginator(
            get_visible_zones(self.request.user).order_by("name"), 10
        ).get_page(self.request.GET.get("page"))

        context["zones"] = page_obj.object_list
        context["page_obj"] = page_obj
        context["is_paginated"] = page_obj.has_other_pages()
        context["departamentos"] = get_zone_filter_departments(self.request.user)
        context["buscar"] = ""
        context["estado_seleccionado"] = ""
        context["departamento_seleccionado"] = ""
        context["query_string"] = ""
        context["open_modal"] = True
        return context


# Listado (ListView): exige view_zone. Incluye buscador, dos filtros (estado y departamento) y paginación.
class ZoneListView(PageSizeMixin, ZoneAccessMixin, ListView):
    permission_required = "organizations.view_zone"
    template_name = "organizations/zone_list.html"
    context_object_name = "zones"
    page_size_session_key = "zone_page_size"

    def get_queryset(self):
        queryset = get_visible_zones(self.request.user)

        # Buscador general.
        buscar = self.request.GET.get("buscar", "").strip()
        if buscar:
            queryset = queryset.filter(
                Q(zone_id__icontains=buscar)
                | Q(name__icontains=buscar)
                | Q(description__icontains=buscar)
                | Q(organization__legal_name__icontains=buscar)
                | Q(department__name__icontains=buscar)
            )

        # Filtro por estado: "1" = activas, "0" = inactivas.
        estado = self.request.GET.get("estado", "").strip()
        if estado in ("0", "1"):
            queryset = queryset.filter(status=(estado == "1"))

        # Filtro por departamento.
        departamento = self.request.GET.get("departamento", "").strip()
        if departamento.isdigit():
            queryset = queryset.filter(department_id=int(departamento))

        return queryset.order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Mantener los valores seleccionados en los controles.
        context["buscar"] = self.request.GET.get("buscar", "")
        context["estado_seleccionado"] = self.request.GET.get("estado", "")
        context["departamento_seleccionado"] = self.request.GET.get("departamento", "")
        context["departamentos"] = get_zone_filter_departments(self.request.user)

        # Construir enlaces de paginación conservando los filtros.
        parametros = self.request.GET.copy()
        parametros.pop("page", None)
        query_string = urlencode(parametros, doseq=True)
        context["query_string"] = f"&{query_string}" if query_string else ""

        return context


# Crear (CreateView): exige add_zone y reutiliza el template del listado (modal).
class ZoneCreateView(ZoneAccessMixin, SuccessMessageMixin, ZoneFormPageMixin, CreateView):
    permission_required = ("organizations.view_zone", "organizations.add_zone")
    model = Zone
    form_class = ZoneForm
    template_name = "organizations/zone_list.html"
    success_url = reverse_lazy("organizations:zone_list")
    success_message = "Zona creada correctamente."


# Editar (UpdateView): exige change_zone y reutiliza el mismo ZoneForm.
class ZoneUpdateView(ZoneAccessMixin, SuccessMessageMixin, ZoneFormPageMixin, UpdateView):
    permission_required = ("organizations.view_zone", "organizations.change_zone")
    model = Zone
    form_class = ZoneForm
    template_name = "organizations/zone_list.html"
    success_url = reverse_lazy("organizations:zone_list")
    success_message = "Zona actualizada correctamente."


# Eliminar (DeleteView): exige delete_zone y recibe un POST con CSRF desde SweetAlert2.
class ZoneDeleteView(ZoneAccessMixin, DeleteView):
    permission_required = "organizations.delete_zone"
    model = Zone
    http_method_names = ["post"]  # solo POST: la confirmación la hace SweetAlert2
    success_url = reverse_lazy("organizations:zone_list")

    # Borrado lógico. Si aún tiene dispositivos o historial activos asociados, no se elimina.
    def form_valid(self, form):
        self.object = self.get_object()

        dependencias = []
        if self.object.devices.filter(deleted_at__isnull=True).exists():
            dependencias.append("dispositivos")
        if self.object.histories.filter(deleted_at__isnull=True).exists():
            dependencias.append("registros de historial")

        if dependencias:
            messages.error(
                self.request,
                "No se puede eliminar la zona porque tiene "
                + ", ".join(dependencias)
                + " asociados.",
            )
            return HttpResponseRedirect(self.get_success_url())

        self.object.deleted_at = timezone.now()
        self.object.save(update_fields=["deleted_at", "updated_at"])
        messages.success(self.request, "Zona eliminada correctamente.")
        return HttpResponseRedirect(self.get_success_url())