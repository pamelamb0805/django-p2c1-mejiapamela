from django import forms
from django.core.exceptions import ValidationError
from .models import Department, Organization, User, Zone

import re
from core.validators import FormLimitsMixin, validate_code, validate_name, validate_optional_text

# ModelForm de Organization: se reutiliza para Crear y Editar (mismo patrón que DeviceForm).
# Define campos, widgets Bootstrap y validaciones.
#correccion eva 3 --> PM --> Validadores Formularios
class OrganizationForm(FormLimitsMixin, forms.ModelForm):
    # El modelo permite NULL en status, lo que Django mostraría como "Desconocido / Sí / No".
    # Se declara como casilla simple: marcada = activa, desmarcada = inactiva.
    status = forms.BooleanField(
        required=False,
        label="Activa",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = Organization
        fields = [
            "organization_id",
            "legal_name",
            "comercial_name",
            "contact",
            "email",
            "tax",
            "status",
        ]
        widgets = {
            "organization_id": forms.TextInput(attrs={"class": "form-control"}),
            "legal_name": forms.TextInput(attrs={"class": "form-control"}),
            "comercial_name": forms.TextInput(attrs={"class": "form-control"}),
            "contact": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "tax": forms.TextInput(attrs={"class": "form-control"}),
        }

    # Validación de organization_id: evita códigos repetidos (sin distinguir mayúsculas).
    # Se revisan también las eliminadas lógicamente, porque el código es único en la base de datos.
    # exclude(pk=self.instance.pk) permite editar sin chocar consigo misma.
    def clean_organization_id(self):
        #correccion eva 3 --> PM --> Validadores Formularios
        code = validate_code(self.cleaned_data["organization_id"])
        exists = (
            Organization.objects.filter(organization_id__iexact=code)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if exists:
            raise ValidationError("Ya existe una organización con ese código.")
        return code

    # Validación de legal_name: quita espacios y exige mínimo 3 caracteres.
    #correccion eva 3 --> PM --> Validadores Formularios
    def clean_legal_name(self):
        return validate_name(self.cleaned_data["legal_name"])

    def clean_comercial_name(self):
        return validate_optional_text(self.cleaned_data.get("comercial_name")) or None

    def clean_contact(self):
        return validate_optional_text(self.cleaned_data.get("contact")) or None

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_tax(self):
        tax = self.cleaned_data["tax"].strip()
        if not re.fullmatch(r"[0-9A-Za-z.\-]{5,20}", tax):
            raise ValidationError(
                "Ingrese un RUT o identificación fiscal válido "
                "(5 a 20 caracteres: letras, números, punto y guion)."
            )
        exists = (
            Organization.objects.filter(tax__iexact=tax, deleted_at__isnull=True)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if exists:
            raise ValidationError("Ya existe una organización con ese RUT.")
        return tax

#preentrega eva3 PM --> Formulario Departamento
# ModelForm de Department: se reutiliza para Crear y Editar (mismo patrón que OrganizationForm).
# El superusuario elige la organización; un usuario normal queda atado a la suya.
#correccion eva 3 --> PM --> Validadores Formularios
class DepartmentForm(FormLimitsMixin, forms.ModelForm):
    # Casilla simple: marcada = activo, desmarcada = inactivo.
    status = forms.BooleanField(
        required=False,
        label="Activo",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = Department
        fields = ["department_id", "name", "description", "status", "organization", "user"]
        widgets = {
            "department_id": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.TextInput(attrs={"class": "form-control"}),
            "organization": forms.Select(attrs={"class": "form-select"}),
            "user": forms.Select(attrs={"class": "form-select"}),
        }

    # Recibe el usuario que opera para limitar organización y responsables a su ámbito.
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_superuser = bool(user and user.is_superuser)
        profile = getattr(user, "profile", None) if user else None
        self.org = None if self.is_superuser else getattr(profile, "organization", None)

        responsables = User.objects.filter(deleted_at__isnull=True)
        if self.is_superuser:
            self.fields["organization"].queryset = Organization.objects.filter(
                deleted_at__isnull=True
            )
        else:
            # Un usuario normal no elige organización: se usa siempre la suya.
            del self.fields["organization"]
            if self.org:
                self.instance.organization = self.org
                responsables = responsables.filter(organization=self.org)
            else:
                responsables = responsables.none()

        self.fields["user"].queryset = responsables
        self.fields["user"].required = False
        self.fields["user"].empty_label = "Sin responsable"

    # El código es único en la base de datos (incluye eliminados lógicos).
    def clean_department_id(self):
        #correccion eva 3 --> PM --> Validadores Formularios
        code = validate_code(self.cleaned_data["department_id"])
        exists = (
            Department.objects.filter(department_id__iexact=code)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if exists:
            raise ValidationError("Ya existe un departamento con ese código.")
        return code

    #correccion eva 3 --> PM --> Validadores Formularios
    def clean_name(self):
        return validate_name(self.cleaned_data["name"])

    def clean_description(self):
        return validate_optional_text(self.cleaned_data.get("description")) or None

    # Reglas que cruzan campos: organización definida, nombre único dentro de ella (RN-05)
    # y responsable perteneciente a la misma organización.
    def clean(self):
        cleaned = super().clean()

        if self.is_superuser:
            org = cleaned.get("organization")
            if org is None:
                return cleaned  # el propio campo ya muestra su error
        else:
            org = self.org
            if org is None:
                raise ValidationError("Tu cuenta no tiene una organización asignada.")

        name = cleaned.get("name")
        if name and (
            Department.objects.filter(
                organization=org, name__iexact=name, deleted_at__isnull=True
            )
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            self.add_error("name", "Ya existe un departamento con ese nombre en la organización.")

        responsable = cleaned.get("user")
        if responsable and responsable.organization_id != org.pk:
            self.add_error("user", "El responsable debe pertenecer a la misma organización.")

        return cleaned

    
#preentrega eva3 PM --> Formulario Zonas
# ModelForm de Zone: se reutiliza para Crear y Editar (mismo patrón que DepartmentForm).
# El superusuario elige la organización; un usuario normal queda atado a la suya.
#correccion eva 3 --> PM --> Validadores Formularios
class ZoneForm(FormLimitsMixin, forms.ModelForm):
    # Casilla simple: marcada = activa, desmarcada = inactiva.
    status = forms.BooleanField(
        required=False,
        label="Activa",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = Zone
        fields = ["zone_id", "name", "description", "status", "organization", "department"]
        widgets = {
            "zone_id": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.TextInput(attrs={"class": "form-control"}),
            "organization": forms.Select(attrs={"class": "form-select"}),
            "department": forms.Select(attrs={"class": "form-select"}),
        }

    # Recibe el usuario que opera para limitar organización y departamentos a su ámbito.
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_superuser = bool(user and user.is_superuser)
        profile = getattr(user, "profile", None) if user else None
        self.org = None if self.is_superuser else getattr(profile, "organization", None)

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

    # El código es único en la base de datos (incluye eliminadas lógicas).
    def clean_zone_id(self):

        #correccion eva 3 --> PM --> Validadores Formularios
        code = validate_code(self.cleaned_data["zone_id"])
        exists = (
            Zone.objects.filter(zone_id__iexact=code)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if exists:
            raise ValidationError("Ya existe una zona con ese código.")
        return code

    #correccion eva 3 --> PM --> Validadores Formularios
    def clean_name(self):
        return validate_name(self.cleaned_data["name"])

    # Reglas que cruzan campos: organización definida, nombre único dentro de ella (RN-05)
    # y departamento perteneciente a la misma organización.
    def clean(self):
        cleaned = super().clean()

        if self.is_superuser:
            org = cleaned.get("organization")
            if org is None:
                return cleaned  # el propio campo ya muestra su error
        else:
            org = self.org
            if org is None:
                raise ValidationError("Tu cuenta no tiene una organización asignada.")

        name = cleaned.get("name")
        if name and (
            Zone.objects.filter(
                organization=org, name__iexact=name, deleted_at__isnull=True
            )
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            self.add_error("name", "Ya existe una zona con ese nombre en la organización.")

        departamento = cleaned.get("department")
        if departamento and departamento.organization_id != org.pk:
            self.add_error("department", "El departamento debe pertenecer a la misma organización.")

        return cleaned