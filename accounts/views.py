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
from .models import UserProfile, PasswordResetCode
from core.pagination import PageSizeMixin

from websocket.mixins import WebSocketCrudEventsMixin
import hashlib
import hmac
import secrets

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction

#Eva 3 - PM

# Eva 3 - Registro de usuarios PM
def registro(request):
    if request.method == "POST":

        # Datos enviados desde registration/registro.html
        nombre = request.POST.get("nombre", "").strip()
        apellido = request.POST.get("apellido", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("pswd", "")
        password_confirm = request.POST.get("pswd-repeat", "")

        # Validaciones del lado del servidor.
        if not nombre or not apellido or not email or not password:
            messages.error(
                request,
                "Debes completar todos los campos obligatorios."
            )
            return render(
                request,
                "registration/registro.html"
            )

        if User.objects.filter(email__iexact=email).exists():
            messages.error(
                request,
                "Este correo electrónico ya está registrado."
            )
            return render(
                request,
                "registration/registro.html"
            )

        if User.objects.filter(username__iexact=email).exists():
            messages.error(
                request,
                "Este correo electrónico ya está asociado a una cuenta."
            )
            return render(
                request,
                "registration/registro.html"
            )

        if password != password_confirm:
            messages.error(
                request,
                "Las contraseñas no coinciden."
            )
            return render(
                request,
                "registration/registro.html"
            )

        # El correo se utiliza como nombre de usuario.
        nuevo_usuario = User(
            username=email,
            email=email,
            first_name=nombre,
            last_name=apellido,
        )

        # Aplicar validadores de contraseña configurados en Django.
        try:
            validate_password(password, nuevo_usuario)

        except ValidationError as error:
            for mensaje in error.messages:
                messages.error(request, mensaje)

            return render(
                request,
                "registration/registro.html"
            )

        # Crear usuario y perfil en una sola transacción.
        try:
            with transaction.atomic():

                nuevo_usuario = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=nombre,
                    last_name=apellido,
                    is_active=False,
                )

                # Crear perfil pendiente de asignación administrativa.
                UserProfile.objects.create(
                    user=nuevo_usuario
                )

            messages.success(
                request,
                "¡Cuenta creada con éxito! "
                "Tu cuenta está pendiente de aprobación "
                "por un administrador."
            )

            return redirect("login")

        except Exception:
            messages.error(
                request,
                "No fue posible completar el registro. "
                "Inténtalo nuevamente."
            )

            return render(
                request,
                "registration/registro.html"
            )

    return render(
        request,
        "registration/registro.html"
    )

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


# Crear usuario y perfil.
class UserProfileCreateView(
    WebSocketCrudEventsMixin,
    UserProfileAccessMixin,
    SuccessMessageMixin,
    UserProfileFormPageMixin,
    CreateView
):
    crud_module = "usuarios"
    crud_action = "creado"

    permission_required = (
        "accounts.view_userprofile",
        "accounts.add_userprofile"
    )

    model = UserProfile
    form_class = UserProfileForm
    template_name = "accounts/user_list.html"

    success_url = reverse_lazy("accounts:user_list")

    success_message = (
        "Usuario y perfil creados correctamente."
    )


# Modificar usuario y perfil.
class UserProfileUpdateView(
    WebSocketCrudEventsMixin,
    UserProfileAccessMixin,
    SuccessMessageMixin,
    UserProfileFormPageMixin,
    UpdateView
):
    crud_module = "usuarios"
    crud_action = "actualizado"

    permission_required = (
        "accounts.view_userprofile",
        "accounts.change_userprofile"
    )

    model = UserProfile
    form_class = UserProfileForm
    template_name = "accounts/user_list.html"

    success_url = reverse_lazy("accounts:user_list")

    success_message = (
        "Usuario y perfil actualizados correctamente."
    )


# Eliminar usuario y perfil.
class UserProfileDeleteView(
    WebSocketCrudEventsMixin,
    UserProfileAccessMixin,
    DeleteView
):
    crud_module = "usuarios"
    crud_action = "eliminado"

    permission_required = "accounts.delete_userprofile"

    model = UserProfile
    http_method_names = ["post"]

    success_url = reverse_lazy("accounts:user_list")

    def form_valid(self, form):

        self.object = self.get_object()

        # Evitar que el usuario elimine su propio perfil.
        if self.object.user_id == self.request.user.id:

            messages.error(
                self.request,
                "No puedes eliminar tu propio perfil."
            )

            return HttpResponseRedirect(
                self.get_success_url()
            )

        # Guardar el perfil antes de desactivar la cuenta.
        self.object.deleted_at = timezone.now()

        self.object.save(
            update_fields=[
                "deleted_at",
                "updated_at"
            ]
        )

        cuenta = self.object.user

        cuenta.is_active = False

        cuenta.save(
            update_fields=["is_active"]
        )

        # Registrar la eliminación en la bitácora.
        self.publish_crud_notification("eliminado")

        messages.success(
            self.request,
            "Perfil eliminado y acceso de la cuenta desactivado correctamente."
        )

        return HttpResponseRedirect(
            self.get_success_url()
        )

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

#Eva3 recuperar contrasenia --> PM

# ============================================================
# RECUPERACIÓN DE CONTRASEÑA - ECOENERGY
# Códigos persistentes en base de datos.
# ============================================================

RESET_SESSION_KEY = "ecoenergy_password_reset"


def _enmascarar_correo(email):
    """Oculta parte del correo electrónico."""
    try:
        usuario, dominio = email.split("@", 1)

        if len(usuario) <= 2:
            usuario_oculto = usuario[0] + "*"
        else:
            usuario_oculto = usuario[:2] + "*" * (len(usuario) - 2)

        return f"{usuario_oculto}@{dominio}"

    except (ValueError, IndexError):
        return email


def _generar_hash_codigo(codigo):
    """Genera un hash seguro del código usando la SECRET_KEY."""
    contenido = f"{codigo}{settings.SECRET_KEY}"
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()


def _obtener_ttl_reset():
    """Duración del código en segundos, configurable desde settings.py."""
    return getattr(settings, "PASSWORD_RESET_CODE_TTL", 120)


def _obtener_max_intentos():
    """Cantidad máxima de intentos permitidos por código."""
    return getattr(settings, "PASSWORD_RESET_MAX_ATTEMPTS", 5)


def recuperar_password(request):
    """
    Paso 1: recibe el correo y genera un código de recuperación.
    Los códigos anteriores del usuario quedan invalidados.
    """

    if request.method == "POST":

        email = request.POST.get("email", "").strip().lower()

        if not email:
            messages.error(
                request,
                "Debes ingresar un correo electrónico."
            )
            return render(
                request,
                "registration/recover_password.html",
                {"paso": "ingresar_correo"},
            )

        User = get_user_model()

        usuario = User.objects.filter(
            email__iexact=email,
            is_active=True
        ).first()

        # Reiniciar los datos anteriores de esta solicitud.
        request.session.pop(RESET_SESSION_KEY, None)

        codigo_id = None

        if usuario:

            ahora = timezone.now()

            # Invalidar códigos anteriores que todavía no se han usado.
            PasswordResetCode.objects.filter(
                user=usuario,
                is_used=False
            ).update(is_used=True)

            # Generar código aleatorio de seis dígitos.
            codigo = f"{secrets.randbelow(900000) + 100000:06d}"

            # Crear el registro persistente.
            registro_codigo = PasswordResetCode.objects.create(
                user=usuario,
                code_hash=_generar_hash_codigo(codigo),
                expires_at=ahora + timedelta(
                    seconds=_obtener_ttl_reset()
                ),
            )

            # Enviar el código al correo registrado.
            enviado = send_mail(
                subject="Código de recuperación - EcoEnergy",
                message=(
                    f"Hola {usuario.get_username()},\n\n"
                    f"Tu código de recuperación es: {codigo}\n\n"
                    f"Este código vence en "
                    f"{_obtener_ttl_reset()} segundos.\n\n"
                    "Si no solicitaste este cambio, puedes ignorar "
                    "este correo."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[usuario.email],
                fail_silently=True,
            )

            # Si el envío falla, eliminar el código recién creado.
            if enviado:
                codigo_id = registro_codigo.pk
            else:
                registro_codigo.delete()

        # Solo se guarda el identificador, nunca el código en texto plano.
        request.session[RESET_SESSION_KEY] = {
            "codigo_id": codigo_id,
            "email": email,
            "verificado": False,
        }

        # Mensaje genérico para no revelar si existe la cuenta.
        messages.success(
            request,
            "Si el correo está registrado, recibirás un código de recuperación."
        )

        return render(
            request,
            "registration/recover_password.html",
            {
                "paso": "verificar_codigo",
                "email": email,
                "email_enmascarado": _enmascarar_correo(email),
            },
        )

    return render(
        request,
        "registration/recover_password.html",
        {"paso": "ingresar_correo"},
    )


def verificar_codigo_reset(request):
    """
    Paso 2: verifica el código almacenado en la base de datos.
    Controla expiración, uso único e intentos.
    """

    if request.method != "POST":
        return redirect("accounts:recuperar_password")

    datos = request.session.get(RESET_SESSION_KEY)

    if not datos:
        messages.error(
            request,
            "La solicitud de recuperación expiró. Solicita un nuevo código."
        )
        return redirect("accounts:recuperar_password")

    codigo_id = datos.get("codigo_id")

    if not codigo_id:
        messages.error(
            request,
            "El código no es válido. Solicita uno nuevo."
        )
        return redirect("accounts:recuperar_password")

    codigo_ingresado = request.POST.get("codigo", "").strip()

    if not codigo_ingresado.isdigit() or len(codigo_ingresado) != 6:
        messages.error(
            request,
            "Debes ingresar un código válido de 6 dígitos."
        )
        return render(
            request,
            "registration/recover_password.html",
            {
                "paso": "verificar_codigo",
                "email": datos.get("email"),
                "email_enmascarado": _enmascarar_correo(
                    datos.get("email", "")
                ),
            },
        )

    resultado = None

    # Bloquear temporalmente el registro durante la validación.
    with transaction.atomic():

        registro_codigo = (
            PasswordResetCode.objects
            .select_for_update()
            .filter(pk=codigo_id)
            .first()
        )

        if not registro_codigo:
            resultado = "invalido"

        elif registro_codigo.is_used:
            resultado = "usado"

        elif timezone.now() >= registro_codigo.expires_at:
            resultado = "expirado"

        elif registro_codigo.attempts >= _obtener_max_intentos():
            resultado = "intentos"

        else:
            usuario = registro_codigo.user

            if not usuario.is_active:
                resultado = "invalido"

            else:
                hash_ingresado = _generar_hash_codigo(
                    codigo_ingresado
                )

                codigo_valido = hmac.compare_digest(
                    hash_ingresado,
                    registro_codigo.code_hash
                )

                if not codigo_valido:
                    registro_codigo.attempts += 1
                    registro_codigo.save(
                        update_fields=["attempts"]
                    )

                    if registro_codigo.attempts >= _obtener_max_intentos():
                        resultado = "intentos"
                    else:
                        resultado = "incorrecto"

                else:
                    resultado = "correcto"

    if resultado == "expirado":
        request.session.pop(RESET_SESSION_KEY, None)
        messages.error(
            request,
            "El código expiró. Solicita uno nuevo."
        )
        return redirect("accounts:recuperar_password")

    if resultado == "usado":
        request.session.pop(RESET_SESSION_KEY, None)
        messages.error(
            request,
            "Este código ya fue utilizado. Solicita uno nuevo."
        )
        return redirect("accounts:recuperar_password")

    if resultado == "intentos":
        request.session.pop(RESET_SESSION_KEY, None)
        messages.error(
            request,
            "Superaste el máximo de intentos. Solicita un nuevo código."
        )
        return redirect("accounts:recuperar_password")

    if resultado != "correcto":
        messages.error(
            request,
            "Código incorrecto. Verifica el código e inténtalo nuevamente."
        )
        return render(
            request,
            "registration/recover_password.html",
            {
                "paso": "verificar_codigo",
                "email": datos.get("email"),
                "email_enmascarado": _enmascarar_correo(
                    datos.get("email", "")
                ),
            },
        )

    # La autorización queda asociada a esta sesión.
    datos["verificado"] = True
    request.session[RESET_SESSION_KEY] = datos

    return render(
        request,
        "registration/recover_password.html",
        {"paso": "cambiar_password"},
    )


def confirmar_password_reset(request):
    """
    Paso 3: guarda la nueva contraseña y marca el código como utilizado.
    """

    if request.method != "POST":
        return redirect("accounts:recuperar_password")

    datos = request.session.get(RESET_SESSION_KEY)

    if not datos or not datos.get("verificado"):
        messages.error(
            request,
            "Primero debes verificar el código de recuperación."
        )
        return redirect("accounts:recuperar_password")

    codigo_id = datos.get("codigo_id")

    if not codigo_id:
        request.session.pop(RESET_SESSION_KEY, None)
        messages.error(
            request,
            "La solicitud de recuperación no es válida."
        )
        return redirect("accounts:recuperar_password")

    password = request.POST.get("password", "")
    password_confirm = request.POST.get("password_confirm", "")

    if password != password_confirm:
        messages.error(
            request,
            "Las contraseñas no coinciden."
        )
        return render(
            request,
            "registration/recover_password.html",
            {"paso": "cambiar_password"},
        )

    resultado = None

    with transaction.atomic():

        registro_codigo = (
            PasswordResetCode.objects
            .select_for_update()
            .select_related("user")
            .filter(pk=codigo_id)
            .first()
        )

        if not registro_codigo:
            resultado = "invalido"

        elif registro_codigo.is_used:
            resultado = "usado"

        elif timezone.now() >= registro_codigo.expires_at:
            resultado = "expirado"

        elif not registro_codigo.user.is_active:
            resultado = "invalido"

        else:
            usuario = registro_codigo.user

            try:
                validate_password(password, usuario)

            except ValidationError as error:
                resultado = "password_invalida"
                errores_password = error.messages

            else:
                usuario.set_password(password)
                usuario.save(update_fields=["password"])

                # Marcar el código como utilizado.
                registro_codigo.is_used = True
                registro_codigo.save(update_fields=["is_used"])

                resultado = "correcto"

    if resultado == "password_invalida":
        for mensaje in errores_password:
            messages.error(request, mensaje)

        return render(
            request,
            "registration/recover_password.html",
            {"paso": "cambiar_password"},
        )

    if resultado == "expirado":
        request.session.pop(RESET_SESSION_KEY, None)
        messages.error(
            request,
            "La autorización expiró. Solicita un nuevo código."
        )
        return redirect("accounts:recuperar_password")

    if resultado != "correcto":
        request.session.pop(RESET_SESSION_KEY, None)
        messages.error(
            request,
            "No fue posible completar la recuperación. Solicita un nuevo código."
        )
        return redirect("accounts:recuperar_password")

    # Eliminar los datos temporales de la sesión.
    request.session.pop(RESET_SESSION_KEY, None)

    messages.success(
        request,
        "Tu contraseña fue actualizada correctamente. Ya puedes iniciar sesión."
    )

    return redirect("login")