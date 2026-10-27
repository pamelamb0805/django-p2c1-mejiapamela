from django import forms
from django.core.exceptions import ValidationError

from organizations.models import Zone
from .models import Catalog, Device, Measurement, History, AlertEvent, AlertRule, MaintenanceRequest

class ArchiveDevicesForm(forms.Form):
    """Valida que los dispositivos elegidos pertenezcan al ámbito del usuario."""

    devices = forms.ModelMultipleChoiceField(
        queryset=Device.objects.none(),
        label="Dispositivos a archivar",
    )

    def __init__(self, *args, queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        if queryset is not None:
            self.fields["devices"].queryset = queryset


# ModelForm de Device: se reutiliza para Crear y Editar. Define campos, widgets Bootstrap y validaciones.
# Clase 8 - Alexander
class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = [
            "device_id",
            "internal_name",
            "description",
            "reference_power",
            "serial_number",
            "status",
            "product",
            "zone",
        ]
        widgets = {
            "device_id": forms.TextInput(attrs={"class": "form-control"}),
            "internal_name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "reference_power": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "serial_number": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.TextInput(attrs={"class": "form-control"}),
            "product": forms.Select(attrs={"class": "form-select"}),
            "zone": forms.Select(attrs={"class": "form-select"}),
        }

    # Recibe el usuario para que el selector de zona solo muestre zonas de su organización.
    # Clase 8 - Alexander - corrección preentrega eva 3 --> PM
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Los productos eliminados lógicamente no se pueden seleccionar.
        self.fields["product"].queryset = (
            self.fields["product"].queryset.filter(
                deleted_at__isnull=True
            )
        )

        # Solo zonas activas que el usuario tenga autorizadas.
        zones = Zone.objects.filter(deleted_at__isnull=True)

        if user is not None and not user.is_superuser:
            profile = getattr(user, "profile", None)

            if profile is None or not profile.organization_id:
                zones = zones.none()
            else:
                zones = zones.filter(
                    organization_id=profile.organization_id
                )

        self.fields["zone"].queryset = zones


    # Validación del campo internal_name: quita espacios y exige mínimo 3 caracteres.
    # Clase 8 - Alexander
    def clean_internal_name(self):
        name = self.cleaned_data["internal_name"].strip()
        if len(name) < 3:
            raise ValidationError("Ingrese al menos 3 caracteres.")
        return name

    # Validación del campo device_id: evita códigos repetidos (sin distinguir mayúsculas).
    # exclude(pk=self.instance.pk) permite editar sin chocar consigo mismo.
    # Clase 8 - Alexander
    def clean_device_id(self):
        device_id = self.cleaned_data["device_id"].strip()
        exists = (
            Device.objects.filter(device_id__iexact=device_id)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if exists:
            raise ValidationError("Ya existe un dispositivo con ese código.")
        return device_id

    # Validación del campo serial_number: es opcional, pero si viene no puede repetirse.
    # Clase 8 - Alexander
    def clean_serial_number(self):
        serial = self.cleaned_data.get("serial_number")
        if not serial:
            return None
        serial = serial.strip()
        exists = (
            Device.objects.filter(serial_number__iexact=serial)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if exists:
            raise ValidationError("Ya existe un dispositivo con ese número de serie.")
        return serial

    def clean(self):
        cleaned_data = super().clean()
        zone = cleaned_data.get("zone")

        if zone and self.fields["zone"].queryset.filter(
            pk=zone.pk
        ).exists() is False:
            self.add_error(
                "zone",
                "La zona seleccionada no está autorizada."
            )

        return cleaned_data


#def Measurement --> preentrega eva3
class MeasurementForm(forms.ModelForm):
    class Meta:
        #def Registro Formulario
        def __init__(self, *args, user=None, **kwargs):
            if user is not None:
                from .views import get_user_devices
                self.fields['device'].queryset = get_user_devices(user) 
            for field in self.fields.values():
                field.widget.attrs.setdefault({'class': 'form-control'})
            self.fields["datetime"].widget = forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local",}
            )
        model = Measurement
        fields = [
            "measurement_id",
            "value",
            "unit",
            "datetime",
            "status",
            "origin",
            "device"
        ]
        widgets = {
            "device": forms.Select(attrs={"class": "form-select"}),
            "value": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "timestamp": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
        }

#preentrega eva3 - PM Formulario Catalogo
class CatalogForm(forms.ModelForm):
    class Meta:
        model = Catalog
        fields = ["catalog_id", "name", "description", "status"]
        widgets = {
            "catalog_id": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "status": forms.TextInput(attrs={"class": "form-control"}),
        }