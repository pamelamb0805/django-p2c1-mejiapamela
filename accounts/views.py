from urllib.parse import urlencode

from django.shortcuts import render, redirect
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import SuspiciousOperation
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from organizations.models import Department, Organization
from organizations.views import CrudAccessMixin

from .forms import (
    ProfileAvatarForm,
    ProfileContactForm,
    ProfileDataForm,
    ProfilePasswordForm,
    UserProfileForm,
)
from .models import UserProfile
from core.pagination import PageSizeMixin

#preentrega eva 3 - PM
def registro(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya está en uso.')
        else:
            User.objects.create_user(username=username, email=email, password=password)
            messages.success(request, '¡Cuenta creada con éxito!')
            # Redirige a la URL nombrada 'login' (/accounts/login/)
            return redirect('login')
            
    return render(request, 'registration/registro.html')


# ==========================================
# M02 · USUARIOS Y PERFILES - CRUD con modal y SweetAlert2
# preentrega eva 3 - PM
# Mismo patrón que los CRUD de Dispositivos y Departamentos.
# ==========================================

def get_visible_profiles(user):
    """Perfiles activos que el usuario puede ver (scoping por organización)."""
    queryset = (
        UserProfile.objects.filter(deleted_at__isnull=True)
        .select_related("user", "organization", "department")
        .prefetch_related("user__groups")
    )
    if user.is_superuser:
        return queryset
    profile = getattr(user, "profile", None)
    if profile is None or profile.organization_id is None:
        return queryset.none()
    # Un usuario normal solo ve los perfiles de su organización y nunca los de un superusuario.
    return queryset.filter(
        organization_id=profile.organization_id, user__is_superuser=False
    )


def get_profile_filter_options(user):
    """Opciones de los filtros: departamentos, roles y (solo superusuario) organizaciones."""
    departamentos = Department.objects.filter(deleted_at__isnull=True)
    organizaciones = Organization.objects.none()
    if user.is_superuser:
        organizaciones = Organization.objects.filter(
            deleted_at__isnull=True
        ).order_by("legal_name")
    else:
        profile = getattr(user, "profile", None)
        org_id = getattr(profile, "organization_id", None)
        departamentos = departamentos.filter(organization_id=org_id) if org_id else departamentos.none()
    return departamentos.order_by("name"), Group.objects.order_by("name"), organizaciones


# Login + permiso, y consultas limitadas al ámbito del usuario.
class UserProfileAccessMixin(CrudAccessMixin):
    def get_queryset(self):
        return get_visible_profiles(self.request.user)


# Mixin para Create y Update: pasa el usuario al formulario, entrega el listado (paginado)
# detrás del modal y envía open_modal=True para abrir el modal automáticamente.
class UserProfileFormPageMixin:
    #correccion paginacion Eva3 --> PM
    page_size_session_key = "user_profile_page_size"
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        page_obj = Paginator(
            get_visible_profiles(self.request.user).order_by("user__username"), 10
        ).get_page(self.request.GET.get("page"))
        departamentos, roles, organizaciones = get_profile_filter_options(self.request.user)

        context["profiles"] = page_obj.object_list
        context["page_obj"] = page_obj
        context["is_paginated"] = page_obj.has_other_pages()
        context["departamentos"] = departamentos
        context["roles"] = roles
        context["organizaciones"] = organizaciones
        context["buscar"] = ""
        context["departamento_seleccionado"] = ""
        context["rol_seleccionado"] = ""
        context["organizacion_seleccionada"] = ""
        context["query_string"] = ""
        context["open_modal"] = True
        return context


# Listado (ListView): exige view_userprofile. Incluye buscador, filtros y paginación.
class UserProfileListView(PageSizeMixin, UserProfileAccessMixin, ListView):
    permission_required = "accounts.view_userprofile"
    template_name = "accounts/user_list.html"
    context_object_name = "profiles"
    page_size_session_key = "user_page_size"

    def get_queryset(self):
        queryset = get_visible_profiles(self.request.user)

        # Buscador general.
        buscar = self.request.GET.get("buscar", "").strip()
        if buscar:
            queryset = queryset.filter(
                Q(user__username__icontains=buscar)
                | Q(user__first_name__icontains=buscar)
                | Q(user__last_name__icontains=buscar)
                | Q(user__email__icontains=buscar)
                | Q(employee_code__icontains=buscar)
                | Q(rut__icontains=buscar)
                | Q(organization__legal_name__icontains=buscar)
            )

        # Filtro por organización (solo lo usa el superusuario).
        organizacion = self.request.GET.get("organizacion", "").strip()
        if organizacion.isdigit() and self.request.user.is_superuser:
            queryset = queryset.filter(organization_id=int(organizacion))

        # Filtro por departamento.
        departamento = self.request.GET.get("departamento", "").strip()
        if departamento.isdigit():
            queryset = queryset.filter(department_id=int(departamento))

        # Filtro por rol (grupo).
        rol = self.request.GET.get("rol", "").strip()
        if rol.isdigit():
            queryset = queryset.filter(user__groups__id=int(rol))

        return queryset.order_by("user__username")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        departamentos, roles, organizaciones = get_profile_filter_options(self.request.user)
        context["departamentos"] = departamentos
        context["roles"] = roles
        context["organizaciones"] = organizaciones

        # Mantener los valores seleccionados en los controles.
        context["buscar"] = self.request.GET.get("buscar", "")
        context["departamento_seleccionado"] = self.request.GET.get("departamento", "")
        context["rol_seleccionado"] = self.request.GET.get("rol", "")
        context["organizacion_seleccionada"] = self.request.GET.get("organizacion", "")

        # Construir enlaces de paginación conservando los filtros.
        parametros = self.request.GET.copy()
        parametros.pop("page", None)
        query_string = urlencode(parametros, doseq=True)
        context["query_string"] = f"&{query_string}" if query_string else ""

        return context


# Crear (CreateView): exige add_userprofile y reutiliza el template del listado (modal).
class UserProfileCreateView(UserProfileAccessMixin, SuccessMessageMixin, UserProfileFormPageMixin, CreateView):
    permission_required = ("accounts.view_userprofile", "accounts.add_userprofile")
    model = UserProfile
    form_class = UserProfileForm
    template_name = "accounts/user_list.html"
    success_url = reverse_lazy("accounts:user_list")
    success_message = "Usuario y perfil creados correctamente."


# Editar (UpdateView): exige change_userprofile y reutiliza el mismo UserProfileForm.
class UserProfileUpdateView(UserProfileAccessMixin, SuccessMessageMixin, UserProfileFormPageMixin, UpdateView):
    permission_required = ("accounts.view_userprofile", "accounts.change_userprofile")
    model = UserProfile
    form_class = UserProfileForm
    template_name = "accounts/user_list.html"
    success_url = reverse_lazy("accounts:user_list")
    success_message = "Usuario y perfil actualizados correctamente."


# Eliminar (DeleteView): exige delete_userprofile y recibe un POST con CSRF desde SweetAlert2.
class UserProfileDeleteView(UserProfileAccessMixin, DeleteView):
    permission_required = "accounts.delete_userprofile"
    model = UserProfile
    http_method_names = ["post"]  # solo POST: la confirmación la hace SweetAlert2
    success_url = reverse_lazy("accounts:user_list")

    # Borrado lógico del perfil y desactivación de la cuenta (is_active=False) para que
    # la persona ya no pueda iniciar sesión. Nadie puede eliminar su propio perfil.
    def form_valid(self, form):
        self.object = self.get_object()

        if self.object.user_id == self.request.user.id:
            messages.error(self.request, "No puedes eliminar tu propio perfil.")
            return HttpResponseRedirect(self.get_success_url())

        self.object.deleted_at = timezone.now()
        self.object.save(update_fields=["deleted_at", "updated_at"])

        cuenta = self.object.user
        cuenta.is_active = False
        cuenta.save(update_fields=["is_active"])

        messages.success(
            self.request, "Perfil eliminado y acceso de la cuenta desactivado correctamente."
        )
        return HttpResponseRedirect(self.get_success_url())


# ==========================================
# Perfil de usuario (Clase 9 y Evaluación Sumativa 3) --> PM
# Ninguna de estas vistas recibe un id por la URL: siempre trabajan con request.user,
# así nadie puede ver ni modificar el perfil, la foto o la contraseña de otra persona.
# ==========================================
@login_required
def perfil(request):
    """Mi perfil: muestra los datos del usuario autenticado (solo lectura)."""
    # Si la cuenta no tiene perfil (por ejemplo un superusuario recién creado), getattr devuelve None y no se rompe.
    profile = getattr(request.user, "profile", None)
    return render(request, "accounts/perfil.html", {"profile": profile})


@login_required
def perfil_editar(request):
    """Editar mi perfil: datos personales, foto y contraseña (formularios independientes, una acción por POST)."""
    # Copia fresca del usuario: si un formulario es inválido, request.user no queda con datos sin guardar
    # (por ejemplo el menú mostrando un correo que no se guardó).
    usuario = User.objects.get(pk=request.user.pk)
    profile = getattr(request.user, "profile", None)

    datos_form = ProfileDataForm(instance=usuario)
    # Teléfono y dirección viven en el perfil: solo existen si la cuenta tiene perfil.
    contacto_form = ProfileContactForm(instance=profile) if profile else None
    foto_form = ProfileAvatarForm(instance=profile) if profile else None
    password_form = ProfilePasswordForm(usuario)

    if request.method == "POST":
        # El campo oculto "accion" indica cuál de los formularios se envió.
        accion = request.POST.get("accion")

        if accion == "datos":
            datos_form = ProfileDataForm(request.POST, instance=usuario)
            contacto_form = ProfileContactForm(request.POST, instance=profile) if profile else None
            # Se validan ambos para mostrar todos los errores de una vez (sin cortar en el primero).
            datos_ok = datos_form.is_valid()
            contacto_ok = contacto_form.is_valid() if contacto_form else True
            if datos_ok and contacto_ok:
                # atomic: o se guardan los dos o no se guarda ninguno.
                with transaction.atomic():
                    datos_form.save()
                    if contacto_form:
                        contacto_form.save()
                messages.success(request, "Tus datos se actualizaron correctamente.")
                return redirect("accounts:perfil_editar")

        elif accion == "foto" and profile is not None:
            # request.FILES lleva la imagen ya recortada; el formulario HTML tiene enctype="multipart/form-data".
            foto_form = ProfileAvatarForm(request.POST, request.FILES, instance=profile)
            if foto_form.is_valid():
                foto_form.save()
                messages.success(request, "Tu foto de perfil se actualizó correctamente.")
                return redirect("accounts:perfil_editar")

        elif accion == "password":
            password_form = ProfilePasswordForm(usuario, request.POST)
            if password_form.is_valid():
                usuario = password_form.save()
                # Cambiar la contraseña invalida la sesión; esto la renueva para que el usuario no sea expulsado.
                update_session_auth_hash(request, usuario)
                messages.success(request, "Tu contraseña se cambió correctamente.")
                return redirect("accounts:perfil_editar")

        else:
            # Acción inventada o manipulada: Django responde 400 (solicitud inválida).
            raise SuspiciousOperation("Acción de perfil no válida.")

    return render(request, "accounts/perfil_editar.html", {
        "profile": profile,
        "datos_form": datos_form,
        "contacto_form": contacto_form,
        "foto_form": foto_form,
        "password_form": password_form,
    })