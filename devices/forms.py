from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from organizations.models import Zone
from .models import Catalog, Product, Device, Measurement, History, AlertEvent, AlertRule, MaintenanceRequest
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
#clases formulario categoria y producto - preentrega eva3 --> PM 
# ModelForm de Categoría (modelo Catalog): se reutiliza para Crear y Editar.
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Catalog
        fields = ["catalog_id", "name", "description", "status"]
        widgets = {
            "catalog_id": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "status": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if len(name) < 3:
            raise ValidationError("Ingrese al menos 3 caracteres.")
        return name

    def clean_catalog_id(self):
        catalog_id = self.cleaned_data["catalog_id"].strip()
        exists = (
            Catalog.objects.filter(catalog_id__iexact=catalog_id)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if exists:
            raise ValidationError("Ya existe una categoría con ese código.")
        return catalog_id


# ModelForm de Producto: se reutiliza para Crear y Editar.
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "product_id", "name", "description", "kwh",
            "manufacturer", "model", "sku", "catalog",
        ]
        labels = {"catalog": "Categoría"}
        widgets = {
            "product_id": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "kwh": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "manufacturer": forms.TextInput(attrs={"class": "form-control"}),
            "model": forms.TextInput(attrs={"class": "form-control"}),
            "sku": forms.TextInput(attrs={"class": "form-control"}),
            "catalog": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Las categorías eliminadas lógicamente no se pueden seleccionar.
        self.fields["catalog"].queryset = Catalog.objects.filter(
            deleted_at__isnull=True
        ).order_by("name")

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if len(name) < 3:
            raise ValidationError("Ingrese al menos 3 caracteres.")
        return name

    def clean_product_id(self):
        product_id = self.cleaned_data["product_id"].strip()
        exists = (
            Product.objects.filter(product_id__iexact=product_id)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if exists:
            raise ValidationError("Ya existe un producto con ese código.")
        return product_id

    def clean_sku(self):
        sku = self.cleaned_data["sku"].strip()
        exists = (
            Product.objects.filter(sku__iexact=sku)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if exists:
            raise ValidationError("Ya existe un producto con ese SKU.")
        return sku

    def clean_kwh(self):
        kwh = self.cleaned_data.get("kwh")
        if kwh is not None and kwh < 0:
            raise ValidationError("El consumo no puede ser negativo.")
        return kwh
    
#def Measurement --> preentrega eva3 --> PM
# ModelForm de Measurement: se reutiliza para Crear y Editar (mismo patrón que DeviceForm).
class MeasurementForm(forms.ModelForm):
    class Meta:
        model = Measurement
        fields = [
            "measurement_id",
            "value",
            "unit",
            "datetime",
            "status",
            "origin",
            "device",
        ]
        widgets = {
            "measurement_id": forms.TextInput(attrs={"class": "form-control"}),
            "value": forms.NumberInput(attrs={"class": "form-control", "step": "0.0001"}),
            "unit": forms.TextInput(attrs={"class": "form-control"}),
            # format: para que al editar el campo datetime-local muestre el valor guardado.
            "datetime": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"class": "form-control", "type": "datetime-local"},
            ),
            "status": forms.TextInput(attrs={"class": "form-control"}),
            "origin": forms.TextInput(attrs={"class": "form-control"}),
            "device": forms.Select(attrs={"class": "form-select"}),
        }

    # Recibe el usuario para que el selector solo muestre dispositivos de su ámbito.
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            from .views import get_visible_devices  # import local: evita import circular
            self.fields["device"].queryset = get_visible_devices(user)

    # El código es único en la base de datos (incluye eliminadas lógicas).
    def clean_measurement_id(self):
        code = self.cleaned_data["measurement_id"].strip()
        exists = (
            Measurement.objects.filter(measurement_id__iexact=code)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if exists:
            raise ValidationError("Ya existe una medición con ese código.")
        return code

    # Una lectura de consumo no puede ser negativa.
    def clean_value(self):
        value = self.cleaned_data["value"]
        if value < 0:
            raise ValidationError("El valor no puede ser negativo.")
        return value
    
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

#preentrega eva3 - PM Formulario Alertas
# Estados posibles de una alerta: se usan en el formulario y en el filtro del listado.
ALERT_STATUS_CHOICES = [
    ("abierta", "Abierta"),
    ("reconocida", "Reconocida"),
    ("resuelta", "Resuelta"),
]


# ModelForm de AlertEvent: se reutiliza para Crear y Editar (mismo patrón que DeviceForm).
# Quién reconoce o resuelve (y cuándo) lo decide el servidor, no el formulario.
class AlertEventForm(forms.ModelForm):
    status = forms.ChoiceField(
        choices=ALERT_STATUS_CHOICES,
        initial="abierta",
        label="Estado",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = AlertEvent
        fields = [
            "alert_event_id",
            "alert_rule",
            "device",
            "measurement",
            "status",
            "min_limit_snapshot",
            "max_limit_snapshot",
            "observations",
        ]
        widgets = {
            "alert_event_id": forms.TextInput(attrs={"class": "form-control"}),
            "alert_rule": forms.Select(attrs={"class": "form-select"}),
            "device": forms.Select(attrs={"class": "form-select"}),
            "measurement": forms.Select(attrs={"class": "form-select"}),
            "min_limit_snapshot": forms.NumberInput(attrs={"class": "form-control", "step": "0.0001"}),
            "max_limit_snapshot": forms.NumberInput(attrs={"class": "form-control", "step": "0.0001"}),
            "observations": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
        help_texts = {
            "min_limit_snapshot": "Si lo dejas vacío se copia de la regla.",
            "max_limit_snapshot": "Si lo dejas vacío se copia de la regla.",
        }

    # Recibe el usuario para que dispositivos y mediciones sean solo los de su ámbito.
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["alert_rule"].queryset = AlertRule.objects.filter(deleted_at__isnull=True)
        if user is not None:
            from .views import get_visible_devices, get_visible_measurements  # import local: evita import circular
            self.fields["device"].queryset = get_visible_devices(user)
            self.fields["measurement"].queryset = get_visible_measurements(user)

    # El código es único en la base de datos (incluye eliminadas lógicas).
    def clean_alert_event_id(self):
        code = self.cleaned_data["alert_event_id"].strip()
        exists = (
            AlertEvent.objects.filter(alert_event_id__iexact=code)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if exists:
            raise ValidationError("Ya existe una alerta con ese código.")
        return code

    # Reglas que cruzan campos: la medición debe ser del dispositivo, la regla debe
    # corresponder al producto del dispositivo, y los límites se copian de la regla si vienen vacíos.
    def clean(self):
        cleaned = super().clean()
        device = cleaned.get("device")
        measurement = cleaned.get("measurement")
        rule = cleaned.get("alert_rule")

        if device and measurement and measurement.device_id != device.pk:
            self.add_error("measurement", "La medición no pertenece al dispositivo seleccionado.")

        if device and rule and rule.product_id != device.product_id:
            self.add_error("alert_rule", "La regla no corresponde al producto del dispositivo.")

        if rule:
            if cleaned.get("min_limit_snapshot") is None:
                cleaned["min_limit_snapshot"] = rule.min_limit
            if cleaned.get("max_limit_snapshot") is None:
                cleaned["max_limit_snapshot"] = rule.max_limit

        minimo = cleaned.get("min_limit_snapshot")
        maximo = cleaned.get("max_limit_snapshot")
        if minimo is not None and maximo is not None and minimo > maximo:
            self.add_error("max_limit_snapshot", "El límite máximo no puede ser menor que el mínimo.")

        return cleaned


#preentrega eva3 - PM Formulario Mantenimiento
# Opciones controladas: se usan en el formulario y en los filtros del listado.
MAINTENANCE_TYPE_CHOICES = [
    ("preventivo", "Preventivo"),
    ("correctivo", "Correctivo"),
]
MAINTENANCE_PRIORITY_CHOICES = [
    ("baja", "Baja"),
    ("media", "Media"),
    ("alta", "Alta"),
    ("crítica", "Crítica"),
]
MAINTENANCE_STATUS_CHOICES = [
    ("pendiente", "Pendiente"),
    ("en proceso", "En proceso"),
    ("cerrada", "Cerrada"),
]


# ModelForm de MaintenanceRequest: se reutiliza para Crear y Editar (mismo patrón que DeviceForm).
# La organización, quién la solicita y la fecha de cierre las decide el servidor, no el formulario.
class MaintenanceRequestForm(forms.ModelForm):
    request_type = forms.ChoiceField(
        choices=MAINTENANCE_TYPE_CHOICES,
        label="Tipo de solicitud",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    priority = forms.ChoiceField(
        choices=MAINTENANCE_PRIORITY_CHOICES,
        initial="media",
        label="Prioridad",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    status = forms.ChoiceField(
        choices=MAINTENANCE_STATUS_CHOICES,
        initial="pendiente",
        label="Estado",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    # RF-26: toda solicitud se asocia a un dispositivo.
    device = forms.ModelChoiceField(
        queryset=Device.objects.none(),
        label="Dispositivo",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = MaintenanceRequest
        fields = [
            "maintenance_request_id",
            "request_type",
            "reason",
            "priority",
            "status",
            "device",
            "assigned_to",
            "scheduled_date",
            "actual_date",
            "diagnosis",
            "actions_text",
            "observations",
            "cost",
        ]
        widgets = {
            "maintenance_request_id": forms.TextInput(attrs={"class": "form-control"}),
            "reason": forms.TextInput(attrs={"class": "form-control"}),
            "assigned_to": forms.Select(attrs={"class": "form-select"}),
            # format: para que al editar el campo datetime-local muestre el valor guardado.
            "scheduled_date": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"class": "form-control", "type": "datetime-local"},
            ),
            "actual_date": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"class": "form-control", "type": "datetime-local"},
            ),
            "diagnosis": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "actions_text": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "observations": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "cost": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
        }
        help_texts = {
            "diagnosis": "Obligatorio para cerrar la solicitud.",
            "actions_text": "Obligatorio para cerrar la solicitud.",
            "actual_date": "Obligatoria para cerrar la solicitud.",
        }

    # Recibe el usuario para que dispositivos y responsables sean solo los de su ámbito.
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].required = False
        self.fields["assigned_to"].label_from_instance = (
            lambda u: u.get_full_name() or u.username
        )
        if user is not None:
            from .views import get_visible_devices  # import local: evita import circular
            self.fields["device"].queryset = get_visible_devices(user)

            # RF-27: solo usuarios activos de la misma organización (RN-03 / RF-08).
            responsables = get_user_model().objects.filter(
                is_active=True, profile__isnull=False
            )
            if not user.is_superuser:
                profile = getattr(user, "profile", None)
                if profile is None or profile.organization_id is None:
                    responsables = responsables.none()
                else:
                    responsables = responsables.filter(
                        profile__organization_id=profile.organization_id
                    )
            self.fields["assigned_to"].queryset = responsables.order_by("username")

    # El código es único en la base de datos (incluye eliminadas lógicas).
    def clean_maintenance_request_id(self):
        code = self.cleaned_data["maintenance_request_id"].strip()
        exists = (
            MaintenanceRequest.objects.filter(maintenance_request_id__iexact=code)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if exists:
            raise ValidationError("Ya existe una solicitud con ese código.")
        return code

    # Un costo no puede ser negativo.
    def clean_cost(self):
        cost = self.cleaned_data.get("cost")
        if cost is not None and cost < 0:
            raise ValidationError("El costo no puede ser negativo.")
        return cost

    # RN-14 / RF-28: para cerrar se exige fecha real y el resultado de la intervención.
    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") == "cerrada":
            if not cleaned.get("actual_date"):
                self.add_error("actual_date", "Indica la fecha real de ejecución para cerrar la solicitud.")
            if not (cleaned.get("diagnosis") or "").strip():
                self.add_error("diagnosis", "Indica el diagnóstico para cerrar la solicitud.")
            if not (cleaned.get("actions_text") or "").strip():
                self.add_error("actions_text", "Indica las acciones realizadas para cerrar la solicitud.")
        return cleaned