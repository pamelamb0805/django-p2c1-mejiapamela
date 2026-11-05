#UserProfileAdminForm con el clean()
#preentrega eva 3 - PM
import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from organizations.models import Department, Organization

from .models import UserProfile

User = get_user_model()


class UserProfileAdminForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        organization = cleaned_data.get("organization")
        department = cleaned_data.get("department")

        # El departamento debe pertenecer a la organización elegida
        if (
            organization
            and department
            and department.organization_id != organization.id
        ):
            self.add_error(
                "department",
                "El departamento debe pertenecer a la organización seleccionada.",
            )
        return cleaned_data


# ---------------------------------------------------------------------------
# M02 · CRUD de Usuarios y perfiles (preentrega eva 3)
# ---------------------------------------------------------------------------

def normalizar_rut(valor):
    """Deja el RUT sin puntos ni espacios y con guion: '12.345.678-5' -> '12345678-5'."""
    limpio = re.sub(r"[.\s]", "", valor or "").upper()
    if "-" not in limpio and len(limpio) > 1:
        limpio = f"{limpio[:-1]}-{limpio[-1]}"
    return limpio


def rut_valido(rut):
    """Valida el formato y el dígito verificador (módulo 11) de un RUT normalizado."""
    if not re.fullmatch(r"\d{1,8}-[\dK]", rut):
        return False
    cuerpo, dv = rut.split("-")
    suma, factor = 0, 2
    for digito in reversed(cuerpo):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - (suma % 11)
    esperado = "0" if resto == 11 else "K" if resto == 10 else str(resto)
    return dv == esperado


# Un solo formulario para Crear y Editar: maneja la cuenta (User de Django) y su perfil (UserProfile).
class UserProfileForm(forms.ModelForm):
    # --- Datos de la cuenta (modelo User de Django) ---
    username = forms.CharField(
        label="Nombre de usuario",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    first_name = forms.CharField(
        label="Nombres",
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        label="Apellidos",
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    password = forms.CharField(
        label="Contraseña",
        required=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "new-password"}
        ),
    )
    # --- Rol: se guarda como grupo de Django (los permisos viven en el grupo) ---
    role = forms.ModelChoiceField(
        label="Rol (grupo)",
        queryset=Group.objects.none(),
        required=False,
        empty_label="Sin rol",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = UserProfile
        fields = [
            "organization",
            "department",
            "employee_code",
            "rut",
            "phone",
            "address",
        ]
        widgets = {
            "organization": forms.Select(attrs={"class": "form-select"}),
            "department": forms.Select(attrs={"class": "form-select"}),
            "employee_code": forms.TextInput(attrs={"class": "form-control"}),
            "rut": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "12345678-5"}
            ),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
        }
        labels = {
            "employee_code": "Código de empleado",
            "rut": "RUT",
            "phone": "Teléfono",
            "address": "Dirección",
            "organization": "Organización",
            "department": "Departamento",
        }

    # Orden en que se muestran los campos en el modal.
    field_order = [
        "username", "first_name", "last_name", "email", "password",
        "organization", "department", "employee_code", "rut",
        "phone", "address", "role",
    ]

    # Recibe el usuario que opera para limitar organización, departamentos y roles a su ámbito.
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_superuser = bool(user and user.is_superuser)
        profile = getattr(user, "profile", None) if user else None
        self.org = None if self.is_superuser else getattr(profile, "organization", None)

        # Cuenta asociada: solo existe al editar.
        self.cuenta = self.instance.user if self.instance.pk else None

        grupo_actual = None
        if self.cuenta:
            self.fields["username"].disabled = True  # el nombre de usuario no se cambia
            self.initial["username"] = self.cuenta.username
            self.initial["first_name"] = self.cuenta.first_name
            self.initial["last_name"] = self.cuenta.last_name
            self.initial["email"] = self.cuenta.email
            grupo_actual = self.cuenta.groups.first()
            self.initial["role"] = grupo_actual.pk if grupo_actual else None
            self.fields["password"].help_text = "Déjala en blanco para mantener la contraseña actual."
        else:
            self.fields["password"].required = True

        # Organización y departamentos.
        departamentos = Department.objects.filter(deleted_at__isnull=True)
        if self.is_superuser:
            self.fields["organization"].queryset = Organization.objects.filter(
                deleted_at__isnull=True
            )
        else:
            # Un usuario normal no elige organización: se usa siempre la suya.
            del self.fields["organization"]
            if self.org:
                self.instance.organization = self.org
                departamentos = departamentos.filter(organization=self.org)
            else:
                departamentos = departamentos.none()
        self.fields["department"].queryset = departamentos
        self.fields["department"].required = False
        self.fields["department"].empty_label = "Sin departamento"

        # Roles: un usuario normal solo puede asignar grupos cuyos permisos él mismo tiene
        # (así no puede darse ni dar más poder del que posee). Se conserva el grupo actual.
        todos = Group.objects.order_by("name")
        if self.is_superuser:
            grupos = todos
        else:
            mis_permisos = user.get_all_permissions() if user else set()
            permitidos = [
                g.pk
                for g in todos.prefetch_related("permissions__content_type")
                if all(
                    f"{p.content_type.app_label}.{p.codename}" in mis_permisos
                    for p in g.permissions.all()
                )
            ]
            filtro = Q(pk__in=permitidos)
            if grupo_actual:
                filtro |= Q(pk=grupo_actual.pk)
            grupos = todos.filter(filtro)
        self.fields["role"].queryset = grupos

    # El nombre de usuario no puede repetirse (sin distinguir mayúsculas).
    def clean_username(self):
        if self.cuenta:
            return self.cuenta.username
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Ya existe un usuario con ese nombre de usuario.")
        return username

    # El correo no puede repetirse: el login también acepta el correo como usuario.
    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        existentes = User.objects.filter(email__iexact=email)
        if self.cuenta:
            existentes = existentes.exclude(pk=self.cuenta.pk)
        if existentes.exists():
            raise ValidationError("Ya existe un usuario con ese correo.")
        return email

    # Al crear la contraseña es obligatoria; al editar, vacía significa "no cambiar".
    # Se aplican los validadores de contraseña definidos en settings.py.
    def clean_password(self):
        password = self.cleaned_data.get("password", "")
        if password:
            candidato = self.cuenta or User(
                username=self.cleaned_data.get("username", ""),
                email=self.cleaned_data.get("email", ""),
            )
            try:
                validate_password(password, candidato)
            except ValidationError as error:
                raise ValidationError(list(error.messages))
        return password

    # El código de empleado es único en la base de datos (incluye eliminados lógicos).
    def clean_employee_code(self):
        code = self.cleaned_data["employee_code"].strip()
        exists = (
            UserProfile.objects.filter(employee_code__iexact=code)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if exists:
            raise ValidationError("Ya existe un perfil con ese código de empleado.")
        return code

    # El RUT es opcional; si viene se normaliza, se valida su dígito verificador y no puede repetirse.
    def clean_rut(self):
        rut = self.cleaned_data.get("rut")
        if not rut:
            return None
        rut = normalizar_rut(rut)
        if not rut_valido(rut):
            raise ValidationError("RUT inválido. Ejemplo: 12345678-5")
        exists = (
            UserProfile.objects.filter(rut__iexact=rut)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if exists:
            raise ValidationError("Ya existe un perfil con ese RUT.")
        return rut

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if phone and not re.fullmatch(r"[0-9+()\s-]{8,20}", phone):
            raise ValidationError("Ingrese un teléfono válido (8 a 20 dígitos).")
        return phone

    # Un usuario normal debe tener organización. (El departamento vs. organización lo valida
    # UserProfile.clean() del modelo.)
    def clean(self):
        cleaned = super().clean()
        if not self.is_superuser and self.org is None:
            raise ValidationError("Tu cuenta no tiene una organización asignada.")
        return cleaned

    # Guarda cuenta + perfil en una sola transacción y asigna el rol (grupo).
    @transaction.atomic
    def save(self, commit=True):
        datos = self.cleaned_data

        cuenta = self.cuenta or User(username=datos["username"])
        cuenta.first_name = datos.get("first_name", "")
        cuenta.last_name = datos.get("last_name", "")
        cuenta.email = datos["email"]
        if datos.get("password"):
            cuenta.set_password(datos["password"])
        cuenta.save()

        perfil = super().save(commit=False)
        perfil.user = cuenta
        perfil.save()

        # El rol solo se toca si el usuario lo cambió (no se pierden otros grupos sin querer).
        if "role" in self.changed_data:
            rol = datos.get("role")
            cuenta.groups.set([rol] if rol else [])
        return perfil