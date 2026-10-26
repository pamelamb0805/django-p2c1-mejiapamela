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

from .forms import OrganizationForm
from .models import Organization, Department, Zone


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
class OrganizationListView(OrganizationAccessMixin, ListView):
    permission_required = "organizations.view_organization"
    template_name = "organizations/organization_list.html"
    context_object_name = "organizations"
    paginate_by = 10

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
# ==========================================

@login_required
def department_list(request):
    """Listado de departamentos filtrados por la organización del usuario (RN-01)."""
    profile = getattr(request.user, "profile", None)
    
    if request.user.is_superuser:
        departments = Department.objects.filter(deleted_at__isnull=True)
    elif profile and profile.organization:
        departments = Department.objects.filter(organization=profile.organization, deleted_at__isnull=True)
    else:
        departments = Department.objects.none()

    return render(request, 'organizations/department_list.html', {'departments': departments})


@login_required
def department_create(request):
    """Creación de departamentos dentro de la organización del usuario."""
    profile = getattr(request.user, "profile", None)
    organization = getattr(profile, "organization", None) if profile else None

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        
        # Validación de nombre duplicado en el mismo contexto organizacional (RN-05)
        if Department.objects.filter(organization=organization, name=name, deleted_at__isnull=True).exists():
            messages.error(request, "Ya existe un departamento con ese nombre en tu organización.")
        else:
            Department.objects.create(
                organization=organization,
                name=name,
                description=description
            )
            messages.success(request, "Departamento registrado exitosamente.")
            return redirect('organizations:department_list')

    return render(request, 'organizations/department_form.html')


# ==========================================
# 3. ZONAS FÍSICAS (RF-03, RN-02, RN-05)
# ==========================================

@login_required
def zone_list(request):
    """Listado de zonas pertenecientes a la estructura interna de la organización."""
    profile = getattr(request.user, "profile", None)
    
    if request.user.is_superuser:
        zones = Zone.objects.filter(deleted_at__isnull=True)
    elif profile and profile.organization:
        zones = Zone.objects.filter(organization=profile.organization, deleted_at__isnull=True)
    else:
        zones = Zone.objects.none()

    return render(request, 'organizations/zone_list.html', {'zones': zones})


@login_required
def zone_create(request):
    """Creación de zonas asociadas a la organización y departamento opcional (RF-03)."""
    profile = getattr(request.user, "profile", None)
    organization = getattr(profile, "organization", None) if profile else None

    if request.method == 'POST':
        name = request.POST.get('name')
        limit_kwh = request.POST.get('limit_kwh', 0.0)
        department_id = request.POST.get('department_id')
        
        department = Department.objects.filter(id=department_id, organization=organization).first() if department_id else None

        # Validación RN-05 (nombres únicos dentro del contexto organizacional)
        if Zone.objects.filter(organization=organization, name=name, deleted_at__isnull=True).exists():
            messages.error(request, "Ya existe una zona con ese nombre en tu organización.")
        else:
            Zone.objects.create(
                organization=organization,
                department=department,
                name=name,
                limit_kwh=limit_kwh
            )
            messages.success(request, "Zona creada exitosamente.")
            return redirect('organizations:zone_list')

    departments = Department.objects.filter(organization=organization, deleted_at__isnull=True) if organization else []
    return render(request, 'organizations/zone_form.html', {'departments': departments})