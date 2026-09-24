from django.db import models
from core.models import BaseModel
# Create your models here.

#Modelo catalogo --Pamela

class Catalog(BaseModel):
    catalog_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.name

#Modelo producto --Pamela

class Product(BaseModel):
    product_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    kwh = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    manufacter = models.CharField(max_length=150, blank=True, null=True)
    model = models.CharField(max_length=150, blank=True, null=True)
    sku = models.CharField(max_length=100, unique=True)

    catalog = models.ForeignKey(
        "Catalog",
        on_delete=models.PROTECT,
        related_name="products"
    )

    def __str__(self):
        return self.name

#Modelo device --Pamela
class Device(BaseModel):
    device_id = models.CharField(max_length=50, unique=True)
    internal_name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    reference_power = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    serial_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)

    product = models.ForeignKey(
        "Product",
        on_delete=models.PROTECT,
        related_name="devices"
    )
    zone = models.ForeignKey(
        "zones.Zone",
        on_delete=models.PROTECT,
        related_name="devices"
    )

    def __str__(self):
        return self.internal_name


#Modelo Measurement --Pamela

class Measurement(BaseModel):
    measurement_id = models.CharField(max_length=50, unique=True)
    value = models.DecimalField(max_digits=12, decimal_places=4)
    unit = models.CharField(max_length=50)
    datetime = models.DateTimeField()
    status = models.CharField(max_length=50, blank=True, null=True)
    origin = models.CharField(max_length=50)

    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.PROTECT,
        related_name="measurements"
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="measurements",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.measurement_id


#Modelo alert_rule --Pamela

class AlertRule(BaseModel):
    alert_rule_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150)
    severity = models.CharField(max_length=50)
    unit = models.CharField(max_length=50, blank=True, null=True)
    min_limit = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    max_limit = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)

    product = models.ForeignKey(
        "devices.Product",
        on_delete=models.PROTECT,
        related_name="alert_rules"
    )

    def __str__(self):
        return self.name

#Modelo alert_event --Pamela

class AlertEvent(BaseModel):
    alert_event_id = models.CharField(max_length=50, unique=True)
    min_limit_snapshot = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    max_limit_snapshot = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)
    observations = models.TextField(blank=True, null=True)
    acknowledged_at = models.DateTimeField(blank=True, null=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="acknowledged_alert_events",
        blank=True,
        null=True
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="resolved_alert_events",
        blank=True,
        null=True
    )
    measurement = models.ForeignKey(
        "measurements.Measurement",
        on_delete=models.PROTECT,
        related_name="alert_events"
    )
    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.PROTECT,
        related_name="alert_events"
    )
    alert_rule = models.ForeignKey(
        "AlertRule",
        on_delete=models.PROTECT,
        related_name="alert_events"
    )

    def __str__(self):
        return self.alert_event_id


# Creación de la tabla Organization -- Alexander
# Falta creaciones de foreigKey
class MaintenanceRequest(BaseModel):
    maintenance_request_id = models.CharField(max_length=50, unique=True)
    type = models.CharField(max_length=100, blank=True, null=True)
    reason = models.CharField(max_length=255, blank=True, null=True)
    priority = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)
    scheduled_date = models.DateTimeField(blank=True, null=True)
    actual_date = models.DateTimeField(blank=True, null=True)
    diagnosis = models.TextField(blank=True, null=True)
    actions_text = models.TextField(blank=True, null=True) # actions_taken según diagrama
    observations = models.TextField(blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    closed_at = models.DateTimeField(blank=True, null=True)
    
    device = models.ForeignKey(
        "Device",
        on_delete=models.PROTECT,
        related_name="maintenance_requests",
        blank=True,
        null=True
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="maintenance_requests"
    )
    #fk que faltaban --Pamela
        request_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_maintenance_requests"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_maintenance_requests",
        blank=True,
        null=True
    )
    def __str__(self):
        return self.maintenance_request_id

# Creación de la tabla Organization -- Alexander
class History(BaseModel):
    history_id = models.CharField(max_length=50, unique=True)
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    reason = models.CharField(max_length=255, blank=True, null=True)

    device = models.ForeignKey(
        "Device",
        on_delete=models.PROTECT,
        related_name="histories"
    )
    
    zone = models.ForeignKey(
        "zones.Zone",
        on_delete=models.PROTECT,
        related_name="histories",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.history_id
