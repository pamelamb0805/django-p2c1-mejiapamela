from django import forms
from django.core.exceptions import ValidationError

from .models import Organization


# ModelForm de Organization: se reutiliza para Crear y Editar (mismo patrón que DeviceForm).
# Define campos, widgets Bootstrap y validaciones.
class OrganizationForm(forms.ModelForm):
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
        code = self.cleaned_data["organization_id"].strip()
        exists = (
            Organization.objects.filter(organization_id__iexact=code)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if exists:
            raise ValidationError("Ya existe una organización con ese código.")
        return code

    # Validación de legal_name: quita espacios y exige mínimo 3 caracteres.
    def clean_legal_name(self):
        name = self.cleaned_data["legal_name"].strip()
        if len(name) < 3:
            raise ValidationError("Ingrese al menos 3 caracteres.")
        return name

    # Validación de tax (RUT / identificación fiscal): no puede repetirse entre organizaciones activas.
    def clean_tax(self):
        tax = self.cleaned_data["tax"].strip()
        exists = (
            Organization.objects.filter(tax__iexact=tax, deleted_at__isnull=True)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if exists:
            raise ValidationError("Ya existe una organización con ese RUT.")
        return tax